"""`.ghb` — Nar uygulama paketi.

Masaüstü hedefi bir klasör üretiyor: HTML, başlatıcı, benioku. Taşımak
için hepsini bir arada tutmak gerekiyor. `.ghb` bunu tek dosyaya indirger:
çift tıklandığında Nar Çalıştırıcı onu açar.

Biçim ZIP'tir — özel bir şey icat etmeye gerek yok. İçinde:

    nar.json      uygulama adı, sürüm, pencere boyutu, giriş dosyası
    program.js    Nar'dan üretilmiş JavaScript
    index.html    programı çalıştıran sayfa
    varliklar/    isteğe bağlı dosyalar (resim, veri, stil)

ZIP olduğu için içine bakmak da kolay: uzantıyı `.zip` yapıp açmak yeter.
Kapalı bir kutu değil.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

# Paket biçiminin sürümü. Çalıştırıcı bunu okuyup uyumluluğa bakar.
BICIM_SURUMU = 1

HTML_SABLONU = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{baslik}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; }}
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
<script src="program.js"></script>
</body>
</html>
"""


def paketle(js_kodu: str, hedef: Path, baslik: str, kaynak_adi: str,
            genislik: int = 1000, yukseklik: int = 700,
            varliklar: Path | None = None) -> Path:
    """`.ghb` paketini yazar ve yolunu döndürür.

    `varliklar` verilirse o klasörün içeriği pakete `varliklar/` altında
    kopyalanır; program onlara göreli yolla erişebilir.
    """
    hedef = hedef.with_suffix(".ghb")
    hedef.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "bicim": BICIM_SURUMU,
        "ad": baslik,
        "kaynak": kaynak_adi,
        "giris": "index.html",
        "pencere": {"genislik": genislik, "yukseklik": yukseklik},
    }

    with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("nar.json", json.dumps(meta, ensure_ascii=False, indent=2))
        z.writestr("program.js", js_kodu)
        z.writestr("index.html", HTML_SABLONU.format(baslik=baslik))

        if varliklar is not None and varliklar.is_dir():
            for dosya in sorted(varliklar.rglob("*")):
                if dosya.is_file():
                    ic_yol = "varliklar/" + dosya.relative_to(varliklar).as_posix()
                    z.write(dosya, ic_yol)

    return hedef


def meta_oku(paket: Path) -> dict:
    """Paketin `nar.json` içeriğini döndürür.

    Bozuk ya da yanlış sürümlü paketleri burada yakalamak, çalıştırıcının
    anlamsız bir hatayla çökmesinden iyidir.
    """
    if not paket.exists():
        raise FileNotFoundError(f"paket bulunamadı: {paket}")
    if not zipfile.is_zipfile(paket):
        raise ValueError(f"{paket.name} bir Nar paketi değil (ZIP değil)")

    with zipfile.ZipFile(paket) as z:
        if "nar.json" not in z.namelist():
            raise ValueError(f"{paket.name} içinde nar.json yok")
        meta = json.loads(z.read("nar.json").decode("utf-8"))

    bicim = meta.get("bicim", 0)
    if bicim > BICIM_SURUMU:
        raise ValueError(
            f"{paket.name} daha yeni bir Nar sürümüyle üretilmiş "
            f"(biçim {bicim}, bu sürüm {BICIM_SURUMU} okuyor)"
        )
    return meta


def ac(paket: Path, hedef_klasor: Path) -> Path:
    """Paketi klasöre açar ve giriş dosyasının yolunu döndürür."""
    meta = meta_oku(paket)
    hedef_klasor.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(paket) as z:
        # ZIP içindeki yollar güvenilmez: klasör dışına çıkmaya çalışan
        # bir girdi ("../", mutlak yol) diskte istenmeyen yere yazabilir.
        for ad in z.namelist():
            p = Path(ad)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError(f"pakette güvenli olmayan yol: {ad}")
        z.extractall(hedef_klasor)

    return hedef_klasor / meta.get("giris", "index.html")
