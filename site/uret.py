"""Belgeler sitesini üretir.

Her örneği gerçekten derler ve Node ile çalıştırır; sayfadaki çıktılar
elle yazılmaz, üretim sırasında ölçülür. Bir örnek beklenmedik biçimde
kırılırsa üretim hata verip durur — yani site her zaman çalışan kod gösterir.

Sayfanın görünüşü `tasarim.py`'de durur: palet, stil, betik ve iskelet.
Burada yalnız içeriğin derlenip yerleştirilmesi var.

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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from narc import __version__  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.backends import js as js_backend  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.renk import renklendir_toplu  # noqa: E402
from narc.parser import parse  # noqa: E402

import oyun  # noqa: E402
import tasarim  # noqa: E402
from tasarim import (  # noqa: E402
    IKON_ARA, IKON_AY, IKON_BAG, IKON_CIZGI, IKON_GITHUB, IKON_GUNES,
    IKON_KOD, IKON_KOPYA, IKON_OK, IKON_ONAY, IKON_BILESEN, IKON_OYNAT, IKON_PAKET, IKON_TAKVIM,
)
from icerik import (  # noqa: E402
    ALT_BASLIK, BASLIK, BOLUMLER, DEPO, GIRIS, HEDEFLER, NASIL_CALISTIRILIR,
    NOT_SARMAL, REFERANS, VITRIN,
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


# --------------------------------------------------------------------- HTML
# Renklendirme, Nar ile yazılmış renklendiriciye yaptırılır (IDE ile aynı
# kaynak). Node sürecini her blok için açmamak adına hepsi bir kerede
# renklendirilip burada saklanır.
_RENKLER: dict[str, str] = {}


def renkleri_hazirla() -> None:
    kaynaklar = [VITRIN["kod"]]
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


def kod_blogu(kaynak: str, dil_etiketi: str = "nar",
              denenecek: str | None = None) -> str:
    """Kod kutusu: üstte dil etiketi, Dene ve kopyala düğmeleri.

    Kopyalanan metin `pre`'nin kendisinden okunur; ayrı bir veri
    özniteliğinde saklansaydı ikisi zamanla ayrışabilirdi.

    `denenecek` verilirse deneme alanına bağlantı çıkar. Bağlantıya
    gömülen kaynak, sayfanın çıktısını alırken çalıştırdığı kaynağın
    aynısıdır — orada da aynı sonucu vermeli.
    """
    # Nar dışındaki bloklar (kabuk komutları) renklendirilmez: Nar
    # renklendiricisi onları yanlış boyar.
    govde = renklendir(kaynak) if dil_etiketi == "nar" else html.escape(kaynak)

    dene = ""
    if denenecek is not None:
        dene = (
            f'<a class="dene" href="deneme/#k={oyun.kodu_sar(denenecek)}">'
            f'{IKON_OYNAT}<span>dene</span></a>'
        )

    return (
        '<div class="kod-kutu">'
        '<div class="kod-basi">'
        f'<span class="kod-dil">{html.escape(dil_etiketi)}</span>'
        f'<span class="kod-eylem">{dene}'
        '<button class="kopyala" type="button">'
        f'<span class="kopya">{IKON_KOPYA}</span>'
        f'<span class="onay">{IKON_ONAY}</span>'
        '<span class="yazi">kopyala</span>'
        "</button></span>"
        "</div>"
        f'<pre class="kod"><code>{govde}</code></pre>'
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
        f'<h3><a class="capa" href="#{konu["id"]}">'
        f'{html.escape(konu["baslik"])}{IKON_BAG}</a></h3>',
        f'<div class="aciklama">{konu["aciklama"].strip()}</div>',
    ]

    # Deneme alanı yalnız çalışan örnekler için anlamlı: kabuk komutları ve
    # çalıştırılmayan parçalar oraya götürülmez.
    denenecek = None
    if konu.get("dil", "nar") == "nar" and konu.get("calistirma", True):
        denenecek = calistirilacak_kaynak(konu)
    parcalar.append(kod_blogu(konu["kod"], konu.get("dil", "nar"), denenecek))

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
    parcalar = [
        '<section class="bolum" id="referans">',
        bolum_basi_html(
            "Hızlı başvuru",
            "Ararken bakılacak tablolar: hazır fonksiyonlar, metotlar, işleçler.",
            f"{len(REFERANS)} tablo", len(BOLUMLER) + 1),
    ]
    for tablo in REFERANS:
        parcalar.append('<div class="ref-grup">')
        parcalar.append(f'<h3>{html.escape(tablo["baslik"])}</h3>')
        parcalar.append(f'<p class="aciklama">{tablo["aciklama"]}</p>')
        # Geniş tablo kendi kabında kayar; gövde yatay olarak kaymaz.
        parcalar.append('<div class="ref-sar"><table class="ref"><tbody>')
        for ad, acik in tablo["satirlar"]:
            parcalar.append(
                f'<tr><td><code>{html.escape(ad)}</code></td>'
                f"<td>{html.escape(acik)}</td></tr>"
            )
        parcalar.append("</tbody></table></div></div>")
    parcalar.append("</section>")
    return "\n".join(parcalar)


def bolum_basi_html(baslik: str, aciklama: str, sayi: str,
                    sira: int) -> str:
    """Bölüm başlığı: ad, soluk alt satır, sağda sayaç, arkada sıra numarası.

    Numara süs değil: rehber baştan sona okunmak üzere yazıldı, bölümler
    birbirinin üzerine biniyor. Hayalet rakam o sırayı gösteriyor.
    """
    return (
        '<div class="bolum-basi">'
        f'<span class="hayalet-no" aria-hidden="true">{sira:02d}</span>'
        f"<h2>{html.escape(baslik)}"
        f'<span class="sayi">{html.escape(sayi)}</span></h2>'
        f'<p class="alt">{html.escape(aciklama)}</p>'
        "</div>"
    )


def bolum_dizini_html() -> str:
    """Girişin altındaki yoğun bölüm listesi.

    56 konuluk bir rehberde okuyucunun ilk sorusu "neler var" oluyor;
    içindekiler çubuğu uzun, bu dizin tek bakışta tamamını gösteriyor.
    """
    ogeler = []
    for bolum in BOLUMLER:
        ogeler.append(
            f'<li><a href="#{bolum["id"]}">{IKON_CIZGI}'
            f'<span class="ad">{html.escape(bolum["baslik"])}</span>'
            f'<span class="adet">{len(bolum["konular"])}</span></a></li>'
        )
    ogeler.append(
        f'<li><a href="#referans">{IKON_CIZGI}'
        f'<span class="ad">Hızlı başvuru</span>'
        f'<span class="adet">{len(REFERANS)}</span></a></li>'
    )
    ogeler.append(
        f'<li><a href="deneme/">{IKON_OYNAT}'
        f'<span class="ad">Deneme alanı</span>'
        f'<span class="adet">→</span></a></li>'
    )
    ogeler.append(
        f'<li><a href="bilesenler/">{IKON_BILESEN}'
        f'<span class="ad">Bileşen vitrini</span>'
        f'<span class="adet">→</span></a></li>'
    )
    ogeler.append(
        f'<li><a href="takvim/">{IKON_TAKVIM}'
        f'<span class="ad">Takvim örneği</span>'
        f'<span class="adet">→</span></a></li>'
    )
    ogeler.append(
        f'<li><a href="kavurga/">{IKON_PAKET}'
        f'<span class="ad">Kavurga — tam site</span>'
        f'<span class="adet">→</span></a></li>'
    )
    konu_sayisi = sum(len(b["konular"]) for b in BOLUMLER)
    return f"""<section class="dizin-alani">
  <div class="sinir dizin-ic">
    <div class="dizin-basi">
      <h2>Bölümler</h2>
      <p>{len(BOLUMLER)} bölüm · {konu_sayisi} konu</p>
      <a class="sag" href="#baslangic">Baştan başla &rsaquo;</a>
    </div>
    <ul class="dizin">{"".join(ogeler)}</ul>
  </div>
