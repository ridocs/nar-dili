"""Tarayıcıda çalışan Nar deneme alanını (playground) üretir.

Neden var: bir dili kimse kurup denemez. Nar'ı denemek için şimdiye kadar
depoyu klonlamak, Python ve Node kurmak gerekiyordu. Bu sayfa o engeli
kaldırıyor — kod yazılır, `Çalıştır`a basılır, çıktı ve ekran görünür.

Nasıl çalışıyor:

- **Derleyici** tarayıcıda Pyodide üzerinde çalışır. `narc` saf Python
  olduğu için olduğu gibi paketlenip yükleniyor; ilk `Çalıştır`a kadar
  indirilmez.
- **Renklendirme** Nar ile yazılmış renklendiriciden gelir
  (`araclar/renklendirici.nar`), yani IDE ve belgeler sitesiyle aynı
  kaynak. Yazarken sayfa kendi dilini kendi aracıyla boyuyor.
- **Çalıştırma** ayrı kökenli, betik dışında hiçbir yetkisi olmayan bir
  iframe içinde olur. Kullanıcı kodu sayfaya erişemez; çıktı `postMessage`
  ile geri döner. Program sayfayla konuşuyorsa (`bul("#uygulama")`) o
  iframe aynı zamanda ekranıdır — yani arayüz örnekleri gerçekten çizilir.
- **Paylaşma** kodu adres çubuğuna gömer; sunucu yok, bağlantı yeter.

Üretim:
    python site/oyun.py                 -> docs/deneme/
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from narc import __version__  # noqa: E402
from narc.driver import compile_file  # noqa: E402

import tasarim  # noqa: E402
from tasarim import (  # noqa: E402
    IKON_AY, IKON_GUNES, IKON_KOD, IKON_KOPYA, IKON_OK, IKON_ONAY,
)
from icerik import BASLIK, DEPO  # noqa: E402

# Pyodide sürümü sabitlenir: "latest" bir gün sessizce değişir ve sayfa
# çalışmayı bırakır.
PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"

ILK_KOD = """// Nar'a hoş geldin. Değiştir ve Çalıştır'a bas (Ctrl+Enter).

struct Kisi {
  ad: String
  yas: Int
}

fn selamla(k: Kisi) -> String =
  "Merhaba ${k.ad}, ${k.yas} yaşındasın."

fn main() {
  let kisiler = [
    Kisi { ad: "Ayşe", yas: 30 },
    Kisi { ad: "Mehmet", yas: 17 },
    Kisi { ad: "Zeynep", yas: 24 }
  ]

  for k in kisiler {
    print(selamla(k))
  }

  let yetiskinler = kisiler.filter(|k| k.yas >= 18)
  print("yetişkin sayısı:", yetiskinler.len())
}
"""

# Sol üstteki hazır örnekler. Hepsi kısa: amaç dilin farklı yanlarını tek
# ekranda göstermek.
ORNEKLER = [
    ("Başlangıç", ILK_KOD),
    ("Tip güvenliği", """// Nar tipleri derleme anında denetler.
// Aşağıdaki satırın yorumunu kaldır, hatayı Türkçe gör.

fn main() {
  let yas: Int = 30
  // let ad: String = yas

  print("yaş:", yas)
}
"""),
    ("match ve enum", """enum Sekil {
  Daire(Float)
  Dikdortgen(Float, Float)
  Kare(Float)
}

fn alan(s: Sekil) -> Float = match s {
  Daire(r) -> 3.14159 * r * r
  Dikdortgen(en, boy) -> en * boy
  Kare(k) -> k * k
}

fn main() {
  let sekiller = [Daire(2.0), Dikdortgen(3.0, 4.0), Kare(5.0)]
  for s in sekiller {
    print(alan(s))
  }
}
"""),
    ("Arayüz çizmek", """// Bu örnek ekrana çizer: sağdaki "Ekran" sekmesine bak.

