"""Belgeler sitesini üretir.

Her örneği gerçekten derler ve Node ile çalıştırır; sayfadaki çıktılar
elle yazılmaz, üretim sırasında ölçülür. Bir örnek beklenmedik biçimde
kırılırsa üretim hata verip durur — yani site her zaman çalışan kod gösterir.

Çalıştırma:
    python site/uret.py                 -> cikti/site/index.html
    python site/uret.py --cikti yol.html
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import __version__  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.backends import js as js_backend  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.renk import RenkHatasi, renklendir_toplu  # noqa: E402
from narc.parser import parse  # noqa: E402

from icerik import (  # noqa: E402
    ALT_BASLIK, BASLIK, BOLUMLER, GIRIS, NASIL_CALISTIRILIR, NOT_SARMAL, REFERANS,
)

NODE = shutil.which("node")

# Üst düzeyde yazılması gereken bildirimler; kod bunlardan birini içeriyorsa
# `fn main()` içine sarılamaz.
UST_DUZEY = re.compile(r"^\s*(fn|struct|enum|type|import)\b", re.MULTILINE)


# ------------------------------------------------------------------ çalıştırma
def calistirilacak_kaynak(konu: dict) -> str:
    if konu.get("tam"):
        return konu["tam"]
    kod = konu["kod"]
    if UST_DUZEY.search(kod):
        return kod
    govde = "\n".join("  " + s if s.strip() else s for s in kod.splitlines())
    return "fn main() {\n" + govde + "\n}\n"


def ornegi_calistir(konu: dict) -> tuple[str, bool]:
    """(çıktı, hata_mı) döndürür."""
    kaynak = calistirilacak_kaynak(konu)

    try:
        module = parse(kaynak, konu["id"] + ".nar")
        checker = Checker(module, kaynak)
        checker.check()
        kod = js_backend.generate(module, checker)
    except NarError as err:
        return err.render(kaynak), True

    if NODE is None:
        raise SystemExit("hata: 'node' bulunamadı; site üretilemez")

    with tempfile.TemporaryDirectory() as tmp:
        betik = Path(tmp) / "program.js"
        betik.write_text(kod, encoding="utf-8")
        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
        )
    cikti = (sonuc.stdout + sonuc.stderr).strip()
    return cikti, sonuc.returncode != 0


# ----------------------------------------------------------------- kontrast
def _kanal(deger: float) -> float:
    d = deger / 255
    return d / 12.92 if d <= 0.04045 else ((d + 0.055) / 1.055) ** 2.4


def luminans(hex_renk: str) -> float:
    h = hex_renk.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _kanal(r) + 0.7152 * _kanal(g) + 0.0722 * _kanal(b)


def kontrast(on: str, arka: str) -> float:
    a, b = luminans(on), luminans(arka)
    parlak, koyu = max(a, b), min(a, b)
    return (parlak + 0.05) / (koyu + 0.05)


# Sayfa paleti — açık tema. Kontrastlar üretim sırasında doğrulanır.
PALET = {
    "zemin": "#FDFCFB",
    "yuzey": "#FFFFFF",
    "kod_zemin": "#F6F3F1",
    "cikti_zemin": "#F3F5F4",
    "metin": "#1C1917",
    "metin_soluk": "#5F5751",
    "kenar": "#E7E1DD",
    "vurgu": "#A32A2F",
    "vurgu_zemin": "#FBF0F0",
    "hata": "#9F1239",
}

SOZDIZIMI = {
    "n-kw": "#7A2D8F",
    "n-tip": "#1B4FA8",
    "n-metin": "#15693A",
    "n-sayi": "#9A4A05",
    "n-yorum": "#736B65",  # 4.73:1 — daha açığı AA eşiğini geçmiyor (hesaplandı)
    "n-yerlesik": "#0B6473",
    "n-fn": "#2B2521",
    "n-op": "#6B635D",
}


def kontrastlari_dogrula() -> list[str]:
    """Metin renklerinin zeminlerine göre WCAG AA eşiğini geçtiğini doğrular."""
    uyarilar: list[str] = []

    def kontrol(ad: str, on: str, arka: str, esik: float) -> None:
        oran = kontrast(on, arka)
        if oran < esik:
            uyarilar.append(f"{ad}: {oran:.2f}:1 (en az {esik} olmalı)")

    kontrol("gövde metni", PALET["metin"], PALET["zemin"], 4.5)
    kontrol("soluk metin", PALET["metin_soluk"], PALET["zemin"], 4.5)
    kontrol("vurgu", PALET["vurgu"], PALET["zemin"], 4.5)
    kontrol("hata", PALET["hata"], PALET["zemin"], 4.5)
    for ad, renk in SOZDIZIMI.items():
        kontrol(f"sözdizimi {ad}", renk, PALET["kod_zemin"], 4.5)
    return uyarilar


# --------------------------------------------------------------------- HTML
# Renklendirme, Nar ile yazılmış renklendiriciye yaptırılır (IDE ile aynı
# kaynak). Node sürecini her blok için açmamak adına hepsi bir kerede
# renklendirilip burada saklanır.
_RENKLER: dict[str, str] = {}


def renkleri_hazirla() -> None:
    kaynaklar = []
    for bolum in BOLUMLER:
        for konu in bolum["konular"]:
            kaynaklar.append(konu["kod"])
    benzersiz = list(dict.fromkeys(kaynaklar))
    for kaynak, boyali in zip(benzersiz, renklendir_toplu(benzersiz)):
        _RENKLER[kaynak] = boyali


def renklendir(kaynak: str) -> str:
    if kaynak not in _RENKLER:
        _RENKLER[kaynak] = renklendir_toplu([kaynak])[0]
    return _RENKLER[kaynak]


def kod_blogu(kaynak: str, dil_etiketi: str = "nar") -> str:
    # Nar dışındaki bloklar (kabuk komutları) renklendirilmez: Nar
    # renklendiricisi onları yanlış boyar.
    govde = renklendir(kaynak) if dil_etiketi == "nar" else html.escape(kaynak)
    return (
        '<div class="kod-kutu">'
        f'<button class="kopyala" type="button" data-kod="{html.escape(kaynak)}">kopyala</button>'
        f'<pre class="kod" data-dil="{dil_etiketi}"><code>{govde}</code></pre>'
        "</div>"
    )


def cikti_blogu(cikti: str, hata: bool) -> str:
    if not cikti:
        return ""
    etiket = "hata mesajı" if hata else "çıktı"
    sinif = "cikti hatali" if hata else "cikti"
    return (
        f'<div class="{sinif}"><span class="cikti-etiket">{etiket}</span>'
        f"<pre><code>{html.escape(cikti)}</code></pre></div>"
    )


def konu_html(konu: dict) -> str:
    parcalar = [
        f'<article class="konu" id="{konu["id"]}">',
        f'<h3><a class="capa" href="#{konu["id"]}">{html.escape(konu["baslik"])}</a></h3>',
        f'<div class="aciklama">{konu["aciklama"].strip()}</div>',
        kod_blogu(konu["kod"], konu.get("dil", "nar")),
    ]

    if konu.get("calistirma", True):
        cikti, hata = ornegi_calistir(konu)
        bekleniyor = konu.get("beklenen_hata", False)
        if hata != bekleniyor:
            durum = "hata verdi" if hata else "hata vermesi gerekirken çalıştı"
            raise SystemExit(
                f"'{konu['id']}' örneği {durum}:\n{cikti}"
            )
        parcalar.append(cikti_blogu(cikti, hata))

    if konu.get("not"):
        parcalar.append(f'<p class="not">{konu["not"]}</p>')

    parcalar.append("</article>")
    return "\n".join(parcalar)


def referans_html() -> str:
    parcalar = ['<section class="bolum" id="referans">', "<h2>Hızlı başvuru</h2>"]
    for tablo in REFERANS:
        parcalar.append('<div class="ref-grup">')
        parcalar.append(f'<h3>{html.escape(tablo["baslik"])}</h3>')
        parcalar.append(f'<p class="aciklama">{tablo["aciklama"]}</p>')
        parcalar.append('<table class="ref"><tbody>')
        for ad, acik in tablo["satirlar"]:
            parcalar.append(
                f'<tr><td><code>{html.escape(ad)}</code></td>'
                f"<td>{html.escape(acik)}</td></tr>"
            )
        parcalar.append("</tbody></table></div>")
    parcalar.append("</section>")
    return "\n".join(parcalar)


def icindekiler_html() -> str:
    # `details` ile sarılır: dar ekranda katlanır, geniş ekranda hep açıktır.
    parcalar = [
        '<nav class="icindekiler" aria-label="İçindekiler">',
        '<details class="ic-katla" open><summary>İçindekiler</summary>',
    ]
    for bolum in BOLUMLER:
        parcalar.append(f'<div class="ic-grup"><span class="ic-baslik">{html.escape(bolum["baslik"])}</span><ul>')
        for konu in bolum["konular"]:
            parcalar.append(
                f'<li><a href="#{konu["id"]}">{html.escape(konu["baslik"])}</a></li>'
            )
        parcalar.append("</ul></div>")
    parcalar.append(
        '<div class="ic-grup"><span class="ic-baslik">Başvuru</span><ul>'
        '<li><a href="#referans">Hızlı başvuru</a></li></ul></div>'
    )
    parcalar.append("</details></nav>")
    return "\n".join(parcalar)


def stil() -> str:
    sozdizimi_kurallari = "\n".join(
        f"  .{sinif} {{ color: {renk}; }}" for sinif, renk in SOZDIZIMI.items()
    )
    return f"""
