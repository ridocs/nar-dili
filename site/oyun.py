"""Tarayıcıda çalışan Nar deneme alanı — IDE'nin kendisi, sunucusuz.

Deneme alanı artık ayrı bir arayüz değil: `ide/arayuz.html` ve Nar ile
yazılmış `araclar/ide_uygulamasi.nar` olduğu gibi kullanılıyor. IDE her şeyi
`/api/...` çağrılarıyla yaptığı için, tarayıcıda o çağrıları yakalayan bir
köprü yetiyor:

- `/api/denetle`, `/api/uretilen`, `/api/calistir` → derleyici Pyodide
  üzerinde tarayıcıda çalışır (ilk kullanımda iner).
- `/api/dosyalar`, `/api/dosya` → örnekler ve rehber konuları sayfaya gömülü;
  "Çalışmalarım" tarayıcı depolamasında.
- `/api/kaydet` → tarayıcı depolaması.
- `/api/kelimeler` → kod önerisi sözlüğü sayfaya gömülü.

Programlar ayrı kökenli, betik dışında yetkisi olmayan bir iframe'de
çalışır; çıktı `postMessage` ile döner. Program sayfayla konuşuyorsa aynı
iframe onun ekranıdır (Ekran sekmesi).

IDE'de ne varsa burada da var: dosya ağacı, Sorunlar paneli, uyarılar, hata
altı çizgileri, kod önerisi, biçimlendirme. Tek kaynak, iki ev sahibi.

Üretim: `python site/uret.py --cikti docs/index.html` deneme alanını da yazar.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(KOK / "ide"))

from narc.driver import compile_file  # noqa: E402

# Pyodide sürümü sabitlenir: "latest" bir gün sessizce değişir ve sayfa
# çalışmayı bırakır.
PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"

ILK_KOD = """// Nar'a hoş geldin. Değiştir ve Çalıştır'a bas (Ctrl+Enter).
// Yazarken kod önerisi çıkar; Tab ile uygula.

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