fn main() {
  let alan = bul("#uygulama")
  if alan == none {
    print("Bu program bir sayfada çalışmalı.")
    return
  }

  var sayac = 0

  let baslik = olustur("h2")
  baslik.metinYaz("Sayaç")

  let deger = olustur("p")
  deger.metinYaz("0")

  let dugme = olustur("button")
  dugme.metinYaz("Artır")
  dugme.dinle("click", |o| {
    sayac += 1
    deger.metinYaz("${sayac}")
  })

  alan!.ekle(baslik)
  alan!.ekle(deger)
  alan!.ekle(dugme)
}
"""),
]


# ------------------------------------------------------------------ paket

# Derleyiciyi çalıştırmak için gereken en küçük küme. `__main__.py`,
# masaüstü/mobil paketleyiciler ve sanal makine tarayıcıya gitmez.
PAKET_DISI = {
    "__main__.py", "masaustu_paket.py", "mobil_paket.py", "ghb_paket.py",
    "ghb_calistir.py", "uzanti_kayit.py", "vm.py", "vm_metotlar.py",
    "bytecode.py", "renk.py", "bicim.py",
}


def narc_zip(hedef: Path) -> int:
    """`narc` paketini tarayıcıya götürülecek zip'e yazar; boyutu döndürür."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for yol in sorted((KOK / "narc").rglob("*.py")):
            if yol.name in PAKET_DISI or "__pycache__" in yol.parts:
                continue
            if yol.parent.name == "backends" and yol.name == "bytecode_uretici.py":
                continue
            z.write(yol, str(yol.relative_to(KOK)).replace("\\", "/"))
        # Üretilen programın başına gömülen çalışma zamanı.
        calisma = KOK / "narc" / "runtime" / "nar_runtime.js"
        z.write(calisma, "narc/runtime/nar_runtime.js")

    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(tampon.getvalue())
    return len(tampon.getvalue())


def renklendirici_js() -> str:
    """`araclar/renklendirici.nar`'ı kütüphane olarak JavaScript'e derler."""
    return compile_file(KOK / "araclar" / "renklendirici.nar",
                        kutuphane=True).to_js()


def kodu_sar(kaynak: str) -> str:
    """Kaynağı adres çubuğunda taşınabilir hâle getirir."""
    return base64.urlsafe_b64encode(kaynak.encode("utf-8")).decode("ascii")


# -------------------------------------------------------------------- stil