:root {{
  --zemin: {PALET['zemin']};
  --yuzey: {PALET['yuzey']};
  --kod-zemin: {PALET['kod_zemin']};
  --cikti-zemin: {PALET['cikti_zemin']};
  --metin: {PALET['metin']};
  --metin-soluk: {PALET['metin_soluk']};
  --kenar: {PALET['kenar']};
  --vurgu: {PALET['vurgu']};
  --vurgu-zemin: {PALET['vurgu_zemin']};
  --hata: {PALET['hata']};
  --tek: ui-monospace, "SFMono-Regular", "Menlo", "Consolas", monospace;
  --govde: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color-scheme: light;
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  background: var(--zemin);
  color: var(--metin);
  font-family: var(--govde);
  font-size: 16px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}}

a {{ color: var(--vurgu); }}

code {{
  font-family: var(--tek);
  font-size: 0.9em;
}}

.aciklama code, .not code, td code {{
  background: var(--kod-zemin);
  border: 1px solid var(--kenar);
  border-radius: 4px;
  padding: 0.1em 0.35em;
}}

/* --- üst başlık --- */
.ust {{
  border-bottom: 1px solid var(--kenar);
  background: var(--yuzey);
}}

.ust-ic {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 44px 24px 36px;
}}

.marka {{
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}}

