"""Nar komut satırı arayüzü.

  nar run    dosya.nar          derler ve Node ile çalıştırır
  nar build  dosya.nar          JavaScript üretir
  nar build  dosya.nar --target web    tek dosyalık HTML üretir
  nar check  dosya.nar          yalnızca denetler
  nar emit   dosya.nar          üretilen kodu ekrana yazar
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Hata mesajları ve çıktılar Türkçe. Windows'ta konsolun varsayılan kod
# sayfası (cp1254 gibi) bunları yazamaz ve program çöker. `nar.cmd` bunu
# PYTHONIOENCODING ile ayarlıyor ama `python -m narc` doğrudan çağrıldığında
# da çalışmalı.
for _akis in (sys.stdout, sys.stderr):
    if hasattr(_akis, "reconfigure"):
        try:
            _akis.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

from . import __version__
from .bicim import BicimHatasi, bicimlendir
from .diagnostics import NarError, NarErrors
from .masaustu_paket import paketle
from .mobil_paket import paketle as mobil_paketle
from .ghb_paket import paketle as ghb_paketle
from . import exe_paket
from . import ghb_calistir
from . import ide_api, uzanti_kayit
from . import bytecode as bc
from . import vm as vm_modulu
from . import vm_metotlar
from .backends import bytecode_uretici
from .driver import compile_file, to_html


def fail(err: NarError, sources: dict[str, str]) -> int:
    if isinstance(err, NarErrors):
        print(err.render_all(sources), file=sys.stderr)
        return 1
    source = None
    if err.span is not None:
        source = sources.get(err.span.filename)
    print(err.render(source), file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nar",
        description="Nar derleyicisi — çok platformlu uygulamalar için tek dil.",
    )
    parser.add_argument("--version", action="version", version=f"Nar {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)

    fmt = subs.add_parser("fmt", help="kodu yeniden girintiler ve düzenler")
    fmt.add_argument("file", type=Path, help="kaynak .nar dosyası")
    fmt.add_argument("--goster", action="store_true",
                     help="dosyayı değiştirme, sonucu ekrana yaz")
    fmt.add_argument("--denetle", action="store_true",
                     help="dosyayı değiştirme; düzenlenmesi gerekiyorsa 1 döner")

    for name, help_text in (
        ("run", "derler ve çalıştırır"),
        ("build", "hedef kodu dosyaya yazar"),
        ("check", "yalnızca tip denetimi yapar"),
        ("emit", "üretilen kodu ekrana yazar"),
        ("ozdenetim", "Nar ile yazılmış derleyiciyle denetler"),
    ):
        sub = subs.add_parser(name, help=help_text)
        sub.add_argument("file", type=Path, help="kaynak .nar dosyası")
        if name in ("build", "emit"):
            sub.add_argument("--target", default="js",
                             choices=["js", "web", "masaustu", "mobil", "ghb",
                                      "exe", "narb"],
                             help="çıktı hedefi: js (Node), web (tek HTML), "
                                  "masaustu (kendi penceresinde açılan uygulama), "
                                  "mobil (Android/iOS projesi), "
                                  "ghb (tek dosyalık Nar uygulaması), "
                                  "exe (tek başına çalışan Windows uygulaması), "
                                  "narb (Nar bytecode — kendi sanal makinesi)")
        if name in ("build", "emit", "check", "ozdenetim"):
            sub.add_argument("--kutuphane", action="store_true",
                             help="kütüphane olarak derle: 'main' gerekmez, "
                                  "fonksiyonlar globalThis.Nar altına açılır")
        if name == "build":
            sub.add_argument("-o", "--out", type=Path, default=None,
                             help="çıktı dosyası")
    calistir = subs.add_parser(
        "calistir", help="kendi sanal makinesinde çalıştırır (Node gerekmez)")
    calistir.add_argument("file", type=Path, help=".nar ya da .narb dosyası")
    calistir.add_argument("arguman", nargs="*",
                          help="programa geçirilecek argümanlar")

    bytecode_komutu = subs.add_parser(
        "bytecode", help="üretilen bytecode'u okunabilir biçimde yazar")
    bytecode_komutu.add_argument("file", type=Path, help="kaynak .nar dosyası")

    ac = subs.add_parser("ac", help=".ghb uygulamasını açar")
    ac.add_argument("file", type=Path, help="açılacak .ghb paketi")

    # Düzenleyicinin derleyiciye komut satırından ulaşması için: sonucu
    # tek satır JSON olarak yazar. Nar ile yazılmış IDE sunucusu bunu
    # kullanıyor — başka bir dilin kütüphanesine ihtiyaç duymadan.
    api = subs.add_parser(
        "api", help="düzenleyici için JSON çıktı verir (denetle/uret/calistir/kelimeler)")
    api.add_argument("islem", choices=list(ide_api.ISLEMLER))
    api.add_argument("file", type=Path, nargs="?", help="kaynak .nar dosyası")

    ide = subs.add_parser("ide", help="Nar IDE'yi açar")
    ide.add_argument("--port", type=int, default=8777)
    ide.add_argument("--motor", choices=["nar", "python"], default="nar",
                     help="sunucuyu hangi dilde yazılmış sürüm karşılasın")
    ide.add_argument("--tarayici-acma", action="store_true",
                     help="pencereyi kendiliğinden açma")

    uzanti_kur = subs.add_parser(
        "uzanti-kur", help=".ghb uzantısını bu bilgisayarda ilişkilendirir")
    uzanti_kur.add_argument(
        "--exe", action="store_true",
        help="Python yerine derlenmiş başlatıcıyı (nar-ac.exe) bağla; "
             "uygulamalar Python kurulu olmadan açılır")
    subs.add_parser("uzanti-kaldir", help=".ghb ilişkilendirmesini kaldırır")
    subs.add_parser("uzanti-durum", help=".ghb ilişkilendirmesini gösterir")

    return parser


def _bytecode_uret(yol: Path):
    """Kaynağı bytecode'a çevirir; hataları çağırana bırakır."""
    vm_metotlar.kur()
    derleme = compile_file(yol)
    return bytecode_uretici.uret(derleme.module, derleme.checker)


