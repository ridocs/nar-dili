"""Belgeler sitesinin görsel katmanı: palet, stil, betik ve ikonlar.

İçerik (`icerik.py`) ve üretim (`uret.py`) burada durmaz; bu dosya yalnız
sayfanın nasıl göründüğünü tarif eder.

## Yön

İki kaynaktan harmanlandı.

**UI/UX Pro Max veritabanı** (yerel, sorgulandı):
- Ürün tipi `API Developer Portal` → birincil stil *Minimalism & Swiss Style*,
  ikincil *Dark Mode (OLED)*; sayfa kalıbı *Quick Start + Interactive Docs* ve
  *Search-First + Hierarchical Navigation*.
- Tipografi eşleşmesi `Developer Mono`: **başlıklar JetBrains Mono**, gövde
  **IBM Plex Sans**. Başlıkların mono olması bu eşleşmenin ayırt edici yanı.
- UX: sabit üst bar içeriği örtmemeli (`scroll-margin-top` ile karşılandı).

**21st.dev** (ham CSS token dökümünden, tahmin değil):
- Nötr merdiven OKLCH aydınlık basamakları: zemin .141, yüzey .21, kenar .274,
  soluk .654, metin .985. Bu basamaklar **Nar'ın hue'suna (30) taşındı** —
  yapı 21st'ten, renk Nar'dan. Sonuç saf gri değil, nara çalan bir mürekkep.
- Yüzen panel gölgesi ve beyaz inset hairline birebir alındı.
- Kenarlık gradyanı, yarıçap merdiveni (`--radius: .5rem` ve türevleri).
- Tek canlı renk yalnız birincil eylemde; gradyanlı pill CTA.
- 48px üst bar, ortada arama + `⌘K` rozeti.
- Yoğun çok sütunlu kategori listesi, sağa yaslı mono sayaçlar.
- Dev hayalet rakamlar — burada süs değil bilgi: rehber sırayla okunmak üzere
  yazıldı, numara o sırayı gösteriyor.

Alınmayan tek imza **split button**: bu duran bir referans sayfası, chevron'un
açacağı bir menü yok. Yalan söyleyen bir arayüz öğesi, eksik bir imzadan kötü.

Kontrastlar üretim sırasında hesaplanır ve eşiği geçmeyen bir renk üretimi
durdurur — yani sitede gözle onaylanmış renk yoktur.
"""

from __future__ import annotations

# --------------------------------------------------------------- kontrast


def _kanal(deger: float) -> float:
    d = deger / 255
    return d / 12.92 if d <= 0.04045 else ((d + 0.055) / 1.055) ** 2.4


def luminans(hex_renk: str) -> float:
    h = hex_renk.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _kanal(r) + 0.7152 * _kanal(g) + 0.0722 * _kanal(b)


def kontrast(on: str, arka: str) -> float:
    a, b = luminans(on), luminans(arka)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


# ------------------------------------------------------------------ palet
# Nötrler 21st.dev'in OKLCH merdiveninden, hue 30'a (nar) taşınarak alındı.
# Hex karşılıkları OKLCH→sRGB dönüşümüyle hesaplandı, elle seçilmedi.

ACIK = {
    "zemin": "#FBF8F8",
    "yuzey": "#FFFFFF",
    "yuzey_2": "#F7F3F3",
    "kod_zemin": "#F6F2F2",
    "cikti_zemin": "#F2EFEE",
    "metin": "#171110",
    "metin_soluk": "#766763",
    "kenar": "#E8E1E0",
    "kenar_guclu": "#D6CDCB",
    "vurgu": "#AC1922",
    "vurgu_uc": "#A10E2F",
    "vurgu_metin": "#FFFFFF",
    "vurgu_zemin": "#FDF2F2",
    "hata": "#A4132B",
    "hata_zemin": "#FDF1F2",
}

KOYU = {
    "zemin": "#0C0808",
    "yuzey": "#1C1716",
    "yuzey_2": "#251F1E",
    "kod_zemin": "#141010",
    "cikti_zemin": "#111514",
    "metin": "#F8F4F3",
    "metin_soluk": "#A29592",
    "kenar": "#2C2625",
    "kenar_guclu": "#3D3635",
    "vurgu": "#F66D67",
    "vurgu_uc": "#EC6771",
    "vurgu_metin": "#2A0F0E",
    "vurgu_zemin": "#241413",
    "hata": "#F58A84",
    "hata_zemin": "#26100F",
}

# Renk olmayan, yalnız temaya göre değişen değerler.
ACIK_EK = {
    "sema": "light",
    # 21st'in açık tema kart gölgesi.
    "panel-golge": ("0 48px 72px -12px #00000008, "
                    "0 32px 44px -12px #0000000f"),
    "hairline": ("linear-gradient(90deg, #00000005, #00000026 45%, "
                 "#00000005)"),
    "hayalet": "#171110",
    "hayalet-opaklik": ".045",
    "bar-zemin": "#FBF8F8E6",
}