# Hazır örnekler. Hepsi kısa: amaç dilin farklı yanlarını göstermek.
ORNEKLER = [
    ("baslangic", "Başlangıç", ILK_KOD),
    ("tip-guvenligi", "Tip güvenliği", """// Nar tipleri derleme anında denetler.
// Aşağıdaki satırın yorumunu kaldır, hatayı Türkçe gör.

fn main() {
  let yas: Int = 30
  // let ad: String = yas

  print("yaş:", yas)
}
"""),
    ("match-enum", "match ve enum", """enum Sekil {
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
    ("arayuz", "Arayüz çizmek", """// Bu örnek ekrana çizer: sağdaki "Ekran" sekmesine bak.

fn main() {
  if let alan = bul("#uygulama") {
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

    alan.ekle(baslik)
    alan.ekle(deger)
    alan.ekle(dugme)
  } else {
    print("Bu program bir sayfada çalışmalı.")
  }
}
"""),
]


# ------------------------------------------------------------------ paket

# Derleyiciyi çalıştırmak için gereken en küçük küme. `__main__.py`,
# paketleyiciler ve sanal makine tarayıcıya gitmez.
PAKET_DISI = {
    "__main__.py", "masaustu_paket.py", "mobil_paket.py", "ghb_paket.py",
    "ghb_calistir.py", "uzanti_kayit.py", "exe_paket.py", "vm.py",
    "vm_metotlar.py", "bytecode.py", "renk.py", "bicim.py",
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
        calisma = KOK / "narc" / "runtime" / "nar_runtime.js"
        z.write(calisma, "narc/runtime/nar_runtime.js")

    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(tampon.getvalue())
    return len(tampon.getvalue())


def ide_js() -> str:
    """IDE'nin Nar ile yazılmış davranışını kütüphane olarak derler."""
    return compile_file(KOK / "araclar" / "ide_uygulamasi.nar",
                        kutuphane=True).to_js()


def kodu_sar(kaynak: str) -> str:
    """Kaynağı adres çubuğunda taşınabilir hâle getirir."""
    return base64.urlsafe_b64encode(kaynak.encode("utf-8")).decode("ascii")


# Pyodide içinde bir kez çalışan hazırlık. Sunucunun verdiği sözlüklerin
# aynısını üretir; IDE ikisini ayırt edemez.
HAZIRLIK = r'''
import json

from narc.backends import js as _js
from narc.checker import Checker
from narc.diagnostics import NarError
from narc.parser import parse


def _sozluk(err, kaynak):
    return {
        "mesaj": err.message,
        "satir": err.span.line if err.span else None,
        "sutun": err.span.col if err.span else None,
        "uzunluk": err.span.length if err.span else 1,
        "ipucu": err.hint,
        "gosterim": err.render(kaynak),
    }


def _uyarilar(checker, kaynak):
    if checker is None:
        return []
    return [dict(_sozluk(u, kaynak), seviye="uyari") for u in checker.warnings]


def derle(kaynak):
    checker = None
    try:
        modul = parse(kaynak, "deneme.nar")
        checker = Checker(modul, kaynak)
        checker.check()
        kod = _js.generate(modul, checker)
    except NarError as err:
        sozluk = _sozluk(err, kaynak)
        hepsi = getattr(err, "errors", None)
        sozluk["hepsi"] = [_sozluk(h, kaynak) for h in hepsi] if hepsi else [dict(sozluk)]
        sozluk["adet"] = len(sozluk["hepsi"])
        if sozluk["adet"] > 1:
            sozluk["gosterim"] = "\n\n".join(h["gosterim"] for h in sozluk["hepsi"])
        return json.dumps({"tamam": False, "hata": sozluk,
                           "uyarilar": _uyarilar(checker, kaynak)})
    except RecursionError:
        return json.dumps({"tamam": False, "uyarilar": [], "hata": {
            "mesaj": "program çok derin iç içe geçmiş (özyineleme sınırı)",
            "satir": None, "sutun": None, "uzunluk": 1, "ipucu": None,
            "gosterim": "hata: program çok derin iç içe geçmiş",
            "hepsi": [], "adet": 1}})
    return json.dumps({"tamam": True, "hata": None, "kod": kod,
                       "uyarilar": _uyarilar(checker, kaynak)})
'''

# Kullanıcı kodunun içinde çalışan köprü: konsolu ve hataları dışarı taşır.
IFRAME_KOPRUSU = """
(function () {
  var yolla = function (t, s) { parent.postMessage({ t: t, s: String(s) }, '*'); };
  var yaz = function () {
    yolla('log', Array.prototype.map.call(arguments, function (x) {
      return typeof x === 'string' ? x : JSON.stringify(x);
    }).join(' '));
  };
  console.log = yaz; console.info = yaz; console.warn = yaz;
  console.error = function () { yolla('hata', Array.prototype.join.call(arguments, ' ')); };
  window.onerror = function (m) { yolla('hata', m); return true; };
  window.addEventListener('unhandledrejection', function (o) { yolla('hata', o.reason); });
})();
"""

EKRAN_STILI = """
:root { color-scheme: light dark; }
body { margin: 0; padding: 16px; font: 15px/1.6 'IBM Plex Sans', system-ui, sans-serif;
       background: Canvas; color: CanvasText; }
"""


# ------------------------------------------------------------------- köprü

KOPRU_JS = r"""
(function () {
  'use strict';

  // --- gömülü veri ----------------------------------------------------
  var DOSYALAR = __DOSYALAR__;          // yol -> kaynak
  var LISTE = __LISTE__;                // [{ad, yol, grup}]
  var KELIMELER = __KELIMELER__;
  var ILK_KOD = __ILK_KOD__;
  var PYODIDE_URL = __PYODIDE__;
  var HAZIRLIK = __HAZIRLIK__;
  var IFRAME_KOPRUSU = __IFRAME_KOPRUSU__;
  var EKRAN_STILI = __EKRAN_STILI__;
  var DEPO = 'nar-deneme-dosyalar';

  // --- tarayıcı depolaması: Çalışmalarım -------------------------------
  function kayitli() {
    try { return JSON.parse(localStorage.getItem(DEPO) || '{}'); } catch (e) { return {}; }
  }
  function sakla(map) {
    try { localStorage.setItem(DEPO, JSON.stringify(map)); return true; } catch (e) { return false; }
  }

  // Adres çubuğuyla paylaşılan kod "deneme.nar" olarak açılır.
  function coz(metin) {
    var d = metin.replace(/-/g, '+').replace(/_/g, '/');
    var ikilik = atob(d), b = new Uint8Array(ikilik.length);
    for (var i = 0; i < ikilik.length; i++) b[i] = ikilik.charCodeAt(i);
    return new TextDecoder().decode(b);
  }
  function sar(metin) {
    var b = new TextEncoder().encode(metin), s = '';
    b.forEach(function (x) { s += String.fromCharCode(x); });
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  var hashKod = null;
  if (location.hash.indexOf('#k=') === 0) {
    try { hashKod = coz(location.hash.slice(3)); } catch (e) { hashKod = null; }
  }

  function durumYaz(metin) {
    var d = document.getElementById('durum');
    if (d) d.textContent = metin;
  }

  // --- derleyici: Pyodide, ilk kullanımda -------------------------------
  var pyodide = null, yukleniyor = null;
  function derleyici() {
    if (pyodide) return Promise.resolve(pyodide);
    if (yukleniyor) return yukleniyor;
    durumYaz('derleyici indiriliyor… (bir kez, ~10 MB)');
    yukleniyor = new Promise(function (coz, kir) {
      var s = document.createElement('script');
      s.src = PYODIDE_URL + 'pyodide.js';
      s.onload = coz; s.onerror = function () { kir(new Error('Pyodide yüklenemedi')); };
      document.head.appendChild(s);
    }).then(function () {
      return loadPyodide({ indexURL: PYODIDE_URL });
    }).then(function (py) {
      durumYaz('derleyici açılıyor…');
      return fetchAsil('narc.zip').then(function (y) { return y.arrayBuffer(); }).then(function (paket) {
        py.unpackArchive(paket, 'zip');
        py.runPython(HAZIRLIK);
        pyodide = py;
        durumYaz('derleyici hazır');
        return py;
      });
    }).catch(function (h) { yukleniyor = null; durumYaz('derleyici yüklenemedi'); throw h; });
    return yukleniyor;
  }
  function derle(kaynak) {
    return derleyici().then(function (py) {
      return JSON.parse(py.runPython('derle(' + JSON.stringify(kaynak) + ')'));
    });
  }

  // --- çalıştırma: ayrı kökenli iframe ----------------------------------
  var bekleyen = null;
  window.addEventListener('message', function (o) {
    var v = o.data;
    if (!v || typeof v !== 'object' || !bekleyen) return;
    if (v.t === 'log') bekleyen.cikti.push(v.s);
    else if (v.t === 'hata') bekleyen.stderr.push(v.s);
    else if (v.t === 'bitti') { bekleyen.cizdi = !!v.cizdi; bekleyen.bitir(); }
  });
  function programiCalistir(kod) {
    return new Promise(function (coz) {
      var ekran = document.getElementById('ekran');
      var zaman = null;
      bekleyen = {
        cikti: [], stderr: [], cizdi: false,
        bitir: function () {
          clearTimeout(zaman);
          var b = bekleyen; bekleyen = null;
          coz({ cikti: b.cikti.join('\n'), stderr: b.stderr.join('\n'), cizdi: b.cizdi });
        }
      };
      zaman = setTimeout(function () { if (bekleyen) bekleyen.bitir(); }, 10000);
      ekran.srcdoc =
        '<!doctype html><html lang="tr"><head><meta charset="utf-8">' +
        '<style>' + EKRAN_STILI + '</style></head><body><div id="uygulama"></div>' +
        '<script>' + IFRAME_KOPRUSU + '<\/script>' +
        '<script>' + kod + '<\/script>' +
        '<script>parent.postMessage({t:"bitti",cizdi:document.getElementById("uygulama").childNodes.length>0},"*");<\/script>' +
        '</body></html>';
    });
  }

  // --- /api köprüsü ------------------------------------------------------
  var fetchAsil = window.fetch.bind(window);
  function yanit(obj, kod) {
    return new Response(JSON.stringify(obj), {
      status: kod || 200, headers: { 'Content-Type': 'application/json' } });
  }
  function govdeOku(ayar) {
    try { return ayar && ayar.body ? JSON.parse(ayar.body) : {}; } catch (e) { return {}; }
  }
  function dosyaListesi() {
    var liste = [{ ad: 'deneme.nar', yol: 'deneme.nar', grup: 'Oyun alanı' }];
    var k = kayitli();
    Object.keys(k).sort().forEach(function (yol) {
      if (yol !== 'deneme.nar') liste.push({ ad: yol.split('/').pop(), yol: yol, grup: 'Çalışmalarım' });
    });
    return liste.concat(LISTE);
  }
  function dosyaOku(yol) {
    if (yol === 'deneme.nar') {
      if (hashKod !== null) return hashKod;
      var k = kayitli();
      return k['deneme.nar'] !== undefined ? k['deneme.nar'] : ILK_KOD;
    }
    var kk = kayitli();
    if (kk[yol] !== undefined) return kk[yol];
    if (DOSYALAR[yol] !== undefined) return DOSYALAR[yol];
    return null;
  }

  window.fetch = function (url, ayar) {
    var u = String(url);
    if (u.indexOf('/api/') !== 0) return fetchAsil(url, ayar);
    var yol = u.split('?')[0];
    var sorgu = new URLSearchParams(u.split('?')[1] || '');
    var govde = govdeOku(ayar);

    if (yol === '/api/dosyalar') return Promise.resolve(yanit({ dosyalar: dosyaListesi(), surum: __SURUM__ }));
    if (yol === '/api/kelimeler') return Promise.resolve(yanit({ kelimeler: KELIMELER }));
    if (yol === '/api/dosya') {
      var y = sorgu.get('yol') || '';
      var kaynak = dosyaOku(y);
      if (kaynak === null) return Promise.resolve(yanit({ hata: 'dosya bulunamadı' }, 404));
      return Promise.resolve(yanit({ yol: y, kaynak: kaynak }));
    }
    if (yol === '/api/kaydet') {
      var map = kayitli();
      map[govde.yol] = govde.kaynak;
      if (govde.yol === 'deneme.nar') hashKod = null;
      return Promise.resolve(sakla(map) ? yanit({ tamam: true, yol: govde.yol })
                                        : yanit({ hata: 'tarayıcı depolaması kapalı' }, 400));
    }
    if (yol === '/api/denetle') {
      return derle(govde.kaynak || '').then(function (s) {
        return yanit({ tamam: s.tamam, hata: s.hata, uyarilar: s.uyarilar });
      }).catch(function (h) { return yanit({ tamam: true, hata: null, uyarilar: [] }); });
    }
    if (yol === '/api/uretilen') {
      return derle(govde.kaynak || '').then(function (s) {
        return yanit({ kod: s.kod || '', hata: s.hata });
      });
    }
    if (yol === '/api/calistir') {
      return derle(govde.kaynak || '').then(function (s) {
        if (!s.tamam) return yanit({ durum: 'derleme-hatasi', hata: s.hata, uyarilar: s.uyarilar, cikti: '' });
        durumYaz('çalışıyor…');
        return programiCalistir(s.kod).then(function (r) {
          durumYaz('hazır');
          return yanit({ durum: r.stderr ? 'calisma-hatasi' : 'tamam', cikti: r.cikti,
                         stderr: r.stderr, hata: null, cizdi: r.cizdi, uyarilar: s.uyarilar });
        });
      }).catch(function (h) {
        return yanit({ durum: 'ortam-hatasi', cikti: '', hata: {
          mesaj: 'derleyici çalıştırılamadı: ' + h.message, satir: null, sutun: null,
          uzunluk: 1, ipucu: null, gosterim: 'hata: ' + h.message, hepsi: [], adet: 1 } });
      });
    }
    return Promise.resolve(yanit({ hata: 'bulunamadı' }, 404));
  };

  // --- ev sahibine özgü düğme: Paylaş -----------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var kaydet = document.getElementById('btn-kaydet');
    if (!kaydet) return;
    var d = document.createElement('button');
    d.id = 'btn-paylas'; d.type = 'button'; d.title = 'Kodu bağlantı olarak kopyala';
    d.innerHTML = '<svg class="ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">' +
      '<path d="M10 14a4 4 0 0 0 6 .5l2-2a4 4 0 0 0-5.7-5.7L11 8M14 10a4 4 0 0 0-6-.5l-2 2A4 4 0 0 0 11.7 17L13 16"/></svg>Paylaş';
    kaydet.parentNode.insertBefore(d, kaydet.nextSibling);
    d.addEventListener('click', function () {
      var kod = document.getElementById('kod').value;
      var adres = location.origin + location.pathname + '#k=' + sar(kod);
      history.replaceState(null, '', '#k=' + sar(kod));
      var bitir = function (oldu) {
        durumYaz(oldu ? 'bağlantı kopyalandı' : 'bağlantı adres çubuğunda');
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(adres).then(function () { bitir(true); }, function () { bitir(false); });
      } else bitir(false);
    });
  });
})();
"""


def sayfa(ek_dosyalar: list[dict] | None = None) -> str:
    """IDE'nin arayüzünü tarayıcı köprüsüyle birleştirip deneme sayfasını üretir.

    `ek_dosyalar`: [{ad, yol, grup, kaynak}] — rehber konuları gibi ağaçta
    görünecek ek dosyalar.
    """
    from narc import __version__
    from sunucu import kelime_sozlugu  # ide/sunucu.py

    html = (KOK / "ide" / "arayuz.html").read_text(encoding="utf-8")

    dosyalar: dict[str, str] = {}
    liste: list[dict] = []
    for kimlik, ad, kod in ORNEKLER:
        yol = f"ornekler/{kimlik}.nar"
        dosyalar[yol] = kod
        liste.append({"ad": f"{ad}.nar", "yol": yol, "grup": "Örnekler"})
    for d in ek_dosyalar or []:
        dosyalar[d["yol"]] = d["kaynak"]
        liste.append({"ad": d["ad"], "yol": d["yol"], "grup": d["grup"]})

    kopru = (KOPRU_JS
             .replace("__DOSYALAR__", json.dumps(dosyalar, ensure_ascii=False))
             .replace("__LISTE__", json.dumps(liste, ensure_ascii=False))
             .replace("__KELIMELER__", json.dumps(kelime_sozlugu(), ensure_ascii=False))
             .replace("__ILK_KOD__", json.dumps(ILK_KOD, ensure_ascii=False))
             .replace("__PYODIDE__", json.dumps(PYODIDE))
             .replace("__HAZIRLIK__", json.dumps(HAZIRLIK))
             .replace("__IFRAME_KOPRUSU__", json.dumps(IFRAME_KOPRUSU))
             .replace("__EKRAN_STILI__", json.dumps(EKRAN_STILI))
             .replace("__SURUM__", json.dumps(__version__)))

    # `</script>` gömülü metinlerde geçebilir; betiği erken kapatmasın.
    kopru = kopru.replace("</script>", "<\\/script>")
    bundle = ide_js().replace("</script>", "<\\/script>")

    isaret = '<script src="/nar-ide.js"></script>'
    assert isaret in html, "ide/arayuz.html içinde nar-ide.js işareti yok"
    html = html.replace(
        isaret,
        "<!-- Tarayıcı köprüsü: IDE'nin /api çağrılarını burada karşılar. -->\n"
        f"<script>{kopru}</script>\n"
        "<!-- IDE'nin davranışı: araclar/ide_uygulamasi.nar, Nar ile yazıldı. -->\n"
        f"<script>{bundle}</script>",
    )
    html = html.replace("<title>Nar IDE</title>",
                        "<title>Nar deneme alanı</title>\n"
                        '<meta name="description" content="Nar\'ı kurmadan tarayıcıda dene: '
                        'IDE, derleyici ve çalıştırma tarayıcında.">')
    # Rehbere dönüş bağlantısı: marka tıklanınca rehber açılsın.
    html = html.replace('<div class="marka">Nar<span id="surum">IDE</span></div>',
                        '<a class="marka" href="../" style="text-decoration:none" '
                        'title="Rehbere dön">Nar<span id="surum">deneme</span></a>')
    return html