.marka h1 {{
  margin: 0;
  font-size: 34px;
  letter-spacing: -0.02em;
  color: var(--vurgu);
}}

.surum {{
  font-family: var(--tek);
  font-size: 12px;
  color: var(--metin-soluk);
  border: 1px solid var(--kenar);
  border-radius: 999px;
  padding: 2px 10px;
}}

.ust p.alt {{
  margin: 10px 0 0;
  font-size: 18px;
  color: var(--metin-soluk);
  max-width: 62ch;
}}

.ust-grid {{
  margin-top: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 430px);
  gap: 44px;
  align-items: start;
}}

.giris {{
  margin: 0;
  max-width: 60ch;
}}

.ust-grid .not {{ margin-top: 14px; }}

.baslangic-kutu {{
  background: var(--vurgu-zemin);
  border: 1px solid var(--kenar);
  border-radius: 10px;
  padding: 18px 20px;
  max-width: 66ch;
}}

.baslangic-kutu h2 {{
  margin: 0 0 8px;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--vurgu);
}}

.baslangic-kutu p {{ margin: 8px 0; }}

pre.komut {{
  background: var(--yuzey);
  border: 1px solid var(--kenar);
  border-radius: 6px;
  padding: 12px 14px;
  overflow-x: auto;
  margin: 10px 0;
}}

pre.komut code {{ font-size: 13px; }}

/* --- yerleşim --- */
.kabuk {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 24px 96px;
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  gap: 52px;
  align-items: start;
}}

.icindekiler {{
  position: sticky;
  top: 20px;
  padding-top: 36px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  scrollbar-width: thin;
  font-size: 14px;
}}

.ic-katla > summary {{ display: none; }}

.ic-grup {{ margin-bottom: 20px; }}

.ic-baslik {{
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--metin-soluk);
  margin-bottom: 7px;
}}

.icindekiler ul {{
  list-style: none;
  margin: 0;
  padding: 0;
  border-left: 1px solid var(--kenar);
}}

.icindekiler li a {{
  display: block;
  padding: 3px 0 3px 12px;
  margin-left: -1px;
  border-left: 2px solid transparent;
  color: var(--metin);
  text-decoration: none;
}}

.icindekiler li a:hover {{
  color: var(--vurgu);
  border-left-color: var(--vurgu);
}}

.icerik {{ padding-top: 36px; min-width: 0; }}

.bolum {{ margin-bottom: 8px; }}

.bolum > h2 {{
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--vurgu);
  margin: 48px 0 4px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--kenar);
}}

.konu {{ margin: 34px 0 0; }}

.konu h3 {{
  font-size: 21px;
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}}