def komut_calistir(args) -> int:
    """Programı Nar'ın kendi sanal makinesinde çalıştırır.

    JavaScript üretilmez, Node çağrılmaz. Sayfa (DOM) ve sunucu işlemleri
    burada yoktur; onlar için `nar run` ya da `nar build --target web`.
    """
    if not args.file.exists():
        print(f"hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1

    vm_metotlar.kur()
    try:
        if args.file.suffix == ".narb":
            program = bc.oku_dosya(args.file.read_bytes())
        else:
            program = _bytecode_uret(args.file)
    except NarError as err:
        return fail(err, {args.file.name: args.file.read_text(encoding="utf-8-sig")})
    except (ValueError, bytecode_uretici.UretimHatasi) as e:
        print(f"hata: {e}", file=sys.stderr)
        return 1

    try:
        vm_modulu.calistir(program, list(args.arguman))
    except vm_modulu.NarCalismaHatasi as e:
        print(f"çalışma hatası: {e}", file=sys.stderr)
        return 1
    except RecursionError:
        print("çalışma hatası: özyineleme çok derin", file=sys.stderr)
        return 1
    return 0


def komut_bytecode(args) -> int:
    """Üretilen komutları okunabilir biçimde yazar."""
    if not args.file.exists():
        print(f"hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1
    try:
        program = _bytecode_uret(args.file)
    except NarError as err:
        return fail(err, {args.file.name: args.file.read_text(encoding="utf-8-sig")})
    except bytecode_uretici.UretimHatasi as e:
        print(f"hata: {e}", file=sys.stderr)
        return 1

    print(bc.dokum(program.ana))
    for islev in program.islevler:
        print()
        print(bc.dokum(islev))
    return 0


def komut_uzanti(args) -> int:
    """`.ghb` dosya ilişkilendirmesini kurar, kaldırır ya da gösterir.

    Kayıtlar yalnızca bu kullanıcı için yazılır; yönetici hakkı gerekmez
    ve `uzanti-kaldir` ile tamamen geri alınır.
    """
    kok = Path(__file__).resolve().parent.parent
    komut = args.command

    if komut == "uzanti-durum":
        print(uzanti_kayit.durum())
        return 0

    if komut == "uzanti-kur":
        exe_komutu = None
        if getattr(args, "exe", False):
            # Derlenmiş başlatıcı: çift tıklama Python'a uğramaz.
            try:
                calistirici = exe_paket.calistirici_kur()
            except exe_paket.ExeHatasi as e:
                print(f"hata: {e}", file=sys.stderr)
                return 1
            exe_komutu = f'"{calistirici}" "%1"'
        oldu, mesaj = uzanti_kayit.kur(kok, exe_komutu)
    else:
        oldu, mesaj = uzanti_kayit.kaldir()

    print(mesaj if oldu else f"hata: {mesaj}", file=sys.stdout if oldu else sys.stderr)
    return 0 if oldu else 1


def komut_ozdenetim(args) -> int:
    """Nar ile yazılmış derleyiciyle denetler.

    Derleyicinin kendisi Nar'la yazıldığı için önce Python derleyicisiyle
    JavaScript'e çevrilir, sonra Node ile çalıştırılır. Bu, self-hosting'in
    hangi noktada olduğunu elle görmenin yolu.

    Kapsam: sözcüksel çözümleme, sözdizim çözümleme ve tip denetiminin
    **bildirim aşaması** (tipler, imzalar, arayüz uyumu). Gövde denetimi
    henüz Nar'a taşınmadı; onun için `nar check` kullanılır.
    """
    if not args.file.exists():
        print(f"hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1

    node = shutil.which("node")
    if node is None:
        print("hata: 'node' bulunamadı. Node.js kurulu olmalı.", file=sys.stderr)
        return 1

    kok = Path(__file__).resolve().parent.parent
    giris = kok / "derleyici" / "denetle.nar"
    if not giris.exists():
        print(f"hata: {giris} bulunamadı", file=sys.stderr)
        return 1

    try:
        kod = compile_file(giris, kutuphane=True).to_js()
    except NarError as err:
        print("Nar derleyicisi derlenemedi:", err, file=sys.stderr)
        return 1

    build_dir = kok / ".narbuild"
    build_dir.mkdir(exist_ok=True)
    betik = build_dir / "nar-denetle.js"
    betik.write_text(
        kod + "\n"
        "const yol = process.argv[2];\n"
        "const kutuphane = process.argv[3] === 'kutuphane';\n"
        "console.log(Nar.dosyaRaporu(yol, kutuphane));\n",
        encoding="utf-8",
    )

    sonuc = subprocess.run(
        [node, str(betik), str(args.file),
         "kutuphane" if args.kutuphane else "program"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if sonuc.returncode != 0:
        print(sonuc.stderr.strip(), file=sys.stderr)
        return 1

    cikti = sonuc.stdout.strip()
    print(cikti)
    return 0 if cikti.startswith("tamam") else 1


def komut_fmt(args) -> int:
    """Biçimlendirici Nar diliyle yazılmıştır; burada yalnızca çağrılır."""
    if not args.file.exists():
        print(f"hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1

    kaynak = args.file.read_text(encoding="utf-8-sig")
    try:
        sonuc = bicimlendir(kaynak)
    except BicimHatasi as err:
        print(f"hata: {err}", file=sys.stderr)
        return 1

    if args.goster:
        sys.stdout.write(sonuc)
        return 0

    if args.denetle:
        if sonuc != kaynak:
            print(f"{args.file}: düzenlenmesi gerekiyor")
            return 1
        print(f"{args.file}: düzenli")
        return 0

    if sonuc == kaynak:
        print(f"{args.file}: zaten düzenli")
        return 0

    args.file.write_text(sonuc, encoding="utf-8")
    print(f"düzenlendi: {args.file}")
    return 0



def komut_ide(args) -> int:
    """Nar IDE'yi başlatır.

    Varsayılan sunucu Nar ile yazılmıştır (`araclar/ide_sunucusu.nar`);
    `--motor python` eski Python sunucusunu kullanır. İkisi de aynı
    arayüzü ve aynı derleyici API'sini kullanır, fark hızdadır:
    Python sunucusu derleyiciyi kendi içinde çağırır, Nar sunucusu her
    denetim için `nar api` sürecini başlatır.
    """
    import subprocess
    import sys as _sys
    kok = Path(__file__).resolve().parent.parent

    if args.motor == "python":
        komut = [_sys.executable, str(kok / "ide" / "sunucu.py"),
                 "--port", str(args.port)]
        if args.tarayici_acma:
            komut.append("--tarayici-acma")
        return subprocess.call(komut, cwd=str(kok))

    sunucu = kok / "araclar" / "ide_sunucusu.nar"
    if not sunucu.exists():
        print(f"bulunamadı: {sunucu}", file=sys.stderr)
        return 1
    from .driver import compile_file
    kod = compile_file(sunucu).to_js()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        betik = Path(tmp) / "ide_sunucusu.js"
        betik.write_text(kod, encoding="utf-8")
        node = shutil.which("node")
        if node is None:
            print("'node' bulunamadı; Node.js kurulu olmalı", file=sys.stderr)
            return 1
        arg = [node, str(betik), str(args.port), str(kok)]
        if args.tarayici_acma:
            arg.append("--tarayici-acma")
        return subprocess.call(arg, cwd=str(kok))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources: dict[str, str] = {}

    if args.command == "calistir":
        return komut_calistir(args)

    if args.command == "bytecode":
        return komut_bytecode(args)

    if args.command == "ac":
        return ghb_calistir.calistir(args.file.resolve())

    if args.command == "api":
        return ide_api.komut(args.islem,
                             str(args.file) if args.file else None)

    if args.command == "ide":
        return komut_ide(args)

    if args.command in ("uzanti-kur", "uzanti-kaldir", "uzanti-durum"):
        return komut_uzanti(args)

    if args.command == "ozdenetim":
        return komut_ozdenetim(args)

    if args.command == "fmt":
        return komut_fmt(args)

    try:
        compilation = compile_file(args.file, sources,
                                   kutuphane=getattr(args, "kutuphane", False))
    except NarError as err:
        return fail(err, sources)
    except FileNotFoundError:
        print(f"hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1

    if args.command == "check":
        uyarilar = compilation.checker.warnings
        for u in uyarilar:
            kaynak = sources.get(u.span.filename) if u.span else None
            print(u.render(kaynak), file=sys.stderr)
            print(file=sys.stderr)
        if uyarilar:
            print(f"tamam: {args.file} — hata yok, {len(uyarilar)} uyarı")
        else:
            print(f"tamam: {args.file} — hata yok")
        return 0

    target = getattr(args, "target", "js")
    title = args.file.stem

    if target == "masaustu":
        if args.command == "emit":
            sys.stdout.write(compilation.to_js())
            return 0
        hedef = args.out or (args.file.parent / "cikti" / title)
        dosyalar = paketle(compilation.to_js(), Path(hedef), title, args.file.name)
        print(f"masaüstü uygulaması yazıldı: {hedef}")
        for d in dosyalar:
            print(f"  {d.name}")
        print()
        print(f"çalıştırmak için:  {Path(hedef) / 'baslat.cmd'}")
        return 0

    if target == "narb":
        program = bytecode_uretici.uret(compilation.module, compilation.checker)
        veri = bc.yaz_dosya(program)
        if args.command == "emit":
            sys.stdout.write(bc.dokum(program.ana))
            return 0
        out_path = args.out or args.file.with_suffix(".narb")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(veri)
        print(f"bytecode yazıldı: {out_path}  ({len(veri) // 1024} KB)")
        print(f"çalıştırmak için:  nar calistir {out_path}")
        return 0

    if target == "ghb":
        if args.command == "emit":
            sys.stdout.write(compilation.to_js())
            return 0
        hedef = args.out or (args.file.parent / "cikti" / title)
        paket = ghb_paketle(compilation.to_js(), Path(hedef), title, args.file.name)
        boyut = paket.stat().st_size
        print(f"Nar uygulaması yazıldı: {paket}  ({boyut // 1024} KB)")
        print()
        print(f"çalıştırmak için:  nar ac {paket}")
        print("çift tıklamayla açmak için bir kez:  nar uzanti-kur")
        return 0

    if target == "exe":
        if args.command == "emit":
            sys.stdout.write(compilation.to_js())
            return 0
        hedef = args.out or (args.file.parent / "cikti" / title)
        try:
            exe = exe_paket.paketle(compilation.to_js(), Path(hedef), title,
                                    args.file.name)
        except exe_paket.ExeHatasi as e:
            print(f"hata: {e}", file=sys.stderr)
            return 1
        boyut = exe.stat().st_size
        print(f"Windows uygulaması yazıldı: {exe}  ({boyut // 1024} KB)")
        print()
        print("çift tıklayınca kendi penceresinde açılır; Python ya da Node gerekmez.")
        return 0

    if target == "mobil":
        if args.command == "emit":
            sys.stdout.write(compilation.to_js())
            return 0
        hedef = args.out or (args.file.parent / "cikti" / (title + "-mobil"))
        dosyalar = mobil_paketle(compilation.to_js(), Path(hedef), title, args.file.name)
        print(f"mobil proje yazıldı: {hedef}")
        for d in dosyalar:
            print(f"  {d.relative_to(Path(hedef))}")
        print()
        print("önce tarayıcıda dene:  " + str(Path(hedef) / "www" / "index.html"))
        print("Android için:          npm install && npx cap add android")
        print(f"ayrıntılar:            {Path(hedef) / 'BENIOKU.md'}")
        return 0

    output = to_html(compilation, title) if target == "web" else compilation.to_js()

    if args.command == "emit":
        sys.stdout.write(output)
        return 0

    if args.command == "build":
        suffix = ".html" if target == "web" else ".js"
        out_path = args.out or args.file.with_suffix(suffix)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"yazıldı: {out_path}")
        return 0

    # run
    node = shutil.which("node")
    if node is None:
        print("hata: 'node' bulunamadı. Node.js kurulu olmalı.", file=sys.stderr)
        return 1

    build_dir = args.file.parent / ".narbuild"
    build_dir.mkdir(exist_ok=True)
    script = build_dir / (args.file.stem + ".js")
    script.write_text(compilation.to_js(), encoding="utf-8")

    result = subprocess.run([node, str(script)])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