def stil() -> str:
    """Playground'a özgü stil. Renk ve yazı tipi belgelerle ortak."""
    return """
/* --------------------------------------------------------- deneme alanı */

.deneme {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1px;
  background: var(--kenar);
  height: calc(100vh - var(--bar));
  border-top: 1px solid var(--kenar);
}
.bolme {
  display: flex; flex-direction: column; min-width: 0; min-height: 0;
  background: var(--zemin);
}

.arac {
  display: flex; align-items: center; gap: 8px;
  padding: 0 12px; height: 42px; flex: none;
  border-bottom: 1px solid var(--kenar);
  background: var(--yuzey);
}
.arac-etiket {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--metin-soluk);
}
.arac .sag { margin-left: auto; display: flex; align-items: center; gap: 6px; }

.dugme {
  display: inline-flex; align-items: center; gap: 6px;
  height: 28px; padding: 0 10px;
  font: inherit; font-size: 12.5px;
  color: var(--metin); background: var(--yuzey-2);
  border: 1px solid var(--kenar); border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color .2s ease, background .2s ease, color .2s ease;
}
.dugme:hover { border-color: var(--kenar-guclu); }
.dugme[disabled] { opacity: .5; cursor: default; }
.dugme.bitti { color: var(--vurgu); }
.dugme.bitti .onay { display: block; }
.dugme.bitti .kopya { display: none; }
.dugme .onay { display: none; }

.dugme-birincil {
  background: linear-gradient(180deg, var(--vurgu), var(--vurgu-uc));
  color: var(--vurgu-metin); border-color: transparent;
  font-weight: 500;
  box-shadow: 0 1px 0 0 #ffffff2e inset;
}
.dugme-birincil:hover { filter: brightness(1.06); }

select.dugme { padding-right: 6px; }

/* --- düzenleyici --------------------------------------------------------
   Yazma alanı saydam bir textarea; boyalı metin tam altında duran bir
   <pre>. İkisinin yazı ölçüleri birebir aynı olmalı, yoksa imleç kayar. */

.yazim { position: relative; flex: 1 1 auto; min-height: 0; overflow: auto; }

.yazim pre, .yazim textarea {
  margin: 0;
  padding: 14px 16px 40vh;
  font-family: var(--mono); font-size: 13.5px; line-height: 1.7;
  tab-size: 2;
  white-space: pre; word-wrap: normal;
  border: 0;
}
.yazim pre {
  min-height: 100%;
  pointer-events: none;
  color: var(--metin);
}
/* Tarayıcının kendi kuralı <code>'a `font-family: monospace` verir ve
   pre'den devralınan fontu ezer; boyalı metin başka fontla çizilince imleç
   sütun ilerledikçe kayar. İki katman aynı font, aynı boy, ligatürsüz. */
.yazim pre code { font: inherit; letter-spacing: inherit; }
.yazim pre, .yazim textarea {
  font-variant-ligatures: none; font-feature-settings: 'liga' 0, 'calt' 0;
  font-kerning: none;
}
.yazim textarea {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  resize: none; outline: none;
  background: transparent;
  color: transparent;
  caret-color: var(--vurgu);
  overflow: hidden;
}
.yazim textarea::selection { background: color-mix(in srgb, var(--vurgu) 28%, transparent); }

/* --- çıktı -------------------------------------------------------------- */

.sekmeler { display: flex; gap: 2px; }
.sekme {
  height: 28px; padding: 0 10px;
  font: inherit; font-size: 12.5px;
  color: var(--metin-soluk); background: none;
  border: 1px solid transparent; border-radius: var(--radius-md);
  cursor: pointer;
  transition: color .2s ease, background .2s ease;
}
.sekme:hover { color: var(--metin); background: var(--yuzey-2); }
.sekme[aria-selected="true"] {
  color: var(--vurgu); background: var(--vurgu-zemin);
  border-color: var(--kenar);
}

.pano { flex: 1 1 auto; min-height: 0; position: relative; }
.pano > * { position: absolute; inset: 0; }
.pano > [hidden] { display: none; }

#cikti {
  margin: 0; padding: 14px 16px;
  overflow: auto;
  font-family: var(--mono); font-size: 12.5px; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
  color: var(--metin);
}
#cikti .hata { color: var(--hata); }
#cikti .bilgi { color: var(--metin-soluk); }
#cikti .sure {
  display: block; margin-top: 10px;
  color: var(--metin-soluk); font-size: 11px;
}

#ekran { width: 100%; height: 100%; border: 0; background: var(--yuzey); }

.bos-ipucu {
  display: flex; align-items: center; justify-content: center;
  padding: 24px; text-align: center;
  color: var(--metin-soluk); font-size: 13px;
}

/* --- durum çubuğu -------------------------------------------------------- */

.durum {
  flex: none; display: flex; align-items: center; gap: 8px;
  padding: 0 12px; height: 30px;
  border-top: 1px solid var(--kenar);
  background: var(--yuzey);
  font-family: var(--mono); font-size: 11px; color: var(--metin-soluk);
}
.durum .nokta {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--kenar-guclu);
}
.durum.hazir .nokta { background: var(--vurgu); }
.durum.calisiyor .nokta { animation: nabiz 1s ease-in-out infinite; }
@keyframes nabiz { 50% { opacity: .25; } }

@media (max-width: 900px) {
  .deneme { grid-template-columns: minmax(0, 1fr); height: auto; }
  .bolme { height: 70vh; }
}
"""


