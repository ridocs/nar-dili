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
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import __version__  # noqa: E402
from narc.backends import js as js_backend  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.parser import parse  # noqa: E402

ARAYUZ = Path(__file__).resolve().parent / "arayuz.html"
CALISMALAR = KOK / "calismalar"
NODE = shutil.which("node")

# Çalıştırma süresi sınırı: sonsuz döngü tarayıcıyı kilitlemesin.
ZAMAN_ASIMI = 10


def derle(kaynak: str, ad: str = "duzenleyici.nar"):
    """(js_kodu, hata_sozlugu) döndürür; biri her zaman None'dur."""
    try:
        module = parse(kaynak, ad)
        checker = Checker(module, kaynak)
        checker.check()
        return js_backend.generate(module, checker), None
    except NarError as err:
        return None, {
            "mesaj": err.message,
            "satir": err.span.line if err.span else None,
            "sutun": err.span.col if err.span else None,
            "uzunluk": err.span.length if err.span else 1,
            "ipucu": err.hint,
            "gosterim": err.render(kaynak),
        }
    except RecursionError:
        return None, {
            "mesaj": "program çok derin iç içe geçmiş (özyineleme sınırı)",
            "satir": None, "sutun": None, "uzunluk": 1, "ipucu": None,
            "gosterim": "hata: program çok derin iç içe geçmiş",
        }


def calistir(kaynak: str) -> dict:
    kod, hata = derle(kaynak)
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


def dosya_listesi() -> list[dict]:
    """Düzenleyicide açılabilecek dosyalar."""
    dosyalar: list[dict] = []
    for yol in sorted(KOK.glob("*.nar")):
        dosyalar.append({"ad": yol.name, "yol": yol.name, "grup": "Oyun alanı"})
    for yol in sorted((KOK / "ornekler").glob("*.nar")):
        dosyalar.append({"ad": yol.name, "yol": f"ornekler/{yol.name}", "grup": "Örnekler"})
    if CALISMALAR.exists():
        for yol in sorted(CALISMALAR.glob("*.nar")):
            dosyalar.append({"ad": yol.name, "yol": f"calismalar/{yol.name}",
                             "grup": "Çalışmalarım"})
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

        if yol == "/api/dosyalar":
            self._json({"dosyalar": dosya_listesi(), "surum": __version__})
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

        if yol == "/api/calistir":
            self._json(calistir(kaynak))
            return

        if yol == "/api/denetle":
            _, hata = derle(kaynak)
            self._json({"tamam": hata is None, "hata": hata})
            return

        if yol == "/api/uretilen":
            kod, hata = derle(kaynak)
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