.konu h3 a.capa {{
  color: var(--metin);
  text-decoration: none;
}}

.konu h3 a.capa:hover {{ color: var(--vurgu); }}
.konu h3 a.capa:hover::after {{
  content: " #";
  color: var(--kenar);
}}

.aciklama {{ max-width: 68ch; }}
.aciklama p {{ margin: 8px 0; }}
.aciklama ul {{ margin: 8px 0; padding-left: 22px; }}
.aciklama li {{ margin: 4px 0; }}

/* --- kod --- */
.kod-kutu {{
  position: relative;
  margin: 14px 0 0;
}}

pre.kod {{
  background: var(--kod-zemin);
  border: 1px solid var(--kenar);
  border-radius: 8px 8px 0 0;
  padding: 16px 18px;
  margin: 0;
  overflow-x: auto;
  font-size: 13.5px;
  line-height: 1.6;
  tab-size: 2;
}}

pre.kod code {{ font-size: inherit; }}

.kopyala {{
  position: absolute;
  top: 8px;
  right: 10px;
  background: var(--yuzey);
  border: 1px solid var(--kenar);
  border-radius: 5px;
  color: var(--metin-soluk);
  font-family: var(--govde);
  font-size: 11px;
  padding: 3px 9px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.12s;
}}

.kod-kutu:hover .kopyala,
.kopyala:focus-visible {{ opacity: 1; }}
.kopyala:hover {{ color: var(--vurgu); border-color: var(--vurgu); }}

{sozdizimi_kurallari}
  .n-yorum {{ font-style: italic; }}

/* --- çıktı --- */
.cikti {{
  background: var(--cikti-zemin);
  border: 1px solid var(--kenar);
  border-top: none;
  border-radius: 0 0 8px 8px;
  padding: 12px 18px 14px;
}}

.cikti.hatali {{
  background: #FCF3F4;
  border-left: 3px solid var(--hata);
}}

.cikti-etiket {{
  display: block;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--metin-soluk);
  margin-bottom: 6px;
}}

.cikti.hatali .cikti-etiket {{ color: var(--hata); }}

.cikti pre {{
  margin: 0;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}}

.not {{
  font-size: 14px;
  color: var(--metin-soluk);
  max-width: 68ch;
}}

/* --- referans --- */
.ref-grup {{ margin: 28px 0 0; }}
.ref-grup h3 {{ font-size: 19px; margin: 0 0 4px; }}

table.ref {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  font-size: 14.5px;
}}

table.ref td {{
  border-top: 1px solid var(--kenar);
  padding: 7px 10px 7px 0;
  vertical-align: top;
}}

table.ref td:first-child {{
  width: 40%;
  white-space: nowrap;
}}

table.ref td:first-child code {{
  background: none;
  border: none;
  padding: 0;
  color: var(--metin);
}}

table.ref td:last-child {{ color: var(--metin-soluk); }}

/* --- alt bilgi --- */
.alt {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 24px 60px;
  border-top: 1px solid var(--kenar);
  color: var(--metin-soluk);
  font-size: 13.5px;
}}

/* --- dar ekran --- */
@media (max-width: 900px) {{
  .ust-grid {{
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
  }}
  .kabuk {{
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }}
  .icindekiler {{
    position: static;
    max-height: none;
    padding-top: 20px;
    border-bottom: 1px solid var(--kenar);
    padding-bottom: 12px;
  }}
  .ic-katla > summary {{
    display: block;
    cursor: pointer;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--vurgu);
    padding: 8px 0;
    list-style: none;
  }}
  .ic-katla > summary::-webkit-details-marker {{ display: none; }}
  .ic-katla > summary::after {{
    content: " ▾";
    letter-spacing: 0;
  }}
  .ic-katla[open] > summary::after {{ content: " ▴"; }}
  .ic-katla[open] > summary {{ margin-bottom: 12px; }}
  .ic-katla[open] {{ columns: 2; column-gap: 24px; }}
  .ic-katla[open] > summary {{ column-span: all; }}
  .ic-grup {{ break-inside: avoid; }}
  .kopyala {{ opacity: 1; }}
  .marka h1 {{ font-size: 28px; }}
  .ust p.alt {{ font-size: 16px; }}
  table.ref td:first-child {{ white-space: normal; width: 45%; }}
}}