# ------------------------------------------------------------------- betik

def betik() -> str:
    return """
(function () {
  'use strict';

  var kaynak = document.getElementById('kaynak');
  var boya = document.getElementById('boya');
  var cikti = document.getElementById('cikti');
  var ekran = document.getElementById('ekran');
  var calistirDugmesi = document.getElementById('calistir');
  var durum = document.getElementById('durum');
  var durumYazi = document.getElementById('durum-yazi');

  // --- boyama ------------------------------------------------------
  // Renklendirici Nar ile yazılmıştır; IDE ve belgeler sitesiyle aynı
  // kaynaktan gelir, o yüzden üçü arasında sessizce fark oluşamaz.
  function boya_() {
    var metin = kaynak.value;
    // Son satır boşsa <pre> onu yutar; imleç son satıra inince boya
    // kayar. Sona bir boşluk eklemek hizayı korur.
    boya.innerHTML = globalThis.Nar.renklendir(metin + '\\n');
  }

  kaynak.addEventListener('input', boya_);
  kaynak.addEventListener('scroll', function () {
    boya.parentNode.scrollTop = kaynak.scrollTop;
  });

  // Sekme tuşu odağı kaçırmasın: iki boşluk yazar.
  kaynak.addEventListener('keydown', function (o) {
    if (o.key === 'Tab') {
      o.preventDefault();
      var b = kaynak.selectionStart, s = kaynak.selectionEnd;
      kaynak.value = kaynak.value.slice(0, b) + '  ' + kaynak.value.slice(s);
      kaynak.selectionStart = kaynak.selectionEnd = b + 2;
      boya_();
    }
    if ((o.ctrlKey || o.metaKey) && o.key === 'Enter') {
      o.preventDefault();
      calistir();
    }
  });

  // --- çıktı -------------------------------------------------------
  function yaz(metin, sinif) {
    var s = document.createElement('span');
    if (sinif) s.className = sinif;
    s.textContent = metin + '\\n';
    cikti.appendChild(s);
  }
  function temizle() { cikti.textContent = ''; }

  function durumYaz(metin, sinif) {
    durumYazi.textContent = metin;
    durum.className = 'durum' + (sinif ? ' ' + sinif : '');
  }

  // --- sekmeler ----------------------------------------------------
  var sekmeler = Array.prototype.slice.call(document.querySelectorAll('.sekme'));
  function sekmeSec(ad) {
    sekmeler.forEach(function (s) {
      var secili = s.dataset.pano === ad;
      s.setAttribute('aria-selected', secili ? 'true' : 'false');
      document.getElementById(s.dataset.pano).hidden = !secili;
    });
  }
  sekmeler.forEach(function (s) {
    s.addEventListener('click', function () { sekmeSec(s.dataset.pano); });
  });

  // --- derleyici ---------------------------------------------------
  // Pyodide ancak ilk çalıştırmada indirilir: sayfayı okumaya gelen
  // kimse 9 MB ödemesin.
  var pyodide = null;
  var yukleniyor = null;

  function derleyiciyiHazirla() {
    if (pyodide) return Promise.resolve(pyodide);
    if (yukleniyor) return yukleniyor;

    durumYaz('derleyici indiriliyor…', 'calisiyor');
    yukleniyor = new Promise(function (coz, kir) {
      var s = document.createElement('script');
      s.src = PYODIDE_URL + 'pyodide.js';
      s.onload = coz;
      s.onerror = function () { kir(new Error('Pyodide yüklenemedi')); };
      document.head.appendChild(s);
    }).then(function () {
      return loadPyodide({ indexURL: PYODIDE_URL });
    }).then(function (py) {
      durumYaz('derleyici açılıyor…', 'calisiyor');
      return fetch('narc.zip').then(function (y) {
        if (!y.ok) throw new Error('narc.zip alınamadı');
        return y.arrayBuffer();
      }).then(function (paket) {
        py.unpackArchive(paket, 'zip');
        py.runPython(HAZIRLIK);
        pyodide = py;
        durumYaz('derleyici hazır', 'hazir');
        return py;
      });
    }).catch(function (h) {
      yukleniyor = null;
      durumYaz('derleyici yüklenemedi', '');
      throw h;
    });
    return yukleniyor;
  }

  // --- çalıştırma --------------------------------------------------
  var calisiyorMu = false;

  function calistir() {
    if (calisiyorMu) return;
    calisiyorMu = true;
    calistirDugmesi.disabled = true;
    temizle();
    yaz('derleniyor…', 'bilgi');

    derleyiciyiHazirla().then(function (py) {
      temizle();
      durumYaz('derleniyor…', 'calisiyor');
      var baslangic = performance.now();
      var sonuc = JSON.parse(py.runPython(
        'derle(' + JSON.stringify(kaynak.value) + ')'));
      var sure = Math.round(performance.now() - baslangic);

      if (!sonuc.tamam) {
        yaz(sonuc.hata, 'hata');
        durumYaz('derleme hatası', '');
        sekmeSec('pano-cikti');
        return;
      }
      durumYaz('derlendi · ' + sure + ' ms', 'hazir');
      programiCalistir(sonuc.kod);
    }).catch(function (h) {
      temizle();
      yaz('Derleyici çalıştırılamadı: ' + h.message, 'hata');
    }).then(function () {
      calisiyorMu = false;
      calistirDugmesi.disabled = false;
    });
  }

  // Kullanıcı kodu ayrı kökenli bir iframe'de çalışır: sayfaya, çerezlere
  // ve depolamaya erişemez. Çıktı postMessage ile geri gelir.
  var ciziliMi = false;

  function programiCalistir(kod) {
    ciziliMi = false;
    var belge =
      '<!doctype html><html lang="tr"><head><meta charset="utf-8">' +
      '<style>' + EKRAN_STILI + '</style></head><body>' +
      '<div id="uygulama"></div><script>' + KOPRU + '<\\/script>' +
      '<script>' + kod + '<\\/script>' +
      '<script>parent.postMessage({t:"bitti",cizdi:' +
      'document.getElementById("uygulama").childNodes.length>0},"*");<\\/script>' +
      '</body></html>';
    ekran.srcdoc = belge;
  }

  window.addEventListener('message', function (o) {
    var v = o.data;
    if (!v || typeof v !== 'object') return;
    if (v.t === 'log') yaz(v.s);
    else if (v.t === 'hata') { yaz(v.s, 'hata'); durumYaz('çalışma hatası', ''); }
    else if (v.t === 'bitti') {
      ciziliMi = v.cizdi;
      if (ciziliMi) sekmeSec('pano-ekran');
      else sekmeSec('pano-cikti');
    }
  });

  // --- paylaşma ----------------------------------------------------
  function sar(metin) {
    var baytlar = new TextEncoder().encode(metin);
    var ikilik = '';
    baytlar.forEach(function (b) { ikilik += String.fromCharCode(b); });
    return btoa(ikilik).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
  }
  function coz(metin) {
    var d = metin.replace(/-/g, '+').replace(/_/g, '/');
    var ikilik = atob(d);
    var baytlar = new Uint8Array(ikilik.length);
    for (var i = 0; i < ikilik.length; i++) baytlar[i] = ikilik.charCodeAt(i);
    return new TextDecoder().decode(baytlar);
  }

  var paylasDugmesi = document.getElementById('paylas');
  paylasDugmesi.addEventListener('click', function () {
    var adres = location.origin + location.pathname + '#k=' + sar(kaynak.value);
    history.replaceState(null, '', '#k=' + sar(kaynak.value));
    var bitir = function (oldu) {
      paylasDugmesi.classList.toggle('bitti', oldu);
      paylasDugmesi.querySelector('.yazi').textContent =
        oldu ? 'kopyalandı' : 'olmadı';
      setTimeout(function () {
        paylasDugmesi.classList.remove('bitti');
        paylasDugmesi.querySelector('.yazi').textContent = 'Paylaş';
      }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(adres).then(function () { bitir(true); },
                                                function () { bitir(false); });
    } else { bitir(false); }
  });

  // --- örnekler ----------------------------------------------------
  var secici = document.getElementById('ornek');
  secici.addEventListener('change', function () {
    if (!secici.value) return;
    kaynak.value = ORNEKLER[+secici.value];
    boya_();
    history.replaceState(null, '', location.pathname);
  });

  // --- açılış ------------------------------------------------------
  var basla = ORNEKLER[0];
  if (location.hash.indexOf('#k=') === 0) {
    try { basla = coz(location.hash.slice(3)); } catch (e) { /* bozuk bağlantı */ }
  }
  kaynak.value = basla;
  boya_();
  durumYaz('derleyici ilk çalıştırmada inecek', '');

  calistirDugmesi.addEventListener('click', calistir);
})();
"""


