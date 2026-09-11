"""Nar Çalıştırıcı — `.ghb` paketlerini açar ve kendi penceresinde gösterir.

Windows'ta `.ghb` uzantısı bu çalıştırıcıya bağlandığında pakete çift
tıklamak uygulamayı başlatır.

Pencere için sırayla üç yol denenir:
  1. pywebview — gerçek yerel pencere (kuruluysa)
  2. Tarayıcının `--app` modu — adres çubuğu olmayan pencere
  3. Normal tarayıcı sekmesi — son çare

Böylece ek kurulum olmadan da çalışır.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

from .ghb_paket import ac, meta_oku


def tarayici_yolu() -> str | None:
    """Uygulama penceresi açabilecek bir tarayıcı bulur."""
    adaylar = [
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for yol in adaylar:
        if yol and Path(yol).exists():
            return yol
    for ad in ("msedge", "google-chrome", "chromium", "chrome", "brave"):
        bulunan = shutil.which(ad)
        if bulunan:
            return bulunan
    return None


def hata_goster(mesaj: str) -> None:
    """Hatayı konsola yazar; konsol yoksa pencereyle bildirir.

    Çift tıklamayla açıldığında konsol olmaz — hata sessizce kaybolmamalı.
    """
    print(f"hata: {mesaj}", file=sys.stderr)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, mesaj, "Nar Çalıştırıcı", 0x10)
        except Exception:
            pass


def calistir(paket: Path, bekle: bool = True) -> int:
    """Paketi açar ve penceresinde gösterir."""
    try:
        meta = meta_oku(paket)
    except (FileNotFoundError, ValueError) as e:
        hata_goster(str(e))
        return 1

    ad = meta.get("ad", paket.stem)
    pencere = meta.get("pencere", {})
    genislik = int(pencere.get("genislik", 1000))
    yukseklik = int(pencere.get("yukseklik", 700))

    # Paket geçici bir klasöre açılır. Uygulama kapanınca silinir; `bekle`
    # kapalıysa (tarayıcı sekmesi) silme işi işletim sistemine bırakılır.
    gecici = Path(tempfile.mkdtemp(prefix="nar-ghb-"))
    try:
        giris = ac(paket, gecici)
    except ValueError as e:
        hata_goster(str(e))
        shutil.rmtree(gecici, ignore_errors=True)
        return 1

    adres = giris.as_uri()

    # 1) Yerel pencere
    try:
        import webview  # type: ignore
        webview.create_window(ad, adres, width=genislik, height=yukseklik,
                              min_size=(480, 360), text_select=True)
        webview.start()
        shutil.rmtree(gecici, ignore_errors=True)
        return 0
    except ImportError:
        pass

    # 2) Tarayıcının uygulama penceresi
    uygulama = tarayici_yolu()
    if uygulama is not None:
        profil = gecici / ".pencere-profili"
        profil.mkdir(exist_ok=True)
        komut = [
            uygulama,
            f"--app={adres}",
            f"--window-size={genislik},{yukseklik}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if bekle:
            subprocess.run(komut)
            shutil.rmtree(gecici, ignore_errors=True)
        else:
            subprocess.Popen(komut)
        return 0

    # 3) Son çare
    webbrowser.open(adres)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        hata_goster("kullanım: nar ac uygulama.ghb")
        return 1
    return calistir(Path(argv[0]).resolve())


if __name__ == "__main__":
    sys.exit(main())