KOYU_EK = {
    "sema": "dark",
    # 21st'in koyu tema kart gölgesi: dev ve çok yumuşak, üstüne beyaz inset
    # hairline. Hale bu üç inset katmandan çıkıyor, `filter: blur` ile değil.
    "panel-golge": ("0 12px 24px 0 #ffffff08 inset, "
                    "0 .5px .5px 0 #ffffff0f inset, "
                    "0 .25px .25px 0 #ffffff1f inset, "
                    "0 48px 72px -12px #0000003d, "
                    "0 32px 44px -12px #00000052"),
    "hairline": ("linear-gradient(90deg, #ffffff03, #ffffff4d 45%, "
                 "#ffffff03)"),
    "hayalet": "#F8F4F3",
    "hayalet-opaklik": ".035",
    "bar-zemin": "#0C0808E6",
}

# Söz dizimi renkleri; oranlar kod zeminine göre ölçülür.
SOZ_ACIK = {
    "n-kw": "#7A2D8F",
    "n-tip": "#1B4FA8",
    "n-metin": "#15693A",
    "n-sayi": "#9A4A05",
    "n-yorum": "#736A65",
    "n-yerlesik": "#0B6473",
    "n-fn": "#2B2521",
    "n-op": "#6F6661",
}

SOZ_KOYU = {
    "n-kw": "#D6A0E8",
    "n-tip": "#8FB6F0",
    "n-metin": "#84CFA0",
    "n-sayi": "#EBA96A",
    "n-yorum": "#8B807C",
    "n-yerlesik": "#6FC6D6",
    "n-fn": "#EDE7E3",
    "n-op": "#A29592",
}

# (açıklama, ön plan, arka plan, en az oran)
# Kenar ve zemin ayrımlarının eşiği metinden düşüktür: okunması değil,
# seçilebilmesi gerekir.
_DENETIM = [
    ("gövde metni", "metin", "zemin", 4.5),
    ("gövde metni (yüzey)", "metin", "yuzey", 4.5),
    ("gövde metni (yüzey-2)", "metin", "yuzey_2", 4.5),
    ("soluk metin", "metin_soluk", "zemin", 4.5),
    ("soluk metin (yüzey)", "metin_soluk", "yuzey", 4.5),
    ("soluk metin (yüzey-2)", "metin_soluk", "yuzey_2", 4.5),
    ("soluk metin (kod)", "metin_soluk", "kod_zemin", 4.5),
    ("soluk metin (çıktı)", "metin_soluk", "cikti_zemin", 4.5),
    ("bağlantı / vurgu", "vurgu", "zemin", 4.5),
    ("vurgu (yüzey)", "vurgu", "yuzey", 4.5),
    ("vurgu (yüzey-2)", "vurgu", "yuzey_2", 4.5),
    ("vurgu (vurgu zemini)", "vurgu", "vurgu_zemin", 4.5),
    ("birincil düğme yazısı", "vurgu_metin", "vurgu", 4.5),
    ("düğme yazısı (gradyan ucu)", "vurgu_metin", "vurgu_uc", 4.5),
    ("hata", "hata", "zemin", 4.5),
    ("hata (hata zemini)", "hata", "hata_zemin", 4.5),
    ("kenar", "kenar", "zemin", 1.15),
    ("kenar (yüzey)", "kenar", "yuzey", 1.15),
    ("güçlü kenar", "kenar_guclu", "yuzey", 1.35),
    ("yüzey / zemin ayrımı", "yuzey", "zemin", 1.03),
    ("kod / yüzey ayrımı", "kod_zemin", "yuzey", 1.02),
]


def kontrastlari_dogrula() -> list[str]:
    """Her iki temanın kontrastlarını hesaplar; eşiği geçmeyenleri döndürür."""
    uyarilar: list[str] = []
    for ad, palet, soz in (("açık", ACIK, SOZ_ACIK), ("koyu", KOYU, SOZ_KOYU)):
        for aciklama, on, arka, esik in _DENETIM:
            oran = kontrast(palet[on], palet[arka])
            if oran < esik:
                uyarilar.append(
                    f"{ad} tema · {aciklama}: {oran:.2f}:1 (en az {esik})")
        for sinif, renk in soz.items():
            oran = kontrast(renk, palet["kod_zemin"])
            if oran < 4.5:
                uyarilar.append(
                    f"{ad} tema · sözdizimi {sinif}: {oran:.2f}:1 (en az 4.5)")
    return uyarilar


# ------------------------------------------------------------------ ikonlar
# Emoji yok: hepsi aynı aileden, 1.5 kalınlıkta çizgi ikon.

def _ikon(govde: str, boyut: int = 16) -> str:
    return (
        f'<svg class="ikon" width="{boyut}" height="{boyut}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{govde}</svg>"
    )


IKON_ARA = _ikon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>')
IKON_GUNES = _ikon(
    '<circle cx="12" cy="12" r="4"/>'
    '<path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4'
    'M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/>')
IKON_AY = _ikon('<path d="M20 13.5A8 8 0 1 1 10.5 4a6.5 6.5 0 0 0 9.5 9.5Z"/>')
IKON_KOD = _ikon('<path d="m9 8-5 4 5 4M15 8l5 4-5 4"/>')
IKON_GITHUB = _ikon(
    '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6'
    'c3-.3 6.2-1.5 6.2-6.7A5.2 5.2 0 0 0 20 5.8a4.9 4.9 0 0 0-.1-3.6'
    's-1.1-.3-3.7 1.4a12.6 12.6 0 0 0-6.6 0C7 1.9 5.9 2.2 5.9 2.2'
    'A4.9 4.9 0 0 0 5.8 5.8 5.2 5.2 0 0 0 4.4 9.4c0 5.2 3.2 6.4 6.2 6.7'
    'a3.4 3.4 0 0 0-.9 2.6V21"/>')
