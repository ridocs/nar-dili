"""Nar IDE — masaüstü uygulaması.

Yerel sunucuyu arka planda başlatır ve kendi penceresinde açar; tarayıcı
sekmesi değil, görev çubuğunda kendi yeri olan bir uygulama penceresidir.

Pencere için sırayla şunlar denenir:
  1. pywebview  — gerçek yerel pencere (Windows'ta Edge WebView2)
  2. Edge/Chrome `--app` — kurulum gerektirmez, adres çubuğu olmayan pencere
  3. Normal tarayıcı sekmesi — son çare

Çalıştırma:
    python ide/masaustu.py
    ide.cmd
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sunucu import CALISMALAR, Islem  # noqa: E402
from narc import __version__  # noqa: E402

BASLIK = f"Nar IDE {__version__}"


def sunucu_baslat() -> tuple[ThreadingHTTPServer, int]:
    """Boş bir portta sunucuyu arka planda başlatır."""
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Islem)
    port = sunucu.server_address[1]
    is_parcacigi = threading.Thread(target=sunucu.serve_forever, daemon=True)
    is_parcacigi.start()
    return sunucu, port


def _tarayici_uygulama_yolu() -> str | None:
    """Edge ya da Chrome'un çalıştırılabilir yolunu bulur."""
    adaylar = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for yol in adaylar:
        if yol and Path(yol).exists():
            return yol
    for ad in ("msedge", "google-chrome", "chromium", "chrome"):
        bulunan = shutil.which(ad)
        if bulunan:
            return bulunan
    return None


def pencere_ac_pywebview(adres: str, genislik: int, yukseklik: int) -> bool:
    try:
        import webview  # type: ignore
    except ImportError:
        return False

    webview.create_window(
        BASLIK, adres,
        width=genislik, height=yukseklik,
        min_size=(760, 500),
        text_select=True,
    )
    webview.start()
    return True


def pencere_ac_tarayici_uygulamasi(adres: str, genislik: int, yukseklik: int) -> bool:
    uygulama = _tarayici_uygulama_yolu()
    if uygulama is None:
        return False

    profil = KOK / ".narbuild" / "ide-profil"
    profil.mkdir(parents=True, exist_ok=True)
    surec = subprocess.Popen([
        uygulama,
        f"--app={adres}",
        f"--window-size={genislik},{yukseklik}",
        f"--user-data-dir={profil}",
        "--no-first-run",
        "--no-default-browser-check",
    ])
    surec.wait()
    return True


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Nar IDE — masaüstü uygulaması")
    ayristirici.add_argument("--genislik", type=int, default=1320)
    ayristirici.add_argument("--yukseklik", type=int, default=860)
    ayristirici.add_argument("--tarayici", action="store_true",
                             help="yerel pencere yerine normal tarayıcı sekmesi kullan")
    args = ayristirici.parse_args()

    CALISMALAR.mkdir(exist_ok=True)
    sunucu, port = sunucu_baslat()
    adres = f"http://127.0.0.1:{port}/"
    print(f"{BASLIK}\n  {adres}")

    try:
        if args.tarayici:
            webbrowser.open(adres)
            print("  tarayıcı sekmesinde açıldı; kapatmak için Ctrl+C")
            while True:
                time.sleep(3600)

        if pencere_ac_pywebview(adres, args.genislik, args.yukseklik):
            return 0
        print("  (pywebview yok — tarayıcının uygulama penceresi kullanılıyor)")
        if pencere_ac_tarayici_uygulamasi(adres, args.genislik, args.yukseklik):
            return 0

        print("  (uygun pencere bulunamadı — normal sekmede açılıyor)")
        webbrowser.open(adres)
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nkapatılıyor")
    finally:
        sunucu.shutdown()
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