# Kullanıcı kodunun içinde çalışan köprü: konsolu ve hataları dışarı taşır.
KOPRU = """
(function () {
  var yolla = function (t, s) { parent.postMessage({ t: t, s: String(s) }, '*'); };
  var yaz = function () {
    yolla('log', Array.prototype.map.call(arguments, function (x) {
      return typeof x === 'string' ? x : JSON.stringify(x);
    }).join(' '));
  };
  console.log = yaz;
  console.info = yaz;
  console.warn = yaz;
  console.error = function () {
    yolla('hata', Array.prototype.join.call(arguments, ' '));
  };
  window.onerror = function (m) { yolla('hata', m); return true; };
  window.addEventListener('unhandledrejection', function (o) {
    yolla('hata', o.reason);
  });
})();
"""

# İframe içindeki ekranın stili. Programın çizdiği arayüz burada görünür;
# arayüz kütüphanesi kendi stilini zaten kendi getiriyor.
EKRAN_STILI = """
:root { color-scheme: light dark; }
body {
  margin: 0; padding: 16px;
  font: 15px/1.6 'IBM Plex Sans', system-ui, sans-serif;
  background: Canvas; color: CanvasText;
}
"""

# Pyodide içinde bir kez çalışan hazırlık. `derle` tek bir kaynak metni
# alır ve JSON döndürür; hata durumunda Türkçe hata metnini verir.
HAZIRLIK = r'''
import json

from narc.backends import js as _js
from narc.checker import Checker
from narc.diagnostics import NarError
from narc.parser import parse


def derle(kaynak):
    try:
        modul = parse(kaynak, "deneme.nar")
        denetci = Checker(modul, kaynak)
        denetci.check()
        kod = _js.generate(modul, denetci)
    except NarError as hata:
        return json.dumps({"tamam": False, "hata": hata.render(kaynak)})
    except RecursionError:
        return json.dumps({"tamam": False,
                           "hata": "program çok derin: derleyici yığını taştı"})
    return json.dumps({"tamam": True, "kod": kod})
'''


