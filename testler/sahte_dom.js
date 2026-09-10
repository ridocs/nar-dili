// Node için küçük bir sahte DOM.
//
// Arayüz kütüphanesini tarayıcı açmadan test edebilmek için var. Gerçek DOM'un
// tamamını değil, Nar'ın Element bağlamasının kullandığı yüzeyi taklit eder:
// createElement / querySelector, appendChild, textContent, style, olaylar.
//
// Testin sonunda ağaç `$dom.metin(kok)` ile düz metne çevrilip karşılaştırılır;
// olaylar `$dom.tikla(dugme)` ile tetiklenir.

class SahteOge {
  constructor(etiket) {
    this.tagName = etiket.toUpperCase();
    this.childNodes = [];
    this.parentNode = null;
    this.dinleyiciler = {};
    this.ozellikler = {};
    this.stiller = {};
    this.value = "";
    this._metin = "";
    this.style = {
      setProperty: (ad, deger) => { this.stiller[ad] = deger; },
    };
    this.classList = {
      add: () => {},
      remove: () => {},
      contains: () => false,
    };
  }

  get firstChild() {
    return this.childNodes.length ? this.childNodes[0] : null;
  }

  get textContent() {
    if (this.childNodes.length === 0) return this._metin;
    return this.childNodes.map((c) => c.textContent).join("");
  }

  set textContent(v) {
    this.childNodes = [];
    this._metin = String(v);
  }

  appendChild(c) {
    c.parentNode = this;
    this.childNodes.push(c);
    return c;
  }

  removeChild(c) {
    const i = this.childNodes.indexOf(c);
    if (i >= 0) this.childNodes.splice(i, 1);
    c.parentNode = null;
    return c;
  }

  setAttribute(ad, deger) { this.ozellikler[ad] = String(deger); }
  getAttribute(ad) { return ad in this.ozellikler ? this.ozellikler[ad] : null; }

  addEventListener(tur, islev) {
    (this.dinleyiciler[tur] = this.dinleyiciler[tur] || []).push(islev);
  }

  tetikle(tur, olay) {
    for (const f of this.dinleyiciler[tur] || []) f(olay || { target: this });
  }

  focus() {}

  querySelector(secici) {
    return ara(this, secici);
  }

  querySelectorAll(secici) {
    const bulunan = [];
    tara(this, secici, bulunan);
    return bulunan;
  }
}

// Yalnızca `#kimlik` ve etiket adı seçicileri desteklenir; testin ihtiyacı bu.
function uyuyorMu(oge, secici) {
  if (secici.startsWith("#")) return oge.ozellikler.id === secici.slice(1);
  return oge.tagName === secici.toUpperCase();
}

function ara(kok, secici) {
  for (const c of kok.childNodes) {
    if (uyuyorMu(c, secici)) return c;
    const alt = ara(c, secici);
    if (alt) return alt;
  }
  return null;
}

function tara(kok, secici, bulunan) {
  for (const c of kok.childNodes) {
    if (uyuyorMu(c, secici)) bulunan.push(c);
    tara(c, secici, bulunan);
  }
}

const belge = new SahteOge("html");
const govde = new SahteOge("body");
belge.appendChild(govde);

globalThis.document = {
  body: govde,
  createElement: (etiket) => new SahteOge(etiket),
  querySelector: (secici) => (uyuyorMu(govde, secici) ? govde : ara(belge, secici)),
  querySelectorAll: (secici) => { const b = []; tara(belge, secici, b); return b; },
};

// Testlerin kullandığı yardımcılar.
globalThis.$dom = {
  govde,
  // Kök öğeye `id` verip sayfaya ekler; Nar programı `bul("#ad")` ile bulur.
  kokKur(kimlik) {
    const kok = new SahteOge("div");
    kok.setAttribute("id", kimlik);
    govde.appendChild(kok);
    return kok;
  },
  // Ağacı satır satır düz metne çevirir: her öğe kendi metniyle bir satır.
  satirlar(oge) {
    const cikti = [];
    const gez = (o) => {
      if (o.childNodes.length === 0) {
        const m = o.textContent.trim();
        const d = o.ozellikler.placeholder;
        if (m) cikti.push(m);
        else if (o.tagName === "INPUT") cikti.push(`<giris:${o.value}|${d || ""}>`);
      } else {
        for (const c of o.childNodes) gez(c);
      }
    };
    gez(oge);
    return cikti;
  },
  // Metnine göre bir düğme bulur.
  dugme(kok, etiket) {
    for (const d of kok.querySelectorAll("button")) {
      if (d.textContent.trim() === etiket) return d;
    }
    return null;
  },
  giris(kok) {
    return kok.querySelector("input");
  },
  tikla(oge) {
    if (oge === null) throw new Error("tıklanacak öğe bulunamadı");
    oge.tetikle("click", { target: oge });
  },
  yaz(giris, metin) {
    giris.value = metin;
    giris.tetikle("input", { target: giris });
  },
};