IKON_KOPYA = _ikon(
    '<rect x="9" y="9" width="11" height="11" rx="2"/>'
    '<path d="M5 15V6a2 2 0 0 1 2-2h9"/>', 14)
IKON_ONAY = _ikon('<path d="m5 12.5 4.5 4.5L19 7.5"/>', 14)
IKON_BAG = _ikon('<path d="M10 14a4 4 0 0 0 6 .5l2-2a4 4 0 0 0-5.7-5.7L11 8'
                 'M14 10a4 4 0 0 0-6-.5l-2 2A4 4 0 0 0 11.7 17L13 16"/>', 14)
IKON_OK = _ikon('<path d="M5 12h13m-5-5 5 5-5 5"/>', 15)
# 21st'in kategori listesindeki minik çizgi işareti.
IKON_CIZGI = _ikon('<path d="M7 12h10"/>', 14)


# -------------------------------------------------------------------- stil

def _tema_degiskenleri(palet: dict, ek: dict, soz: dict,
                       girinti: str = "  ") -> str:
    satirlar = [f"{girinti}--{ad.replace('_', '-')}: {deger};"
                for ad, deger in palet.items()]
    satirlar += [f"{girinti}--{ad}: {deger};"
                 for ad, deger in ek.items() if ad != "sema"]
    satirlar.append(f"{girinti}color-scheme: {ek['sema']};")
    satirlar += [f"{girinti}--{sinif}: {renk};" for sinif, renk in soz.items()]
    return "\n".join(satirlar)