# -------------------------------------------------------------------- sayfa

def sayfa(renklendirici: str) -> str:
    ornek_secenekleri = "".join(
        f'<option value="{i}">{html.escape(ad)}</option>'
        for i, (ad, _) in enumerate(ORNEKLER)
    )
    ornek_kodlari = json.dumps([kod for _, kod in ORNEKLER], ensure_ascii=False)

    sabitler = (
        f"var PYODIDE_URL = {json.dumps(PYODIDE)};\n"
        f"var ORNEKLER = {ornek_kodlari};\n"
        f"var HAZIRLIK = {json.dumps(HAZIRLIK)};\n"
        f"var KOPRU = {json.dumps(KOPRU)};\n"
        f"var EKRAN_STILI = {json.dumps(EKRAN_STILI)};\n"
    )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nar deneme alanı</title>
<meta name="description" content="Nar'ı kurmadan tarayıcıda dene: yaz, çalıştır, bağlantıyı paylaş.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?\
family=IBM+Plex+Sans:wght@400;500;600&\
family=JetBrains+Mono:wght@400;500&display=swap">
<style>{tasarim.stil()}</style>
<style>{stil()}</style>
</head>
<body>
<div lang="tr" class="kok">

<header class="bar">
  <a class="bar-marka" href="../">
    <b>{html.escape(BASLIK)}</b>
    <span class="surum">v{__version__}</span>
  </a>
  <span class="arac-etiket">deneme alanı</span>
  <div class="bar-sag">
    <a class="bar-dugme" href="../">{IKON_KOD}<span>Rehber</span></a>
    <a class="bar-dugme" href="{html.escape(DEPO)}" rel="noreferrer">
      <span>Kaynak</span></a>
    <button id="tema" class="bar-dugme" type="button" aria-pressed="false">
      <span class="gunes">{IKON_GUNES}</span><span class="ay">{IKON_AY}</span>
      <span class="gizli-metin">Temayı değiştir</span>
    </button>
  </div>