</section>"""


def icindekiler_html() -> str:
    # `details` ile sarılır: dar ekranda katlanır, geniş ekranda hep açıktır.
    parcalar = [
        '<nav class="icindekiler" aria-label="İçindekiler">',
        '<details class="ic-katla" open>'
        "<summary>İçindekiler</summary>",
        '<p class="ara-bos" hidden>Eşleşen konu yok.</p>',
    ]
    for bolum in BOLUMLER:
        parcalar.append(
            '<div class="ic-grup">'
            f'<span class="ic-baslik">{html.escape(bolum["baslik"])}'
            f'<span class="sayi">{len(bolum["konular"])}</span></span><ul>'
        )
        for konu in bolum["konular"]:
            parcalar.append(
                f'<li><a href="#{konu["id"]}">{html.escape(konu["baslik"])}</a></li>'
            )
        parcalar.append("</ul></div>")
    parcalar.append(
        '<div class="ic-grup"><span class="ic-baslik">Başvuru'
        f'<span class="sayi">{len(REFERANS)}</span></span><ul>'
        '<li><a href="#referans">Hızlı başvuru</a></li></ul></div>'
    )
    parcalar.append("</details></nav>")
    return "\n".join(parcalar)


# ------------------------------------------------------------------- giriş
def vitrin_html() -> str:
    """Giriş bölümündeki program ve onun gerçek çıktısı.

    Bir dili tanıtmanın en doğrudan yolu bir program ile onun çıktısıdır;
    bu ikisi de üretim sırasında ölçülür.
    """
    cikti, hata = ornegi_calistir(VITRIN)
    if hata:
        raise SystemExit(f"vitrin örneği çalışmadı:\n{cikti}")
    return (kod_blogu(VITRIN["kod"], "nar", calistirilacak_kaynak(VITRIN))
            + cikti_blogu(cikti, False))


def giris_html(konu_sayisi: int, calisan: int) -> str:
    hedef_html = "".join(f"<li>{html.escape(h)}</li>" for h in HEDEFLER)

    return f"""<section class="giris-alani">
  <div class="sinir giris-ic">
    <div class="giris">
      <p class="eyebrow"><span class="nokta"></span>
        {html.escape(BASLIK)} dil rehberi · v{__version__}</p>
      <h1>{html.escape(ALT_BASLIK)}</h1>
      <div class="giris-ozet">{GIRIS.strip()}</div>
      <div class="eylemler">
        <a class="cta" href="deneme/">{IKON_OYNAT}Tarayıcıda dene</a>
        <a class="cta-ikincil" href="#baslangic">Rehbere başla{IKON_OK}</a>
      </div>
      <p class="giris-not">Kurulum yok: deneme alanı derleyiciyi tarayıcında
      çalıştırır. Yazdığın kodun bağlantısını paylaşabilirsin.</p>
      <ul class="hedefler">{hedef_html}</ul>
    </div>
    <div class="giris-yan">
      <div class="panel">{vitrin_html()}</div>
    </div>
  </div>
