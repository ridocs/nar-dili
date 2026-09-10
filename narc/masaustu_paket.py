"""`nar build --target masaustu` — Nar programını masaüstü uygulamasına paketler.

Üretilen klasör kendi başına çalışır: içinde programın HTML'i, onu kendi
penceresinde açan bir başlatıcı ve Windows için bir `.cmd` dosyası bulunur.

Pencere için sırayla pywebview, tarayıcının `--app` modu ve normal sekme
denenir; yani ek kurulum olmadan da açılır.
"""

from __future__ import annotations

from pathlib import Path

HTML_SABLONU = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{baslik}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px;
    background: #FDFCFB;
    color: #1C1917;
    font: 14px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
  }}
  #uygulama {{ max-width: 900px; }}
  #cikti {{
    margin-top: 20px;
    font-family: ui-monospace, "SFMono-Regular", "Menlo", "Consolas", monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-word;
    color: #1C1917;
  }}
  #cikti:empty {{ display: none; }}
</style>
</head>
<body>
<div id="uygulama"></div>
<div id="cikti"></div>
<script>
// `print` çıktısı hem konsola hem sayfaya gider.
(function () {{
  var hedef = document.getElementById("cikti");
  var asil = console.log.bind(console);
  console.log = function () {{
    var parcalar = Array.prototype.slice.call(arguments);
    asil.apply(null, parcalar);
    hedef.textContent += parcalar.join(" ") + "\\n";
  }};
}})();
</script>
<script>
{kod}
</script>
</body>
</html>
"""

BASLATICI = '''"""{baslik} — masaüstü başlatıcı.

Bu dosya, yanındaki index.html sayfasını kendi penceresinde açar.
Çalıştırmak için:  python baslat.py     (ya da Windows'ta baslat.cmd)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SAYFA = BURASI / "index.html"
BASLIK = {baslik!r}
GENISLIK = {genislik}
YUKSEKLIK = {yukseklik}


def tarayici_yolu() -> str | None:
    adaylar = [
        os.path.expandvars(r"%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\\Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe"),
    ]
    for yol in adaylar:
        if yol and Path(yol).exists():
            return yol
    for ad in ("msedge", "google-chrome", "chromium", "chrome"):
        bulunan = shutil.which(ad)
        if bulunan:
            return bulunan
    return None


def main() -> int:
    if not SAYFA.exists():
        print(f"hata: {{SAYFA}} bulunamadı")
        return 1

    adres = SAYFA.as_uri()

    # 1) Yerel pencere (en iyi görünüm)
    try:
        import webview  # type: ignore
        webview.create_window(BASLIK, adres, width=GENISLIK, height=YUKSEKLIK,
                              min_size=(480, 360), text_select=True)
        webview.start()
        return 0
    except ImportError:
        pass

    # 2) Tarayıcının uygulama penceresi (adres çubuğu yok)
    uygulama = tarayici_yolu()
    if uygulama is not None:
        profil = BURASI / ".pencere-profili"
        profil.mkdir(exist_ok=True)
        subprocess.run([
            uygulama,
            f"--app={{adres}}",
            f"--window-size={{GENISLIK}},{{YUKSEKLIK}}",
            f"--user-data-dir={{profil}}",
            "--no-first-run",
            "--no-default-browser-check",
        ])
        return 0

    # 3) Son çare
    print("uygun pencere bulunamadı; normal tarayıcıda açılıyor")
    webbrowser.open(adres)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

CMD = """@echo off
REM {baslik} -- desktop launcher
REM Keep this file pure ASCII with CRLF line endings.
setlocal
set "PYTHONIOENCODING=utf-8"
python "%~dp0baslat.py" %*
endlocal
"""

BENIOKU = """# {baslik}

Bu klasör, Nar ile yazılmış bir masaüstü uygulamasıdır.

## Çalıştırmak

| Sistem | Komut |
|---|---|
| Windows | `baslat.cmd` (çift tıkla) |
| Linux / macOS | `python3 baslat.py` |

Gereken tek şey **Python**. Daha iyi bir pencere görünümü için
`pip install pywebview` yapabilirsin; kurulu değilse uygulama yine
tarayıcının uygulama penceresinde açılır.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `index.html` | Programın kendisi (Nar'dan üretilmiş JavaScript gömülü) |
| `baslat.py` | Pencereyi açan başlatıcı |
| `baslat.cmd` | Windows kısayolu |

`index.html` tek başına da tarayıcıda açılabilir.

---
Kaynak: `{kaynak}` · Nar ile üretildi.
"""


def paketle(js_kodu: str, hedef: Path, baslik: str, kaynak_adi: str,
            genislik: int = 1000, yukseklik: int = 700) -> list[Path]:
    """Masaüstü uygulaması klasörünü oluşturur, yazılan dosyaları döndürür."""
    hedef.mkdir(parents=True, exist_ok=True)

    sayfa = hedef / "index.html"
    sayfa.write_text(HTML_SABLONU.format(baslik=baslik, kod=js_kodu), encoding="utf-8")

    baslatici = hedef / "baslat.py"
    baslatici.write_text(
        BASLATICI.format(baslik=baslik, genislik=genislik, yukseklik=yukseklik),
        encoding="utf-8",
    )

    # `.cmd` dosyası cmd.exe'nin kod sayfasında okunur: saf ASCII ve CRLF.
    cmd = hedef / "baslat.cmd"
    ascii_baslik = baslik.encode("ascii", "replace").decode("ascii")
    cmd_metni = CMD.format(baslik=ascii_baslik).replace("\r\n", "\n").replace("\n", "\r\n")
    cmd.write_bytes(cmd_metni.encode("ascii", "replace"))

    benioku = hedef / "BENIOKU.md"
    benioku.write_text(
        BENIOKU.format(baslik=baslik, kaynak=kaynak_adi), encoding="utf-8")

    return [sayfa, baslatici, cmd, benioku]