@media (max-width: 520px) {{
  .ic-katla[open] {{ columns: 1; }}
  .ust-ic {{ padding: 32px 20px 28px; }}
  .kabuk {{ padding: 0 20px 72px; }}
  .alt {{ padding: 24px 20px 48px; }}
}}
"""


SCRIPT = """
// İçindekiler dar ekranda katlı başlar, geniş ekranda hep açık kalır.
(function () {
  var katla = document.querySelector('.ic-katla');
  if (!katla) return;
  var sorgu = window.matchMedia('(max-width: 900px)');
  var elle = false;
  katla.addEventListener('toggle', function () { elle = true; });
  function ayarla() {
    if (!elle) katla.open = !sorgu.matches;
  }
  ayarla();
  sorgu.addEventListener('change', function () { elle = false; ayarla(); });
})();

document.querySelectorAll('.kopyala').forEach(function (dugme) {
  dugme.addEventListener('click', function () {
    var kod = dugme.getAttribute('data-kod');
    navigator.clipboard.writeText(kod).then(function () {
      var eski = dugme.textContent;
      dugme.textContent = 'kopyalandı';
      setTimeout(function () { dugme.textContent = eski; }, 1200);
    }).catch(function () {
      dugme.textContent = 'kopyalanamadı';
    });
  });
});
"""


def sayfa_uret(artifact: bool = False) -> str:
    """Sayfayı üretir. `artifact=True` ise `<html>/<head>/<body>` sarmalı
    olmadan, yayın ortamının kendi iskeletine gömülecek biçimde döner."""
    uyarilar = kontrastlari_dogrula()
    if uyarilar:
        raise SystemExit("kontrast yetersiz:\n  " + "\n  ".join(uyarilar))

    govde: list[str] = []
    for bolum in BOLUMLER:
        govde.append(f'<section class="bolum" id="{bolum["id"]}">')
        govde.append(f'<h2>{html.escape(bolum["baslik"])}</h2>')
        for konu in bolum["konular"]:
            govde.append(konu_html(konu))
        govde.append("</section>")
    govde.append(referans_html())

    # `lang="tr"` kök sarmalayıcıda: `text-transform: uppercase` Türkçe
    # kurallarına göre çalışsın (i → İ). Yayın ortamında <html lang> bize ait
    # olmadığı için bu sarmalayıcı gerekli.
    icerik = f"""<div lang="tr" class="kok">

<header class="ust">
  <div class="ust-ic">
    <div class="marka">
      <h1>{html.escape(BASLIK)}</h1>
      <span class="surum">v{__version__}</span>
    </div>
    <p class="alt">{html.escape(ALT_BASLIK)}</p>
    <div class="ust-grid">
      <div>
        <div class="giris">{GIRIS.strip()}</div>
        <p class="not">{NOT_SARMAL}</p>
      </div>
      <div class="baslangic-kutu">
        <h2>Nasıl çalıştırılır</h2>
        {NASIL_CALISTIRILIR.strip()}
      </div>
    </div>
  </div>
</header>

<div class="kabuk">
{icindekiler_html()}
<main class="icerik">
{chr(10).join(govde)}
</main>
</div>

<footer class="alt">
  Bu sayfadaki bütün çıktılar, sayfa üretilirken örnekler gerçekten
  derlenip çalıştırılarak alınmıştır — hiçbiri elle yazılmamıştır.
  Son üretim: {date.today().isoformat()}.
</footer>

</div>"""

    if artifact:
        return (f"<title>Nar Dil Rehberi</title>\n"
                f"<style>{stil()}</style>\n\n{icerik}\n\n<script>{SCRIPT}</script>\n")

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(BASLIK)} — dil rehberi</title>
<meta name="description" content="{html.escape(ALT_BASLIK)}">
<style>{stil()}</style>
</head>
<body>
{icerik}
<script>{SCRIPT}</script>
</body>
</html>
"""


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Nar belgeler sitesini üretir")
    ayristirici.add_argument(
        "--cikti", type=Path, default=KOK / "cikti" / "site" / "index.html",
        help="çıktı HTML dosyası",
    )
    ayristirici.add_argument(
        "--artifact", action="store_true",
        help="Artifact olarak yayımlanacak biçim (html/head/body sarmalayıcısı yok)",
    )
    args = ayristirici.parse_args()

    sayfa = sayfa_uret(artifact=args.artifact)
    args.cikti.parent.mkdir(parents=True, exist_ok=True)
    args.cikti.write_text(sayfa, encoding="utf-8")

    konu_sayisi = sum(len(b["konular"]) for b in BOLUMLER)
    print(f"yazıldı: {args.cikti}")
    print(f"{len(BOLUMLER)} bölüm, {konu_sayisi} konu, {len(sayfa) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