def stil() -> str:
    acik = _tema_degiskenleri(ACIK, ACIK_EK, SOZ_ACIK)
    koyu_medya = _tema_degiskenleri(KOYU, KOYU_EK, SOZ_KOYU, "    ")
    koyu_secim = _tema_degiskenleri(KOYU, KOYU_EK, SOZ_KOYU)
    sozdizimi = "\n".join(f".{sinif} {{ color: var(--{sinif}); }}"
                          for sinif in SOZ_ACIK)

    return f"""
/* ===================================================================
   Nar dil rehberi
   Bütün renkler çıplak :root'ta tanımlı; tema blokları yalnız üzerine
   yazar. Böylece hiçbir renk yalnızca bir medya sorgusunun içinde
   yaşamaz — sistem teması "otomatik"teyken de sayfa eksiksiz boyanır.
   =================================================================== */

:root {{
{acik}

  /* 21st.dev'in yarıçap merdiveni */
  --radius: .5rem;
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: .75rem;

  --olcu: 72ch;
  --bar: 48px;
  /* Developer Mono eşleşmesi: başlıklar mono, gövde sans. */
  --govde: 'IBM Plex Sans', 'Segoe UI', system-ui, -apple-system,
           'Helvetica Neue', Arial, sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, 'Cascadia Code', 'SF Mono',
          Consolas, 'Liberation Mono', monospace;
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-tema='acik']) {{
{koyu_medya}
  }}
}}

:root[data-tema='koyu'] {{
{koyu_secim}
}}

*, *::before, *::after {{ box-sizing: border-box; }}

html {{ scroll-behavior: smooth; }}

@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  *, *::before, *::after {{
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
  }}
}}

body {{
  margin: 0;
  background: var(--zemin);
  color: var(--metin);
  font-family: var(--govde);
  font-size: 16px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}}

.kok {{ background: var(--zemin); color: var(--metin); }}

a {{ color: var(--vurgu); text-decoration-thickness: 1px; text-underline-offset: 2px; }}
a:hover {{ text-decoration-thickness: 2px; }}

:focus-visible {{
  outline: 2px solid var(--vurgu);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}}

.ikon {{ flex: none; }}

/* Kendi kabında kayan her şey ince bir çubuk gösterir; kalın sistem çubuğu
   kod kutusunun içinde bir satır yüksekliği kadar yer kaplıyordu. */
pre, .icindekiler, .ref-sar {{
  scrollbar-width: thin;
  scrollbar-color: var(--kenar-guclu) transparent;
}}
pre::-webkit-scrollbar, .icindekiler::-webkit-scrollbar,
.ref-sar::-webkit-scrollbar {{ width: 8px; height: 8px; }}
pre::-webkit-scrollbar-thumb, .icindekiler::-webkit-scrollbar-thumb,
.ref-sar::-webkit-scrollbar-thumb {{
  background: var(--kenar-guclu); border-radius: 8px;
}}
pre::-webkit-scrollbar-track, .icindekiler::-webkit-scrollbar-track,
.ref-sar::-webkit-scrollbar-track {{ background: transparent; }}

/* Ekran okuyucuya görünür, göze görünmez. */
.gizli-metin {{
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip-path: inset(50%); white-space: nowrap;
}}

.atla {{
  position: absolute; left: 8px; top: -60px; z-index: 60;
  background: var(--vurgu); color: var(--vurgu-metin);
  padding: 8px 14px; border-radius: var(--radius); font-size: 14px;
  transition: top .2s ease;
}}
.atla:focus {{ top: 8px; }}

/* Ortak genişlik: her bölüm aynı ızgaraya oturur. */
.sinir {{
  max-width: 1200px; margin: 0 auto;
  padding-inline: 24px;
}}

/* ------------------------------------------------------------- üst bar */

.bar {{
  position: sticky; top: 0; z-index: 40;
  height: var(--bar);
  display: flex; align-items: center; gap: 16px;
  padding: 0 20px;
  background: var(--bar-zemin);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--kenar);
}}

.bar-marka {{
  display: flex; align-items: baseline; gap: 8px;
  font-family: var(--mono); font-weight: 500; font-size: 14px;
  letter-spacing: -.02em;
  color: var(--metin); text-decoration: none;
}}
.bar-marka b {{ color: var(--vurgu); font-weight: 500; }}
.bar-marka .surum {{
  font-size: 11px; font-weight: 400;
  color: var(--metin-soluk); font-variant-numeric: tabular-nums;
}}

.ara-sar {{
  position: relative;
  flex: 1 1 auto; max-width: 420px; margin: 0 auto;
  display: flex; align-items: center;
}}
.ara-sar .ikon {{
  position: absolute; left: 10px; color: var(--metin-soluk); pointer-events: none;
}}
#ara {{
  width: 100%; height: 30px;
  padding: 0 52px 0 32px;
  font: inherit; font-size: 13px;
  color: var(--metin);
  background: var(--yuzey-2);
  border: 1px solid var(--kenar);
  border-radius: var(--radius-md);
  transition: border-color .2s ease, background .2s ease;
}}
#ara::placeholder {{ color: var(--metin-soluk); }}
#ara:focus {{ outline: none; border-color: var(--kenar-guclu); }}
#ara:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 1px; }}

kbd {{
  font-family: var(--mono); font-size: 10px; line-height: 1;
  padding: 3px 5px; border-radius: var(--radius-sm);
  color: var(--metin-soluk);
  background: var(--zemin);
  border: 1px solid var(--kenar);
}}
.ara-sar kbd {{ position: absolute; right: 8px; pointer-events: none; }}

.bar-sag {{ display: flex; align-items: center; gap: 2px; margin-left: auto; }}

.bar-dugme {{
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: 30px; min-width: 30px; padding: 0 9px;
  color: var(--metin-soluk);
  background: none; border: 1px solid transparent;
  border-radius: var(--radius-md);
  font: inherit; font-size: 13px; cursor: pointer;
  text-decoration: none;
  transition: background .2s ease, color .2s ease, border-color .2s ease;
}}
.bar-dugme:hover {{
  color: var(--metin); background: var(--yuzey-2); border-color: var(--kenar);
}}
.bar-dugme .ay {{ display: none; }}
:root[data-tema='koyu'] .bar-dugme .ay {{ display: block; }}
:root[data-tema='koyu'] .bar-dugme .gunes {{ display: none; }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-tema='acik']) .bar-dugme .ay {{ display: block; }}
  :root:not([data-tema='acik']) .bar-dugme .gunes {{ display: none; }}
  :root[data-tema='acik'] .bar-dugme .ay {{ display: none; }}
  :root[data-tema='acik'] .bar-dugme .gunes {{ display: block; }}
}}

/* ---------------------------------------------------------------- giriş */

.giris-alani {{ position: relative; overflow: hidden; }}
.giris-alani::before {{
  content: ''; position: absolute; inset: -30% -10% auto -10%; height: 70%;
  background: radial-gradient(50% 60% at 30% 40%,
              var(--vurgu-zemin), transparent 70%);
  pointer-events: none;
}}

.giris-ic {{
  position: relative;
  padding-block: 64px 56px;
  display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 6fr);
  gap: 56px; align-items: center;
}}

.eyebrow {{
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 16px;
  font-family: var(--mono); font-size: 11px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--metin-soluk);
}}
.eyebrow .nokta {{
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--vurgu);
}}

.giris h1 {{
  margin: 0 0 18px;
  font-family: var(--mono); font-weight: 500;
  font-size: clamp(27px, 3.2vw, 38px);
  line-height: 1.2; letter-spacing: -.035em;
  text-wrap: balance;
}}

.giris-ozet {{
  margin: 0 0 24px; max-width: 48ch;
  font-size: 16.5px; color: var(--metin-soluk);
}}
.giris-ozet strong {{ color: var(--metin); font-weight: 600; }}
.giris-ozet p {{ margin: 0; }}

.eylemler {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 28px; }}

/* Tek canlı renk yalnız burada: birincil eylem. */
.cta {{
  display: inline-flex; align-items: center; gap: 8px;
  height: 38px; padding: 0 18px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--vurgu), var(--vurgu-uc));
  color: var(--vurgu-metin);
  font-size: 14px; font-weight: 500; text-decoration: none;
  box-shadow: 0 1px 0 0 #ffffff2e inset;
  transition: transform .2s ease, filter .2s ease;
}}
.cta:hover {{ filter: brightness(1.06); transform: translateY(-1px); }}
.cta .ikon {{ transition: transform .2s ease; }}
.cta:hover .ikon {{ transform: translateX(2px); }}

.cta-ikincil {{
  display: inline-flex; align-items: center; gap: 8px;
  height: 38px; padding: 0 16px;
  border-radius: 999px;
  color: var(--metin); text-decoration: none;
  background: var(--yuzey-2); border: 1px solid var(--kenar);
  font-size: 14px;
  transition: border-color .2s ease, background .2s ease;
}}
.cta-ikincil:hover {{ border-color: var(--kenar-guclu); }}

.hedefler {{
  display: flex; flex-wrap: wrap; gap: 6px;
  margin: 0; padding: 0; list-style: none;
}}
.hedefler li {{
  font-family: var(--mono); font-size: 11px; letter-spacing: .02em;
  padding: 3px 9px; border-radius: 999px;
  color: var(--metin-soluk);
  background: var(--yuzey-2); border: 1px solid var(--kenar);
}}

/* Yüzen panel — 21st'in imza detayı: dev yumuşak gölge, beyaz inset
   hairline, üst kenarda gradyanlı saç çizgisi. */
.panel {{
  position: relative;
  border: 1px solid var(--kenar);
  border-radius: var(--radius-xl);
  background: var(--yuzey);
  box-shadow: var(--panel-golge);
  overflow: hidden;
}}
.panel::before {{
  content: ''; position: absolute; inset: 0 0 auto; height: 1px;
  background: var(--hairline);
  z-index: 1;
}}
.panel .kod-kutu, .panel .cikti {{
  margin: 0; border: none; border-radius: 0; box-shadow: none;
}}
.panel .cikti {{ border-top: 1px solid var(--kenar); }}

/* -------------------------------------------------------- bölüm dizini */

.dizin-alani {{
  border-top: 1px solid var(--kenar);
  border-bottom: 1px solid var(--kenar);
  background: var(--yuzey);
}}
.dizin-ic {{ padding-block: 28px 32px; }}

.dizin-basi {{
  display: flex; align-items: baseline; gap: 12px;
  margin-bottom: 18px;
}}
.dizin-basi h2 {{
  margin: 0; font-family: var(--mono); font-size: 13px; font-weight: 500;
  letter-spacing: -.01em;
}}
.dizin-basi p {{ margin: 0; font-size: 12px; color: var(--metin-soluk); }}
.dizin-basi .sag {{
  margin-left: auto; font-size: 12px; color: var(--metin-soluk);
  text-decoration: none;
}}
.dizin-basi .sag:hover {{ color: var(--vurgu); }}

/* Yoğun çok sütunlu kategori listesi: kalın küçük etiket, minik çizgi
   ikon, sağa yaslı mono sayaç. */
.dizin {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 1px 24px;
  margin: 0; padding: 0; list-style: none;
}}
.dizin a {{
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; margin-inline: -8px;
  border-radius: var(--radius-md);
  color: var(--metin); text-decoration: none;
  font-size: 12.5px; font-weight: 500;
  transition: background .2s ease, color .2s ease;
}}
.dizin a .ikon {{ color: var(--metin-soluk); }}
.dizin a .ad {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.dizin a .adet {{
  margin-left: auto;
  font-family: var(--mono); font-size: 11px; font-weight: 400;
  color: var(--metin-soluk); font-variant-numeric: tabular-nums;
}}
.dizin a:hover {{ background: var(--yuzey-2); }}
.dizin a:hover .ikon {{ color: var(--vurgu); }}

/* ------------------------------------------------------------ kod kutusu */

.kod-kutu {{
  margin: 0 0 14px;
  background: var(--kod-zemin);
  border: 1px solid var(--kenar);
  border-radius: var(--radius-lg);
  overflow: hidden;
}}

.kod-basi {{
  display: flex; align-items: center; gap: 8px;
  padding: 0 8px 0 12px; height: 34px;
  background: var(--yuzey-2);
  border-bottom: 1px solid var(--kenar);
}}
.kod-dil {{
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--metin-soluk);
}}

.kopyala {{
  display: inline-flex; align-items: center; gap: 5px;
  margin-left: auto; height: 24px; padding: 0 8px;
  font-family: var(--mono); font-size: 11px;
  color: var(--metin-soluk);
  background: none; border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background .2s ease, color .2s ease, border-color .2s ease;
}}
.kopyala:hover {{
  color: var(--metin); background: var(--zemin); border-color: var(--kenar);
}}
.kopyala .onay {{ display: none; }}
.kopyala.bitti {{ color: var(--vurgu); }}
.kopyala.bitti .onay {{ display: block; }}
.kopyala.bitti .kopya {{ display: none; }}

pre.kod {{
  margin: 0; padding: 14px 16px;
  overflow-x: auto;
  font-family: var(--mono); font-size: 13px; line-height: 1.7;
  tab-size: 2;
}}
pre.kod code {{ font: inherit; }}

{sozdizimi}

/* ------------------------------------------------------------------ çıktı */

.cikti {{
  margin: -14px 0 18px;
  border: 1px solid var(--kenar); border-top: none;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  background: var(--cikti-zemin);
}}
.cikti-etiket {{
  display: block; padding: 8px 16px 0;
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--metin-soluk);
}}
.cikti pre {{
  margin: 0; padding: 4px 16px 14px;
  overflow-x: auto;
  font-family: var(--mono); font-size: 12.5px; line-height: 1.6;
  color: var(--metin);
}}
.cikti.hatali {{
  background: var(--hata-zemin); border-color: var(--hata);
}}
.cikti.hatali .cikti-etiket, .cikti.hatali pre {{ color: var(--hata); }}

/* Kod kutusunun altına çıktı geliyorsa alt köşeleri düzleşir. */
.kod-kutu:has(+ .cikti) {{
  border-bottom-left-radius: 0; border-bottom-right-radius: 0;
}}

/* ---------------------------------------------------------------- kabuk */

.kabuk {{
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  gap: 56px;
  padding-block: 40px 80px;
}}

/* ------------------------------------------------------------ içindekiler */

.icindekiler {{
  position: sticky; top: calc(var(--bar) + 16px);
  align-self: start;
  max-height: calc(100vh - var(--bar) - 32px);
  overflow-y: auto;
  padding-right: 8px;
  font-size: 13px;
}}
.icindekiler summary {{
  display: none;
  font-family: var(--mono); font-size: 13px;
  font-weight: 500; cursor: pointer; padding: 8px 0;
}}

.ic-grup {{ margin-bottom: 18px; }}
.ic-baslik {{
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px;
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--metin-soluk);
}}
.ic-baslik .sayi {{
  margin-left: auto; font-variant-numeric: tabular-nums; opacity: .75;
}}
.ic-grup ul {{ margin: 0; padding: 0; list-style: none; }}
.ic-grup li {{ margin: 0; }}
.ic-grup a {{
  display: block; padding: 3px 10px;
  margin-left: -10px;
  color: var(--metin-soluk); text-decoration: none;
  border-left: 2px solid transparent;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  transition: color .2s ease, background .2s ease;
}}
.ic-grup a:hover {{ color: var(--metin); background: var(--yuzey-2); }}
.ic-grup a.etkin {{
  color: var(--vurgu); border-left-color: var(--vurgu);
  background: var(--vurgu-zemin); font-weight: 500;
}}
.ic-grup[hidden] {{ display: none; }}

.ara-bos {{ padding: 8px 0; color: var(--metin-soluk); font-size: 13px; }}

/* --------------------------------------------------------------- içerik */

.icerik {{ min-width: 0; max-width: var(--olcu); }}

.bolum {{
  position: relative;
  margin-bottom: 64px;
  scroll-margin-top: calc(var(--bar) + 16px);
}}

/* Bölüm başlığı kalıbı: kalın başlık + soluk alt satır, sağda sonraki adım.
   Arkasındaki dev rakam sırayı gösteriyor — rehber baştan sona okunmak
   üzere yazıldı. */
.bolum-basi {{
  position: relative;
  margin-bottom: 28px; padding-bottom: 12px;
  border-bottom: 1px solid var(--kenar);
}}
.bolum-basi h2 {{
  display: flex; align-items: baseline; gap: 10px;
  margin: 0;
  font-family: var(--mono); font-size: 15px; font-weight: 500;
  letter-spacing: -.01em;
}}
.bolum-basi .alt {{
  margin: 2px 0 0;
  font-size: 12.5px; color: var(--metin-soluk);
}}
/* Sayaç başlığın yanında küçük bir mono rozet; sağ kenar hayalet rakama
   ayrıldı, ikisi aynı yerde dururken üst üste biniyordu. */
.bolum-basi .sayi {{
  padding: 2px 7px; border-radius: 999px;
  background: var(--yuzey-2); border: 1px solid var(--kenar);
  font-size: 10px; font-weight: 400; color: var(--metin-soluk);
  font-variant-numeric: tabular-nums;
}}
.bolum-basi .hayalet-no {{
  position: absolute; right: 0; top: 50%;
  transform: translateY(-54%);
  font-family: var(--mono); font-weight: 500;
  font-size: clamp(44px, 6vw, 76px); line-height: 1;
  letter-spacing: -.07em;
  color: var(--hayalet); opacity: var(--hayalet-opaklik);
  pointer-events: none; user-select: none;
}}

.konu {{
  margin-bottom: 38px;
  scroll-margin-top: calc(var(--bar) + 16px);
}}
.konu h3 {{
  margin: 0 0 8px;
  font-family: var(--mono); font-size: 17px; font-weight: 500;
  letter-spacing: -.025em; line-height: 1.35;
}}
.konu h3 .capa {{
  color: inherit; text-decoration: none;
  display: inline-flex; align-items: baseline; gap: 8px;
}}
.konu h3 .capa .ikon {{
  opacity: 0; color: var(--metin-soluk);
  transition: opacity .2s ease;
}}
.konu h3:hover .capa .ikon, .capa:focus-visible .ikon {{ opacity: 1; }}

.aciklama {{ margin: 0 0 14px; }}
.aciklama p {{ margin: 0 0 10px; }}
.aciklama p:last-child {{ margin-bottom: 0; }}
.aciklama ul, .aciklama ol {{ margin: 0 0 10px; padding-left: 22px; }}
.aciklama li {{ margin-bottom: 4px; }}

code {{
  font-family: var(--mono); font-size: .86em;
  padding: .12em .34em; border-radius: var(--radius-sm);
  background: var(--yuzey-2); border: 1px solid var(--kenar);
}}
pre code {{ padding: 0; background: none; border: none; }}

.not {{
  margin: 0 0 14px; padding: 10px 14px;
  font-size: 14px; color: var(--metin-soluk);
  background: var(--yuzey-2);
  border: 1px solid var(--kenar);
  border-left: 2px solid var(--kenar-guclu);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}}
.not code {{ background: var(--zemin); }}

/* -------------------------------------------------------------- başlangıç */

.kart {{
  margin-bottom: 52px;
  padding: 18px 20px;
  background: var(--yuzey);
  border: 1px solid var(--kenar);
  border-radius: var(--radius-lg);
}}
.kart > h2 {{
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 12px;
  font-family: var(--mono); font-size: 10px; font-weight: 500;
  letter-spacing: .1em; text-transform: uppercase;
  color: var(--metin-soluk);
}}
.kart p {{ margin: 0 0 10px; font-size: 14.5px; }}
.kart p:last-child {{ margin-bottom: 0; }}
.kart pre.komut {{
  margin: 0 0 12px; padding: 12px 14px;
  overflow-x: auto;
  background: var(--kod-zemin);
  border: 1px solid var(--kenar); border-radius: var(--radius-md);
  font-family: var(--mono); font-size: 12.5px; line-height: 1.7;
}}
.kart pre.komut code {{ padding: 0; background: none; border: none; }}

/* ------------------------------------------------------------- başvuru */

.ref-grup {{ margin-bottom: 28px; }}
.ref-grup h3 {{
  margin: 0 0 4px;
  font-family: var(--mono); font-size: 15px; font-weight: 500;
  letter-spacing: -.02em;
}}
.ref-grup .aciklama {{ font-size: 14px; color: var(--metin-soluk); }}

.ref-sar {{
  overflow-x: auto;
  border: 1px solid var(--kenar); border-radius: var(--radius-lg);
}}
/* Konu metninin içine doğrudan yazılmış tablolar da kendi kabında kayar;
   ilk sütun kırılmadığı için dar ekranda gövdeyi yatay kaydırıyorlardı. */
.aciklama table.ref {{
  display: block; overflow-x: auto; max-width: 100%;
  margin-bottom: 10px;
  border: 1px solid var(--kenar); border-radius: var(--radius-lg);
}}
table.ref {{
  width: 100%; border-collapse: collapse;
  font-size: 14px;
}}
table.ref td {{
  padding: 8px 14px;
  border-top: 1px solid var(--kenar);
  vertical-align: baseline;
}}
table.ref tr:first-child td {{ border-top: none; }}
table.ref tr:nth-child(even) {{ background: var(--yuzey-2); }}
table.ref td:first-child {{ width: 1%; white-space: nowrap; }}
table.ref code {{ font-size: 12.5px; background: var(--zemin); }}

/* ----------------------------------------------------------------- alt */

.sayfa-alti {{
  border-top: 1px solid var(--kenar);
  background: var(--yuzey);
}}
.sayfa-alti-ic {{
  padding-block: 28px 40px;
  display: flex; flex-wrap: wrap; gap: 16px 32px;
  align-items: baseline;
  font-size: 13.5px; color: var(--metin-soluk);
}}
.sayfa-alti p {{ margin: 0; max-width: 62ch; }}
.sayfa-alti .tarih {{
  margin-left: auto; font-family: var(--mono); font-size: 12px;
  font-variant-numeric: tabular-nums;
}}

/* ------------------------------------------------------------- responsive */

@media (max-width: 1040px) {{
  .giris-ic {{ grid-template-columns: minmax(0, 1fr); gap: 36px; }}
  .bolum-basi .hayalet-no {{ display: none; }}
}}

@media (max-width: 900px) {{
  .kabuk {{ grid-template-columns: minmax(0, 1fr); gap: 24px; }}
  .icerik {{ max-width: none; }}
  .icindekiler {{
    position: static; max-height: none; overflow: visible;
    padding: 0 0 8px;
    border: 1px solid var(--kenar); border-radius: var(--radius-lg);
    background: var(--yuzey);
  }}
  .icindekiler summary {{ display: list-item; padding: 10px 14px; }}
  .icindekiler > details[open] > *:not(summary) {{ padding-inline: 14px; }}
  .ara-sar {{ max-width: none; }}
  .ara-sar kbd {{ display: none; }}
  #ara {{ padding-right: 12px; }}
}}

@media (max-width: 600px) {{
  .bar {{ padding: 0 12px; gap: 8px; }}
  .bar-marka .surum {{ display: none; }}
  .bar-dugme span:not(.gizli-metin) {{ display: none; }}
  .sinir {{ padding-inline: 16px; }}
  .giris-ic {{ padding-block: 40px 36px; }}
  .dizin {{ grid-template-columns: minmax(0, 1fr); }}
}}
"""