</section>"""


# ------------------------------------------------------------------- sayfa
FONT_BAGI = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=IBM+Plex+Sans:wght@400;500;600&"
    'family=JetBrains+Mono:wght@400;500&display=swap">'
)


def sayfa_uret(artifact: bool = False) -> str:
    """Sayfayı üretir. `artifact=True` ise `<html>/<head>/<body>` sarmalı
    olmadan, yayın ortamının kendi iskeletine gömülecek biçimde döner."""
    uyarilar = tasarim.kontrastlari_dogrula()
    if uyarilar:
        raise SystemExit("kontrast yetersiz:\n  " + "\n  ".join(uyarilar))

    renkleri_hazirla()

    govde: list[str] = []
    calisan = 0
    for sira, bolum in enumerate(BOLUMLER, start=1):
        govde.append(f'<section class="bolum" id="{bolum["id"]}">')
        govde.append(bolum_basi_html(
            bolum["baslik"], bolum["aciklama"],
            f'{len(bolum["konular"])} konu', sira))
        for konu in bolum["konular"]:
            govde.append(konu_html(konu))
            if konu.get("calistirma", True):
                calisan += 1
        govde.append("</section>")
    govde.append(referans_html())

    konu_sayisi = sum(len(b["konular"]) for b in BOLUMLER)

    # `lang="tr"` kök sarmalayıcıda: `text-transform: uppercase` Türkçe
    # kurallarına göre çalışsın (i → İ). Yayın ortamında <html lang> bize ait
    # olmadığı için bu sarmalayıcı gerekli.
    icerik = f"""<div lang="tr" class="kok">

<a class="atla" href="#icerik">İçeriğe atla</a>

<header class="bar">
  <a class="bar-marka" href="#">
    <b>{html.escape(BASLIK)}</b>
    <span class="surum">v{__version__}</span>
  </a>
  <div class="ara-sar">
    {IKON_ARA}
    <input id="ara" type="search" autocomplete="off" spellcheck="false"
           placeholder="Konu ara…" aria-label="Konularda ara">
    <kbd>Ctrl K</kbd>
  </div>
  <div class="bar-sag">
    <a class="bar-dugme" href="deneme/">{IKON_OYNAT}<span>Dene</span></a>
    <a class="bar-dugme" href="bilesenler/">{IKON_BILESEN}<span>Bileşenler</span></a>
    <a class="bar-dugme" href="{html.escape(DEPO)}" rel="noreferrer">
      {IKON_GITHUB}<span>Kaynak</span>
    </a>
    <button id="tema" class="bar-dugme" type="button" aria-pressed="false">
      <span class="gunes">{IKON_GUNES}</span><span class="ay">{IKON_AY}</span>
      <span class="gizli-metin">Temayı değiştir</span>
    </button>
  </div>
</header>

{giris_html(konu_sayisi, calisan)}

{bolum_dizini_html()}