</header>

<main class="deneme">
  <section class="bolme" aria-label="Kod">
    <div class="arac">
      <button id="calistir" class="dugme dugme-birincil" type="button">
        Çalıştır{IKON_OK}
      </button>
      <select id="ornek" class="dugme" aria-label="Hazır örnek seç">
        <option value="">örnekler…</option>
        {ornek_secenekleri}
      </select>
      <div class="sag">
        <button id="paylas" class="dugme" type="button">
          <span class="kopya">{IKON_KOPYA}</span>
          <span class="onay">{IKON_ONAY}</span>
          <span class="yazi">Paylaş</span>
        </button>
      </div>
    </div>
    <div class="yazim">
      <pre aria-hidden="true"><code id="boya"></code></pre>
      <textarea id="kaynak" spellcheck="false" autocomplete="off"
                autocapitalize="off" autocorrect="off"
                aria-label="Nar kaynağı"></textarea>
    </div>
    <div id="durum" class="durum">
      <span class="nokta"></span><span id="durum-yazi">hazır</span>
    </div>
  </section>

  <section class="bolme" aria-label="Sonuç">
    <div class="arac">
      <div class="sekmeler" role="tablist">
        <button class="sekme" type="button" role="tab" data-pano="pano-cikti"
                aria-selected="true">Çıktı</button>
        <button class="sekme" type="button" role="tab" data-pano="pano-ekran"
                aria-selected="false">Ekran</button>
      </div>
      <span class="sag arac-etiket">Ctrl+Enter</span>
    </div>
    <div class="pano">
      <pre id="pano-cikti"><code id="cikti"></code></pre>
      <div id="pano-ekran" hidden>
        <iframe id="ekran" title="Programın çizdiği ekran"
                sandbox="allow-scripts"></iframe>
      </div>
    </div>
  </section>
</main>

</div>
<script>{renklendirici}</script>
<script>{sabitler}</script>
<script>{tasarim.SCRIPT}</script>
<script>{betik()}</script>
</body>
</html>
"""


def main() -> int:
    ayristirici = argparse.ArgumentParser(
        description="Nar deneme alanını (playground) üretir")
    ayristirici.add_argument(
        "--cikti", type=Path, default=KOK / "docs" / "deneme",
        help="çıktı klasörü")
    args = ayristirici.parse_args()

    args.cikti.mkdir(parents=True, exist_ok=True)

    boyut = narc_zip(args.cikti / "narc.zip")
    renklendirici = renklendirici_js()
    (args.cikti / "index.html").write_text(sayfa(renklendirici), encoding="utf-8")

    print(f"yazıldı: {args.cikti / 'index.html'}")
    print(f"derleyici paketi: {boyut // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