# ------------------------------------------------------------------ betik

SCRIPT = """
(function () {
  'use strict';

  // --- tema ---------------------------------------------------------
  // Seçim kökte bir öznitelik olarak durur; CSS onu hem sistem temasının
  // hem de varsayılanın üstüne yazar. Seçim yoksa sistem izlenir.
  var kok = document.documentElement;
  var ANAHTAR = 'nar-tema';
  try {
    var kayitli = localStorage.getItem(ANAHTAR);
    if (kayitli === 'acik' || kayitli === 'koyu') kok.setAttribute('data-tema', kayitli);
  } catch (e) { /* gizli sekmede depolama kapalı olabilir */ }

  function koyuMu() {
    var secim = kok.getAttribute('data-tema');
    if (secim) return secim === 'koyu';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  var temaDugmesi = document.getElementById('tema');
  if (temaDugmesi) {
    var etiketle = function () {
      var koyu = koyuMu();
      temaDugmesi.setAttribute('aria-pressed', koyu ? 'true' : 'false');
      temaDugmesi.title = koyu ? 'Açık temaya geç' : 'Koyu temaya geç';
    };
    etiketle();
    temaDugmesi.addEventListener('click', function () {
      var yeni = koyuMu() ? 'acik' : 'koyu';
      kok.setAttribute('data-tema', yeni);
      try { localStorage.setItem(ANAHTAR, yeni); } catch (e) {}
      etiketle();
    });
  }

  // --- kopyala ------------------------------------------------------
  document.querySelectorAll('.kopyala').forEach(function (dugme) {
    dugme.addEventListener('click', function () {
      var kutu = dugme.closest('.kod-kutu');
      var kod = kutu ? kutu.querySelector('pre.kod').textContent : '';
      var bitir = function (basarili) {
        dugme.classList.toggle('bitti', basarili);
        dugme.querySelector('.yazi').textContent = basarili ? 'kopyalandı' : 'olmadı';
        setTimeout(function () {
          dugme.classList.remove('bitti');
          dugme.querySelector('.yazi').textContent = 'kopyala';
        }, 1400);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(kod).then(function () { bitir(true); },
                                                function () { bitir(false); });
      } else {
        bitir(false);
      }
    });
  });

  // --- içindekiler dar ekranda katlanır ------------------------------
  var katla = document.querySelector('.ic-katla');
  if (katla) {
    var dar = window.matchMedia('(max-width: 900px)');
    var elle = false;
    katla.addEventListener('toggle', function () { elle = true; });
    var ayarla = function () { if (!elle) katla.open = !dar.matches; };
    ayarla();
    dar.addEventListener('change', function () { elle = false; ayarla(); });
  }

  // --- arama --------------------------------------------------------
  // İçindekileri yerinde süzer: eşleşmeyen konular gizlenir, boşalan
  // bölüm başlığı da gizlenir. Sayfanın kendisine dokunulmaz.
  var ara = document.getElementById('ara');
  var bos = document.querySelector('.ara-bos');
  if (ara) {
    var gruplar = Array.prototype.map.call(
      document.querySelectorAll('.ic-grup'), function (g) {
        var sayi = g.querySelector('.sayi');
        return {
          oge: g,
          sayi: sayi,
          // Süzme sırasında sayaç görüneni gösterir; toplamı göstermeye
          // devam etseydi ekrandaki listeyle çelişirdi.
          toplam: sayi ? sayi.textContent : '',
          bagalar: Array.prototype.map.call(g.querySelectorAll('a'), function (a) {
            return { oge: a.parentNode, metin: a.textContent.toLocaleLowerCase('tr') };
          })
        };
      });

    var suz = function () {
      var q = ara.value.trim().toLocaleLowerCase('tr');
      var bulunan = 0;
      gruplar.forEach(function (g) {
        var acik = 0;
        g.bagalar.forEach(function (b) {
          var uyar = !q || b.metin.indexOf(q) !== -1;
          b.oge.hidden = !uyar;
          if (uyar) acik += 1;
        });
        g.oge.hidden = acik === 0;
        if (g.sayi) g.sayi.textContent = q ? String(acik) : g.toplam;
        bulunan += acik;
      });
      if (bos) bos.hidden = bulunan !== 0;
    };

    ara.addEventListener('input', suz);
    ara.addEventListener('keydown', function (o) {
      if (o.key === 'Escape') { ara.value = ''; suz(); ara.blur(); }
    });

    document.addEventListener('keydown', function (o) {
      var k = o.key === 'k' || o.key === 'K';
      if (k && (o.metaKey || o.ctrlKey)) { o.preventDefault(); ara.focus(); ara.select(); }
    });
  }

  // --- etkin konu ---------------------------------------------------
  // Görünen konuyu içindekilerde işaretler. Kaydırma olayı dinlemek
  // yerine gözlemci: her karede hesap yapmaz.
  var baglar = {};
  document.querySelectorAll('.ic-grup a').forEach(function (a) {
    var hedef = a.getAttribute('href');
    if (hedef && hedef.charAt(0) === '#') baglar[hedef.slice(1)] = a;
  });

  var etkin = null;
  var isaretle = function (kimlik) {
    var a = baglar[kimlik];
    if (!a || a === etkin) return;
    if (etkin) etkin.classList.remove('etkin');
    a.classList.add('etkin');
    etkin = a;
  };

  if ('IntersectionObserver' in window) {
    var gorunen = new Set();
    var gozlemci = new IntersectionObserver(function (girdiler) {
      girdiler.forEach(function (g) {
        if (g.isIntersecting) gorunen.add(g.target.id);
        else gorunen.delete(g.target.id);
      });
      // En yukarıdaki görünen konu etkin sayılır.
      var ilk = null, enUst = Infinity;
      gorunen.forEach(function (kimlik) {
        var o = document.getElementById(kimlik);
        if (!o) return;
        var ust = o.getBoundingClientRect().top;
        if (ust < enUst) { enUst = ust; ilk = kimlik; }
      });
      if (ilk) isaretle(ilk);
    }, { rootMargin: '-56px 0px -60% 0px' });

    document.querySelectorAll('.konu, #referans').forEach(function (o) {
      gozlemci.observe(o);
    });
  }
})();
"""
