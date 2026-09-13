"""Düzenleyicinin derleyiciden istediği her şey — tek yerde.

`ide/sunucu.py` bu modülü doğrudan çağırır (süreç içinde, ~0.2 ms).
`nar api` komutu aynı işlevleri komut satırından JSON olarak verir; Nar
ile yazılmış sunucu (`araclar/ide_sunucusu.nar`) onu kullanır. İki
sunucunun aynı yanıtı vermesi böyle garanti altında: ortak kod yolu.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import nar_ast as A
from .backends import js as js_backend
from .checker import BUILTIN_NAMES, Checker
from .diagnostics import NarError
from .driver import compile_source
from .lexer import KEYWORDS
from .parser import parse

NODE = shutil.which("node")
ZAMAN_ASIMI = 10  # saniye


def hata_sozlugu(err: NarError, kaynak: str) -> dict:
    return {
        "mesaj": err.message,
        "satir": err.span.line if err.span else None,
        "sutun": err.span.col if err.span else None,
        "uzunluk": err.span.length if err.span else 1,
        "ipucu": err.hint,
        "gosterim": err.render(kaynak),
    }


def uyarilar(checker: "Checker | None", kaynak: str) -> list[dict]:
    """Denetçinin uyarılarını sözlük listesine çevirir."""
    if checker is None:
        return []
    return [dict(hata_sozlugu(u, kaynak), seviye="uyari") for u in checker.warnings]


_son_uyarilar: list[dict] = []


def son_uyarilar() -> list[dict]:
    """Son `derle` çağrısının ürettiği uyarılar."""
    return _son_uyarilar


def derle(kaynak: str, ad: str = "duzenleyici.nar", yol: "Path | None" = None):
    """(js_kodu, hata_sozlugu) döndürür; biri her zaman None'dur.

    `yol` verilirse metin o konumdaki dosyaymış gibi derlenir: içe
    aktarmalar o klasöre göre çözülür ve kütüphanedeki adlar tanınır.
    Verilmezse içe aktarma çözülemez — o durumda tek bir açık hata verilir,
    yoksa kütüphanedeki her ad "tanımsız isim" diye görünür ve düzeltme
    önerileri saçmalar.

    Hata sözlüğü ilk hatayı taşır; `hepsi` alanında tüm hatalar bulunur.
    Uyarılar `son_uyarilar()` ile ayrıca alınır.
    """
    global _son_uyarilar
    _son_uyarilar = []
    checker = None
    try:
        if yol is not None:
            derleme = compile_source(kaynak, yol)
            _son_uyarilar = uyarilar(derleme.checker, kaynak)
            return derleme.to_js(), None
        module = parse(kaynak, ad)
        ilk_iceri = next((i for i in module.items if isinstance(i, A.Import)), None)
        if ilk_iceri is not None:
            raise NarError(
                f"içe aktarma çözülemedi: '{ilk_iceri.path}'",
                ilk_iceri.span,
                hint="dosyayı kaydet; içe aktarma kayıtlı dosyanın "
                     "klasörüne göre aranır",
            )
        checker = Checker(module, kaynak)
        checker.check()
        _son_uyarilar = uyarilar(checker, kaynak)
        return js_backend.generate(module, checker), None
    except NarError as err:
        # Hata olsa da toplanan uyarılar kaybolmasın.
        _son_uyarilar = uyarilar(checker, kaynak)
        sozluk = hata_sozlugu(err, kaynak)
        hepsi = getattr(err, "errors", None)
        sozluk["hepsi"] = ([hata_sozlugu(h, kaynak) for h in hepsi]
                           if hepsi else [dict(sozluk)])
        sozluk["adet"] = len(sozluk["hepsi"])
        if sozluk["adet"] > 1:
            sozluk["gosterim"] = "\n\n".join(h["gosterim"] for h in sozluk["hepsi"])
        return None, sozluk
    except RecursionError:
        return None, {
            "mesaj": "program çok derin iç içe geçmiş (özyineleme sınırı)",
            "satir": None, "sutun": None, "uzunluk": 1, "ipucu": None,
            "gosterim": "hata: program çok derin iç içe geçmiş",
        }


def calistir(kaynak: str, yol: "Path | None" = None) -> dict:
    kod, hata = derle(kaynak, yol=yol)
    if hata is not None:
        return {"durum": "derleme-hatasi", "hata": hata, "cikti": ""}

    if NODE is None:
        return {
            "durum": "ortam-hatasi",
            "cikti": "",
            "hata": {"mesaj": "'node' bulunamadı; Node.js kurulu olmalı",
                     "satir": None, "sutun": None, "uzunluk": 1,
                     "ipucu": None, "gosterim": "hata: 'node' bulunamadı"},
        }

    with tempfile.TemporaryDirectory() as tmp:
        betik = Path(tmp) / "program.js"
        betik.write_text(kod, encoding="utf-8")
        try:
            sonuc = subprocess.run(
                [NODE, str(betik)], capture_output=True, text=True,
                encoding="utf-8", timeout=ZAMAN_ASIMI,
            )
        except subprocess.TimeoutExpired:
            return {
                "durum": "zaman-asimi",
                "cikti": f"Program {ZAMAN_ASIMI} saniyede bitmedi ve durduruldu.\n"
                         "Sonsuz döngü olabilir mi?",
                "hata": None,
            }

    return {
        "durum": "tamam" if sonuc.returncode == 0 else "calisma-hatasi",
        "cikti": sonuc.stdout,
        "stderr": sonuc.stderr,
        "hata": None,
    }


def kelime_sozlugu() -> list[dict]:
    """Kod önerisi sözlüğü: anahtar kelimeler, yerleşikler, metotlar.

    Metot arity'si üreteç tablolarındaki `{n}` yer tutucularından
    çıkarılır; ayrı bir liste tutulsaydı tabloyla ayrışırdı.
    """
    kelimeler: list[dict] = []
    for ad in sorted(KEYWORDS):
        kelimeler.append({"ad": ad, "tur": "anahtar", "arg": 0})
    for ad in sorted(BUILTIN_NAMES):
        kelimeler.append({"ad": ad, "tur": "yerlesik", "arg": 1})

    tablolar = {
        "metin": js_backend.STRING_METHODS,
        "liste": js_backend.LIST_METHODS,
        "eşleme": js_backend.MAP_METHODS,
        "öğe": js_backend.ELEMENT_METHODS,
        "olay": js_backend.OLAY_METHODS,
    }
    gorulen: set[str] = set()
    for sahip, tablo in tablolar.items():
        for ad, sablon in tablo.items():
            if ad in gorulen:
                continue
            gorulen.add(ad)
            arg = len(set(re.findall(r"\{(\d+)\}", sablon))) - 1
            kelimeler.append({"ad": ad, "tur": "metot", "arg": max(0, arg),
                              "sahip": sahip})
    return kelimeler


# --- komut satırı köprüsü -------------------------------------------------
#
# `nar api <islem> [dosya]` — sonucu tek satır JSON olarak stdout'a yazar.
# Nar ile yazılmış sunucu bu köprüyü kullanır; başka bir dilin çalışma
# zamanına ihtiyaç duymadan derleyiciye ulaşır.

ISLEMLER = ("denetle", "uret", "calistir", "kelimeler", "araclar")


def komut(islem: str, dosya: str | None, taban: str | None = None) -> int:
    """`nar api` alt komutu.

    `dosya` denetlenecek metni taşır; düzenleyiciler kaydedilmemiş tamponu
    geçici bir dosyaya yazıp burayı gösterir. `taban` ise metnin gerçekte
    ait olduğu yol — içe aktarmalar ona göre çözülür. Verilmezse geçici
    dosyanın klasörü kullanılır ve içe aktarmalar bulunamaz.
    """
    if islem not in ISLEMLER:
        print(json.dumps({"hata": f"bilinmeyen işlem: {islem}"}), flush=True)
        return 2

    if islem == "kelimeler":
        print(json.dumps({"kelimeler": kelime_sozlugu()}, ensure_ascii=False),
              flush=True)
        return 0

    if islem == "araclar":
        # Düzenleyicinin davranışı (araclar/ide_uygulamasi.nar) kütüphane
        # olarak derlenir. JSON değil, düz JavaScript yazılır: sunucu bunu
        # olduğu gibi tarayıcıya verir.
        from .driver import compile_file
        kok = Path(__file__).resolve().parent.parent
        kaynak = kok / "araclar" / "ide_uygulamasi.nar"
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
        print(compile_file(kaynak, kutuphane=True).to_js(), flush=True)
        return 0

    # Kaynak dosyadan okunur; stdin kullanmak Windows'ta kodlama sürprizi
    # çıkarıyor, dosya yolu her ortamda aynı davranıyor.
    if not dosya:
        print(json.dumps({"hata": "kaynak dosya verilmedi"}), flush=True)
        return 2
    try:
        kaynak = Path(dosya).read_text(encoding="utf-8")
    except OSError as e:
        print(json.dumps({"hata": f"dosya okunamadı: {e}"}), flush=True)
        return 2

    konum = Path(taban) if taban else Path(dosya)

    if islem == "denetle":
        _, hata = derle(kaynak, yol=konum)
        yanit = {"hata": hata, "uyarilar": son_uyarilar()}
    elif islem == "uret":
        kod, hata = derle(kaynak, yol=konum)
        yanit = {"kod": kod or "", "hata": hata}
    else:
        yanit = calistir(kaynak, yol=konum)
        yanit["uyarilar"] = son_uyarilar()

    print(json.dumps(yanit, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(komut(sys.argv[1] if len(sys.argv) > 1 else "",
                   sys.argv[2] if len(sys.argv) > 2 else None,
                   sys.argv[3] if len(sys.argv) > 3 else None))