<div class="sinir kabuk">
{icindekiler_html()}
<main class="icerik" id="icerik">
<div class="kart">
  <h2>{IKON_KOD}Nasıl çalıştırılır</h2>
  {NASIL_CALISTIRILIR.strip()}
  <p class="not">{NOT_SARMAL}</p>
</div>
{chr(10).join(govde)}
</main>
</div>

<footer class="sayfa-alti">
  <div class="sinir sayfa-alti-ic">
    <p>Bu sayfadaki {calisan} örneğin çıktısı, sayfa üretilirken kod gerçekten
    derlenip çalıştırılarak alınmıştır — hiçbiri elle yazılmamıştır.</p>
    <span class="tarih">son üretim {date.today().isoformat()}</span>
  </div>
</footer>

</div>"""

    betik = f"<script>{tasarim.SCRIPT}</script>"
    stil = f"<style>{tasarim.stil()}</style>"

    if artifact:
        return (f"<title>{html.escape(BASLIK)} Dil Rehberi</title>\n"
                f"{FONT_BAGI}\n{stil}\n\n{icerik}\n\n{betik}\n")

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(BASLIK)} — dil rehberi</title>
<meta name="description" content="{html.escape(ALT_BASLIK)}">
{FONT_BAGI}
{stil}
</head>
<body>
{icerik}
{betik}
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

    # Deneme alanı sayfanın yanına üretilir; ayrı bir komut olsaydı
    # ikisinden biri er geç unutulurdu. Rehberdeki her çalışan konu deneme
    # alanının dosya ağacında "Rehber" altında açılabilir.
    if not args.artifact:
        deneme = args.cikti.parent / "deneme"
        deneme.mkdir(parents=True, exist_ok=True)
        boyut = oyun.narc_zip(deneme / "narc.zip")
        rehber = []
        for bolum in BOLUMLER:
            for konu in bolum["konular"]:
                if konu.get("dil", "nar") != "nar" or not konu.get("calistirma", True):
                    continue
                rehber.append({
                    "ad": konu["id"] + ".nar",
                    "yol": f'rehber/{bolum["id"]}/{konu["id"]}.nar',
                    "grup": "Rehber · " + bolum["baslik"],
                    "kaynak": calistirilacak_kaynak(konu),
                })
        (deneme / "index.html").write_text(oyun.sayfa(rehber), encoding="utf-8")
        print(f"yazıldı: {deneme / 'index.html'} "
              f"(derleyici paketi {boyut // 1024} KB, {len(rehber)} rehber konusu)")

        # Bileşen vitrini: arayüz kitaplığının kendi kendini anlattığı sayfa.
        # Nar ile yazılmıştır, derleyiciden geçerek buraya çıkar.
        vitrin = args.cikti.parent / "bilesenler"
        vitrin.mkdir(parents=True, exist_ok=True)
        kaynak = KOK / "ornekler" / "arayuz_galerisi.nar"
        sonuc = subprocess.run(
            [sys.executable, "-m", "narc", "build", str(kaynak),
             "--target", "web", "-o", str(vitrin / "index.html")],
            cwd=KOK, capture_output=True, text=True, encoding="utf-8",
        )
        if sonuc.returncode != 0:
            print("bileşen vitrini üretilemedi:\n" + (sonuc.stderr or sonuc.stdout))
            return 1
        print(f"yazıldı: {vitrin / 'index.html'} (bileşen vitrini)")

        # Takvim demosu: aralık seçicinin gerçek bir ekranda hâli.
        takvim = args.cikti.parent / "takvim"
        takvim.mkdir(parents=True, exist_ok=True)
        sonuc = subprocess.run(
            [sys.executable, "-m", "narc", "build",
             str(KOK / "ornekler" / "takvim.nar"),
             "--target", "web", "-o", str(takvim / "index.html")],
            cwd=KOK, capture_output=True, text=True, encoding="utf-8",
        )
        if sonuc.returncode != 0:
            print("takvim demosu üretilemedi:\n" + (sonuc.stderr or sonuc.stdout))
            return 1
        print(f"yazıldı: {takvim / 'index.html'} (takvim demosu)")

        # Kavurga: kütüphanenin tam bir sitede hâli.
        kavurga = args.cikti.parent / "kavurga"
        kavurga.mkdir(parents=True, exist_ok=True)
        sonuc = subprocess.run(
            [sys.executable, "-m", "narc", "build",
             str(KOK / "ornekler" / "kavurga.nar"),
             "--target", "web", "-o", str(kavurga / "index.html")],
            cwd=KOK, capture_output=True, text=True, encoding="utf-8",
        )
        if sonuc.returncode != 0:
            print("kavurga üretilemedi:" + chr(10)
                  + (sonuc.stderr or sonuc.stdout))
            return 1
        print(f"yazıldı: {kavurga / 'index.html'} (Kavurga örneği)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
