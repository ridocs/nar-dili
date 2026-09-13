"""Nar IDE — yerel sunucu.

Tarayıcıda çalışan bir düzenleyici sunar; derleme ve çalıştırma bu süreçte
yapılır. Yalnızca 127.0.0.1'e bağlanır, dışarıya açılmaz.

Çalıştırma:
    python ide/sunucu.py            (tarayıcıyı da açar)
    python ide/sunucu.py --port 8900 --tarayici-acma
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import __version__  # noqa: E402
from narc import ide_api  # noqa: E402

ARAYUZ = Path(__file__).resolve().parent / "arayuz.html"
CALISMALAR = KOK / "calismalar"
NODE = shutil.which("node")

# IDE'nin araçları — renklendirici, biçimlendirici ve düzenleme yardımcıları —
# Nar diliyle yazılmıştır. Sunucu onları istendiğinde derleyip servis eder;
# kaynak değişirse kendiliğinden yenilenir.
ARACLAR_NAR = KOK / "araclar" / "ide_uygulamasi.nar"
_araclar_onbellek: dict[str, object] = {"imza": None, "js": ""}

# Sunucunun açıldığı an. `araclar/*.nar` değişince kendiliğinden yenilenir
# ama derleyicinin kendisi (narc/*.py) süreç açılışında bir kez yüklenir:
# sonradan eklenen bir dil özelliği bu sunucuya girmez. Kullanıcı yeni
# sözdizimini deneyip "dil bozuk" sanmasın diye durumu kendimiz söyleriz.
BASLANGIC = time.time()


def derleyici_eskidi() -> bool:
    """Sunucu açıldıktan sonra derleyici kaynağı değiştiyse True."""
    for yol in (KOK / "narc").rglob("*.py"):
        try:
            if yol.stat().st_mtime > BASLANGIC:
                return True
        except OSError:
            pass
    return False


def _araclar_imzasi() -> tuple:
    """Araç kaynaklarının değişme zamanları; biri değişirse yeniden derlenir."""
    zamanlar = []
    for yol in sorted((KOK / "araclar").glob("*.nar")):
        try:
            zamanlar.append((yol.name, yol.stat().st_mtime))
        except OSError:
            pass
    return tuple(zamanlar)


def araclar_js() -> str:
    """`araclar/ide_uygulamasi.nar` dosyasını kütüphane olarak derler."""
    if not ARACLAR_NAR.exists():
        return "/* ide_araclari.nar bulunamadı */"

    imza = _araclar_imzasi()
    if _araclar_onbellek["imza"] == imza and _araclar_onbellek["js"]:
        return _araclar_onbellek["js"]  # type: ignore[return-value]

    try:
        from narc.driver import compile_file
        kod = compile_file(ARACLAR_NAR, kutuphane=True).to_js()
    except NarError as err:
        # Araçlar bozulursa IDE çalışmaya devam etmeli; yalnızca renk gider.
        kod = ("/* Nar araçları derlenemedi:\n"
               + err.render().replace("*/", "* /")
               + "\n*/\n")

    _araclar_onbellek["imza"] = imza
    _araclar_onbellek["js"] = kod
    return kod


# Çalıştırma süresi sınırı: sonsuz döngü tarayıcıyı kilitlemesin.
ZAMAN_ASIMI = 10


# Derleyiciye bakan her şey `narc/ide_api.py` içinde: Nar ile yazılmış
# sunucu da aynı işlevleri `nar api` üzerinden çağırıyor, ikisi ayrışmasın.
derle = ide_api.derle
calistir = ide_api.calistir
kelime_sozlugu = ide_api.kelime_sozlugu
uyarilar = ide_api.uyarilar


def son_uyarilar() -> list[dict]:
    return ide_api.son_uyarilar()


# Dosya ağacındaki gruplar: (klasör, görünen ad). Sıra ağaçtaki sıradır;
# kullanıcının kendi dosyaları en üstte.
AGAC_GRUPLARI = [
    ("calismalar", "Çalışmalarım"),
    ("", "Oyun alanı"),
    ("ornekler", "Örnekler"),
    ("araclar", "Araçlar"),
    ("derleyici", "Derleyici"),
    ("testler/nar", "Testler"),
]


def dosya_listesi() -> list[dict]:
    """Düzenleyicide açılabilecek dosyalar, ağaçtaki grup sırasıyla."""
    dosyalar: list[dict] = []
    for klasor, grup in AGAC_GRUPLARI:
        kok = KOK / klasor if klasor else KOK
        if not kok.exists():
            continue
        for yol in sorted(kok.glob("*.nar")):
            bagil = f"{klasor}/{yol.name}" if klasor else yol.name
            dosyalar.append({"ad": yol.name, "yol": bagil, "grup": grup})
    return dosyalar


def guvenli_yol(bagil: str) -> Path | None:
    """Proje kökünün dışına çıkan yolları reddeder."""
    try:
        hedef = (KOK / bagil).resolve()
    except (OSError, ValueError):
        return None
    if hedef == KOK or KOK not in hedef.parents:
        return None
    if hedef.suffix != ".nar":
        return None
    return hedef


class Islem(BaseHTTPRequestHandler):
    server_version = f"NarIDE/{__version__}"

    def log_message(self, bicim, *args):  # sunucu günlüğünü sessizleştir
        pass

    # ---------------------------------------------------------------- yanıtlar
    def _json(self, veri: dict, kod: int = 200) -> None:
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _metin(self, icerik: str, tur: str = "text/html; charset=utf-8") -> None:
        govde = icerik.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _govde_oku(self) -> dict:
        uzunluk = int(self.headers.get("Content-Length") or 0)
        if uzunluk <= 0 or uzunluk > 2_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    # ------------------------------------------------------------------- GET
    def do_GET(self) -> None:
        yol = self.path.split("?")[0]

        if yol in ("/", "/index.html"):
            self._metin(ARAYUZ.read_text(encoding="utf-8"))
            return

        if yol == "/nar-ide.js":
            self._metin(araclar_js(), "application/javascript; charset=utf-8")
            return

        if yol == "/api/dosyalar":
            self._json({"dosyalar": dosya_listesi(), "surum": __version__})
            return

        if yol == "/api/kelimeler":
            self._json({"kelimeler": kelime_sozlugu()})
            return

        if yol == "/api/dosya":
            from urllib.parse import parse_qs, urlparse
            sorgu = parse_qs(urlparse(self.path).query)
            bagil = (sorgu.get("yol") or [""])[0]
            hedef = guvenli_yol(bagil)
            if hedef is None or not hedef.exists():
                self._json({"hata": "dosya bulunamadı"}, 404)
                return
            self._json({"yol": bagil, "kaynak": hedef.read_text(encoding="utf-8-sig")})
            return

        self._json({"hata": "bulunamadı"}, 404)

    # ------------------------------------------------------------------ POST
    def do_POST(self) -> None:
        yol = self.path.split("?")[0]
        veri = self._govde_oku()
        kaynak = veri.get("kaynak", "")
        # Açık dosyanın yolu: içe aktarmalar buna göre çözülür. Dosya henüz
        # kaydedilmemişse kök varsayılır — kullanıcı `import "araclar/..."`
        # yazdığında komut satırındakiyle aynı şey olsun.
        acik = guvenli_yol(veri.get("yol", "")) or (KOK / "duzenleyici.nar")

        if yol == "/api/calistir":
            self._json(calistir(kaynak, yol=acik))
            return

        if yol == "/api/denetle":
            _, hata = derle(kaynak, yol=acik)
            self._json({"tamam": hata is None, "hata": hata,
                        "uyarilar": list(son_uyarilar()),
                        "eskiSunucu": derleyici_eskidi()})
            return

        if yol == "/api/uretilen":
            kod, hata = derle(kaynak, yol=acik)
            self._json({"kod": kod or "", "hata": hata})
            return

        if yol == "/api/kaydet":
            bagil = veri.get("yol", "")
            hedef = guvenli_yol(bagil)
            if hedef is None:
                self._json({"hata": "bu konuma kaydedilemez"}, 400)
                return
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_text(kaynak, encoding="utf-8")
            self._json({"tamam": True, "yol": bagil})
            return

        self._json({"hata": "bulunamadı"}, 404)


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Nar IDE — yerel düzenleyici")
    ayristirici.add_argument("--port", type=int, default=8777)
    ayristirici.add_argument("--tarayici-acma", action="store_true",
                             help="tarayıcıyı kendiliğinden açma")
    args = ayristirici.parse_args()

    CALISMALAR.mkdir(exist_ok=True)
    adres = f"http://127.0.0.1:{args.port}/"

    sunucu = ThreadingHTTPServer(("127.0.0.1", args.port), Islem)
    print(f"Nar IDE v{__version__}")
    print(f"  {adres}")
    print("  durdurmak için Ctrl+C")
    if NODE is None:
        print("  UYARI: 'node' bulunamadı — programlar çalıştırılamaz")

    if not args.tarayici_acma:
        threading.Timer(0.6, lambda: webbrowser.open(adres)).start()

    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nkapatılıyor")
    finally:
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
