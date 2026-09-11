// Nar çalışma zamanı — JavaScript arka ucu.
// Üretilen kodun başına gömülür. Tüm isimler `$` ile başlar; Nar
// tanımlayıcıları `$` içeremediği için çakışma olamaz.

"use strict";

class NarPanic extends Error {
  constructor(message) {
    super(message);
    this.name = "NarPanic";
  }
}

function $panic(message) {
  throw new NarPanic(message);
}

function $assert(cond, message) {
  if (!cond) $panic(message === undefined ? "assert başarısız" : message);
}

// --- sayılar ---------------------------------------------------------------
function $idiv(a, b) {
  if (b === 0) $panic("sıfıra bölme");
  return Math.trunc(a / b);
}

function $imod(a, b) {
  if (b === 0) $panic("sıfıra bölme (mod)");
  return a % b;
}

function $fdiv(a, b) {
  return a / b;
}

// --- opsiyoneller ----------------------------------------------------------
function $unwrap(value, where) {
  if (value === null || value === undefined) {
    $panic("'none' değeri açılmaya çalışıldı" + (where ? " (" + where + ")" : ""));
  }
  return value;
}

function $opt(v, f) {
  return (v === null || v === undefined) ? null : f(v);
}

// --- Türkçe harf duyarlı dönüşüm -------------------------------------------
// Standart upper()/lower() dil-bağımsızdır: "i" → "I". Türkçe metinde
// doğru sonuç için upperTr()/lowerTr() kullanılır: "i" → "İ", "I" → "ı".
function $upperTr(s) {
  return s.replace(/i/g, "İ").replace(/ı/g, "I").toUpperCase();
}

function $lowerTr(s) {
  return s.replace(/I/g, "ı").replace(/İ/g, "i").toLowerCase();
}

// --- eşitlik ---------------------------------------------------------------
function $eq(a, b) {
  if (a === b) return true;
  if (a === null || b === null || a === undefined || b === undefined) {
    return (a === null || a === undefined) && (b === null || b === undefined);
  }
  if (typeof a !== "object" || typeof b !== "object") return false;

  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (!$eq(a[i], b[i])) return false;
    return true;
  }
  if (a instanceof Map) {
    if (!(b instanceof Map) || a.size !== b.size) return false;
    for (const [k, v] of a) {
      if (!b.has(k) || !$eq(v, b.get(k))) return false;
    }
    return true;
  }
  if (a.$tag !== undefined || b.$tag !== undefined) {
    if (a.$tag !== b.$tag) return false;
    return $eq(a.$values, b.$values);
  }
  if (a.constructor !== b.constructor) return false;
  const keys = Object.keys(a);
  if (keys.length !== Object.keys(b).length) return false;
  for (const k of keys) if (!$eq(a[k], b[k])) return false;
  return true;
}

// --- metne çevirme ---------------------------------------------------------
// Tip bilgisi kod üreticiden gelir; JavaScript `4` ile `4.0` arasını
// ayıramadığı için Float'ların doğru yazılması buna bağlıdır.
//
// Tip kodu:  "Int" | "Float" | "Bool" | "String" | <tip adı>
//            ["l", T]  liste   ["m", K, V]  eşleme   ["o", T]  opsiyonel
const $types = Object.create(null);

function $defType(name, def) {
  $types[name] = def;
}

function $strFloat(v) {
  if (v === null || v === undefined) return "none";
  if (!Number.isFinite(v)) return String(v);
  return Number.isInteger(v) ? v.toFixed(1) : String(v);
}

function $fmt(v, t, quoted) {
  if (v === null || v === undefined) return "none";

  if (Array.isArray(t)) {
    if (t[0] === "o") return $fmt(v, t[1], quoted);
    if (t[0] === "u") return $fmtGenerik(v, t[1], t[2], quoted);
    if (t[0] === "l") return "[" + v.map((x) => $fmt(x, t[1], true)).join(", ") + "]";
    if (t[0] === "m") {
      const parts = [];
      for (const [k, val] of v) parts.push($fmt(k, t[1], true) + ": " + $fmt(val, t[2], true));
      return "{" + parts.join(", ") + "}";
    }
  }

  if (t === "Float") return $strFloat(v);
  if (t === "String") return quoted ? JSON.stringify(v) : v;

  if (typeof v === "string") return quoted ? JSON.stringify(v) : v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (typeof v === "function") return "<fonksiyon>";

  if (Array.isArray(v)) return "[" + v.map((x) => $fmt(x, undefined, true)).join(", ") + "]";
  if (v instanceof Map) {
    const parts = [];
    for (const [k, val] of v) parts.push($fmt(k, undefined, true) + ": " + $fmt(val, undefined, true));
    return "{" + parts.join(", ") + "}";
  }

  // Sayfa öğeleri: `<div id="x" class="y">` biçiminde kısaca gösterilir.
  if (typeof Element !== "undefined" && v instanceof Element) {
    let etiket = v.tagName.toLowerCase();
    if (v.id) etiket += "#" + v.id;
    if (v.className && typeof v.className === "string") {
      etiket += "." + v.className.trim().split(/\s+/).join(".");
    }
    return "<" + etiket + ">";
  }

  const name = v.constructor && v.constructor.$narName;
  const def = name ? $types[name] : undefined;

  if (v.$tag !== undefined) {
    const payload = def && def.variants ? def.variants[v.$tag] : undefined;
    if (!v.$values || v.$values.length === 0) return name + "." + v.$tag;
    const shown = v.$values.map((x, i) => $fmt(x, payload ? payload[i] : undefined, true));
    return name + "." + v.$tag + "(" + shown.join(", ") + ")";
  }

  const keys = Object.keys(v);
  const fieldTypes = def && def.fields ? def.fields : {};
  const shown = keys.map((k) => k + ": " + $fmt(v[k], fieldTypes[k], true));
  return name + " { " + shown.join(", ") + " }";
}

// Uygulanmış generic tip: şablondaki tip parametreleri (T, U…) verilen
// argümanlarla değiştirilerek alan tipleri bulunur.
function $genericEsleme(def, argler) {
  const esleme = Object.create(null);
  const params = (def && def.params) || [];
  for (let i = 0; i < params.length; i++) esleme[params[i]] = argler[i];
  return esleme;
}

function $tipiCoz(tip, esleme) {
  if (typeof tip === "string" && esleme[tip] !== undefined) return esleme[tip];
  if (Array.isArray(tip)) {
    if (tip[0] === "l") return ["l", $tipiCoz(tip[1], esleme)];
    if (tip[0] === "o") return ["o", $tipiCoz(tip[1], esleme)];
    if (tip[0] === "m") return ["m", $tipiCoz(tip[1], esleme), $tipiCoz(tip[2], esleme)];
    if (tip[0] === "u") return ["u", tip[1], tip[2].map((a) => $tipiCoz(a, esleme))];
  }
  return tip;
}

function $fmtGenerik(v, ad, argler, quoted) {
  const def = $types[ad];
  if (!def) return $fmt(v, undefined, quoted);
  const esleme = $genericEsleme(def, argler);

  if (v.$tag !== undefined) {
    const yuk = def.variants ? def.variants[v.$tag] : undefined;
    if (!v.$values || v.$values.length === 0) return ad + "." + v.$tag;
    const shown = v.$values.map((x, i) =>
      $fmt(x, yuk ? $tipiCoz(yuk[i], esleme) : undefined, true));
    return ad + "." + v.$tag + "(" + shown.join(", ") + ")";
  }

  const alanlar = def.fields || {};
  const shown = Object.keys(v).map(
    (k) => k + ": " + $fmt(v[k], $tipiCoz(alanlar[k], esleme), true));
  return ad + " { " + shown.join(", ") + " }";
}

function $str(v) {
  return $fmt(v, undefined, false);
}

function $print(v) {
  console.log($str(v));
}

// --- uzunluk ve dizinleme --------------------------------------------------
function $len(v) {
  if (v === null || v === undefined) $panic("'none' üzerinde len çağrıldı");
  if (typeof v === "string") return $karakterDizisi(v).length;
  if (Array.isArray(v)) return v.length;
  if (v instanceof Map) return v.size;
  $panic("len bu değer üzerinde tanımlı değil");
}

function $listGet(list, i) {
  if (i < 0 || i >= list.length) {
    $panic("liste sınırı aşıldı: dizin " + i + ", uzunluk " + list.length);
  }
  return list[i];
}

function $listSet(list, i, v) {
  if (i < 0 || i >= list.length) {
    $panic("liste sınırı aşıldı: dizin " + i + ", uzunluk " + list.length);
  }
  list[i] = v;
}

// Metinler kod noktası bazlı dizinlenir (emoji, birleşik karakterler doğru
// sayılsın diye). Her erişimde diziye çevirmek uzun metinlerde O(n²) yapardı;
// bu yüzden uzun metinlerin karakter dizisi küçük bir önbellekte tutulur.
const $DIZI_ONBELLEK = new Map();
const $ONBELLEK_ESIGI = 64;
const $ONBELLEK_BOYU = 4;

function $karakterDizisi(s) {
  if (s.length < $ONBELLEK_ESIGI) return Array.from(s);
  let dizi = $DIZI_ONBELLEK.get(s);
  if (dizi === undefined) {
    dizi = Array.from(s);
    if ($DIZI_ONBELLEK.size >= $ONBELLEK_BOYU) {
      $DIZI_ONBELLEK.delete($DIZI_ONBELLEK.keys().next().value);
    }
    $DIZI_ONBELLEK.set(s, dizi);
  }
  return dizi;
}

function $strGet(s, i) {
  const chars = $karakterDizisi(s);
  if (i < 0 || i >= chars.length) {
    $panic("metin sınırı aşıldı: dizin " + i + ", uzunluk " + chars.length);
  }
  return chars[i];
}

function $mapGet(m, k) {
  return m.has(k) ? m.get(k) : null;
}

// --- liste metotları -------------------------------------------------------
function $listPop(list) {
  return list.length === 0 ? null : list.pop();
}

function $listFirst(list) {
  return list.length === 0 ? null : list[0];
}

function $listLast(list) {
  return list.length === 0 ? null : list[list.length - 1];
}

function $listIndexOf(list, x) {
  for (let i = 0; i < list.length; i++) if ($eq(list[i], x)) return i;
  return -1;
}

function $listContains(list, x) {
  return $listIndexOf(list, x) !== -1;
}

function $listSort(list) {
  const copy = list.slice();
  copy.sort((a, b) => {
    if (typeof a === "string") return a < b ? -1 : a > b ? 1 : 0;
    return a - b;
  });
  return copy;
}

function $listConcat(a, b) {
  return a.concat(b);
}

function $listReverse(list) {
  return list.slice().reverse();
}

function $listSlice(list, a, b) {
  return list.slice(a, b);
}

function $listReduce(list, f, init) {
  let acc = init;
  for (const item of list) acc = f(acc, item);
  return acc;
}

// --- kolay liste işlemleri -------------------------------------------------
// Lambda yazmadan kullanılabilen, adı kendini anlatan işlemler.
function $listToplam(list) {
  let t = 0;
  for (const x of list) t += x;
  return t;
}

function $listCarpim(list) {
  let t = 1;
  for (const x of list) t *= x;
  return t;
}

function $listOrtalama(list) {
  if (list.length === 0) $panic("boş listenin ortalaması alınamaz");
  return $listToplam(list) / list.length;
}

function $listEnBuyuk(list) {
  if (list.length === 0) return null;
  let e = list[0];
  for (const x of list) if (x > e) e = x;
  return e;
}

function $listEnKucuk(list) {
  if (list.length === 0) return null;
  let e = list[0];
  for (const x of list) if (x < e) e = x;
  return e;
}

function $listKat(list, n) {
  return list.map((x) => x * n);
}

function $listArtir(list, n) {
  return list.map((x) => x + n);
}

function $listBuyukler(list, n) {
  return list.filter((x) => x > n);
}

function $listKucukler(list, n) {
  return list.filter((x) => x < n);
}

function $listCiftler(list) {
  return list.filter((x) => x % 2 === 0);
}

function $listTekler(list) {
  return list.filter((x) => x % 2 !== 0);
}

function $listBenzersiz(list) {
  const out = [];
  for (const x of list) if (!$listContains(out, x)) out.push(x);
  return out;
}

function $listSay(list, x) {
  let n = 0;
  for (const e of list) if ($eq(e, x)) n++;
  return n;
}

function $listBuyukHarf(list) {
  return list.map($upperTr);
}

function $listKucukHarf(list) {
  return list.map($lowerTr);
}

function $listIcerenler(list, parca) {
  return list.filter((s) => s.includes(parca));
}

// --- metin metotları -------------------------------------------------------
function $strSlice(s, a, b) {
  return $karakterDizisi(s).slice(a, b).join("");
}

function $strSplit(s, sep) {
  return sep === "" ? $karakterDizisi(s).slice() : s.split(sep);
}

function $strIndexOf(s, sub) {
  return s.indexOf(sub);
}

function $strRepeat(s, n) {
  if (n < 0) $panic("repeat negatif sayı alamaz");
  return s.repeat(n);
}

// --- dönüşümler ------------------------------------------------------------
function $parseIntOpt(s) {
  const t = s.trim();
  if (!/^[+-]?\d+$/.test(t)) return null;
  const n = Number(t);
  return Number.isSafeInteger(n) ? n : null;
}

function $parseFloatOpt(s) {
  const t = s.trim();
  if (t === "" || !/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(t)) return null;
  const n = Number(t);
  return Number.isNaN(n) ? null : n;
}

function $toInt(v) {
  return Math.trunc(v);
}

function $toFloat(v) {
  return v;
}

// --- eşleme yardımcıları ---------------------------------------------------
function $mapKeys(m) {
  return Array.from(m.keys());
}

function $mapValues(m) {
  return Array.from(m.values());
}

function $mapRemove(m, k) {
  m.delete(k);
}

// --- sunucu ---------------------------------------------------------------
// Yalnızca Node ortamında anlamlıdır. Tarayıcıda `sunucu()` çağrılırsa
// program net bir hatayla durur; sessizce yanlış davranmaz.

function $istekNesnesi(req, govde) {
  const url = new URL(req.url, "http://" + (req.headers.host || "yerel"));
  return {
    $narIstek: true,
    yontem: req.method || "GET",
    yol: url.pathname,
    sorgu: url.searchParams,
    basliklar: req.headers || {},
    govde: govde,
    ip: (req.socket && req.socket.remoteAddress) || "",
  };
}

function $istekSorgu(istek, ad) {
  const deger = istek.sorgu.get(ad);
  return deger === null ? null : deger;
}

function $istekBaslik(istek, ad) {
  const deger = istek.basliklar[String(ad).toLowerCase()];
  return deger === undefined ? null : String(deger);
}

// Yanıt opak bir değerdir; alanları yalnızca buradaki yardımcılarla değişir.
function $yanit(durum, govde, tip) {
  return {
    $narYanit: true,
    durum: durum,
    govde: govde,
    basliklar: tip ? {"Content-Type": tip} : {},
  };
}

function $yanitBaslik(yanit, ad, deger) {
  yanit.basliklar[ad] = deger;
  return yanit;
}

function $yanitDurum(yanit, durum) {
  yanit.durum = durum;
  return yanit;
}

// Dosya uzantısından içerik tipi. Statik dosya sunarken gerekli: yanlış tip
// tarayıcının CSS'i metin, JS'i indirilecek dosya sanmasına yol açar.
const $ICERIK_TIPLERI = {
  html: "text/html; charset=utf-8",
  htm: "text/html; charset=utf-8",
  css: "text/css; charset=utf-8",
  js: "text/javascript; charset=utf-8",
  mjs: "text/javascript; charset=utf-8",
  json: "application/json; charset=utf-8",
  txt: "text/plain; charset=utf-8",
  md: "text/markdown; charset=utf-8",
  csv: "text/csv; charset=utf-8",
  xml: "application/xml; charset=utf-8",
  svg: "image/svg+xml",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  avif: "image/avif",
  ico: "image/x-icon",
  woff: "font/woff",
  woff2: "font/woff2",
  ttf: "font/ttf",
  otf: "font/otf",
  pdf: "application/pdf",
  zip: "application/zip",
  wasm: "application/wasm",
  mp3: "audio/mpeg",
  mp4: "video/mp4",
  webm: "video/webm",
};

function $icerikTipi(yol) {
  const nokta = String(yol).lastIndexOf(".");
  if (nokta < 0) return "application/octet-stream";
  const uzanti = String(yol).slice(nokta + 1).toLowerCase();
  return $ICERIK_TIPLERI[uzanti] || "application/octet-stream";
}

// Dosyayı içerik tipiyle birlikte yanıta çevirir; yoksa `none`.
// Metin dosyaları UTF-8, ötekiler ham bayt olarak okunur.
function $yanitDosya(yol) {
  const fs = $fs();
  if (!fs) return null;
  try {
    const tip = $icerikTipi(yol);
    const metinMi = tip.startsWith("text/") || tip.indexOf("charset") >= 0 ||
      tip === "image/svg+xml" || tip === "application/xml";
    const icerik = metinMi ? fs.readFileSync(yol, "utf8") : fs.readFileSync(yol);
    return $yanit(200, icerik, tip);
  } catch (e) {
    return null;
  }
}

function $sunucu(port, isleyici) {
  if (!$nodeMu()) $panic("sunucu() yalnızca Node ortamında çalışır");
  let http;
  try {
    http = require("http");
  } catch (e) {
    $panic("sunucu(): http modülü yüklenemedi");
  }

  const server = http.createServer((req, res) => {
    const parcalar = [];
    req.on("data", (p) => parcalar.push(p));
    req.on("end", () => {
      let yanit;
      try {
        const govde = Buffer.concat(parcalar).toString("utf8");
        yanit = isleyici($istekNesnesi(req, govde));
      } catch (e) {
        // Bir isteğin çökmesi sunucuyu düşürmemeli.
        console.error("sunucu: istek işlenirken hata:", e && e.message);
        yanit = $yanit(500, "500 — sunucu hatası", "text/plain; charset=utf-8");
      }
      if (!yanit || !yanit.$narYanit) {
        yanit = $yanit(500, "500 — geçersiz yanıt", "text/plain; charset=utf-8");
      }
      const basliklar = Object.assign({}, yanit.basliklar);
      if (!basliklar["Content-Type"]) {
        basliklar["Content-Type"] = "text/plain; charset=utf-8";
      }
      res.writeHead(yanit.durum, basliklar);
      res.end(yanit.govde);
    });
  });

  server.on("error", (e) => {
    if (e && e.code === "EADDRINUSE") {
      $panic("sunucu: " + port + " portu kullanımda");
    }
    $panic("sunucu: " + (e && e.message));
  });

  server.listen(port);
  return null;
}

// --- ortam ve kimlik -------------------------------------------------------

function $ortam(ad) {
  if (!$nodeMu()) return null;
  const deger = process.env[ad];
  return deger === undefined ? null : String(deger);
}

function $kripto() {
  if (!$nodeMu()) return null;
  try {
    return require("crypto");
  } catch (e) {
    return null;
  }
}

// Tahmin edilemez rastgele metin: oturum anahtarı, kimlik, tuz.
// Math.random() bu iş için uygun değildir.
function $rastgeleMetin(uzunluk) {
  if (uzunluk <= 0) return "";
  const harfler = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  const k = $kripto();
  if (k) {
    const bayt = k.randomBytes(uzunluk);
    let sonuc = "";
    for (let i = 0; i < uzunluk; i++) sonuc += harfler[bayt[i] % harfler.length];
    return sonuc;
  }
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const bayt = new Uint8Array(uzunluk);
    crypto.getRandomValues(bayt);
    let sonuc = "";
    for (let i = 0; i < uzunluk; i++) sonuc += harfler[bayt[i] % harfler.length];
    return sonuc;
  }
  $panic("rastgeleMetin(): bu ortamda güvenli rastgelelik yok");
}

function $sha256(metin) {
  const k = $kripto();
  if (!k) $panic("sha256(): bu ortamda crypto yok");
  return k.createHash("sha256").update(String(metin), "utf8").digest("hex");
}

// --- karakter kodları ------------------------------------------------------
// Kod noktası (code point) kullanılır, kod birimi değil: emoji gibi
// BMP dışı karakterler de tek parça sayılır.
function $karakterKodu(s) {
  if (s.length === 0) $panic("kodu(): boş metnin karakter kodu yok");
  return s.codePointAt(0);
}

function $koddanKarakter(n) {
  if (n < 0 || n > 0x10ffff) $panic("koddan(): geçersiz karakter kodu: " + n);
  return String.fromCodePoint(n);
}

// --- sayfa (DOM) işlemleri -------------------------------------------------
// Yalnızca tarayıcıda anlamlıdır. Node ile çalıştırıldığında `bul` none
// döndürür ve diğerleri sessizce hiçbir şey yapmaz — program çökmez.
function $belgeVarMi() {
  return typeof document !== "undefined" && document !== null;
}

function $bul(secici) {
  if (!$belgeVarMi()) return null;
  return document.querySelector(secici);
}

function $bulHepsi(secici) {
  if (!$belgeVarMi()) return [];
  return Array.from(document.querySelectorAll(secici));
}

function $olustur(etiket) {
  if (!$belgeVarMi()) $panic("olustur() yalnızca tarayıcıda kullanılabilir");
  return document.createElement(etiket);
}

function $govde() {
  if (!$belgeVarMi()) $panic("govde() yalnızca tarayıcıda kullanılabilir");
  return document.body;
}

function $ogeBul(oge, secici) {
  return oge.querySelector(secici);
}

function $ogeBulHepsi(oge, secici) {
  return Array.from(oge.querySelectorAll(secici));
}

function $ogeOzellik(oge, ad) {
  const deger = oge.getAttribute(ad);
  return deger === null ? null : deger;
}

function $ogeDeger(oge) {
  return oge.value === undefined ? "" : String(oge.value);
}

function $ogeTemizle(oge) {
  while (oge.firstChild) oge.removeChild(oge.firstChild);
}

function $ogeCikar(oge) {
  if (oge.parentNode) oge.parentNode.removeChild(oge);
}

function $ogeStil(oge, ad, deger) {
  oge.style.setProperty(ad, deger);
}

function $ogeYaziEkle(oge, metin) {
  // İmleç konumuna metin yazar; geri alma yığınını korumak için
  // setRangeText kullanılır.
  const bas = oge.selectionStart || 0;
  const son = oge.selectionEnd || 0;
  if (typeof oge.setRangeText === "function") {
    oge.setRangeText(metin, bas, son, "end");
  } else {
    oge.value = oge.value.slice(0, bas) + metin + oge.value.slice(son);
  }
}

function $olayKaynagi(olay) {
  const hedef = olay.target;
  if (typeof Element !== "undefined" && hedef instanceof Element) return hedef;
  return null;
}

function $zamanla(ms, islev) {
  if (typeof setTimeout === "undefined") $panic("zamanla() bu ortamda yok");
  setTimeout(islev, ms);
}

// Ağ isteği. Nar'da `async` yoktur; sonuç geri çağırma ile verilir.
function $istek(yontem, url, govde, islev) {
  if (typeof fetch === "undefined") {
    $panic("istek() bu ortamda yok");
  }
  const ayar = {method: yontem};
  if (govde !== "" && yontem !== "GET" && yontem !== "HEAD") {
    ayar.body = govde;
    ayar.headers = {"Content-Type": "application/json"};
  }
  fetch(url, ayar)
    .then((y) => y.text())
    .then((metin) => islev(metin))
    .catch((e) => islev(""));
}

// --- dosya, girdi ve zaman -------------------------------------------------
// Dosya işlemleri yalnızca Node ortamında anlamlıdır. Tarayıcıda okuma
// `none`, yazma `false` döner; program çökmez.
function $nodeMu() {
  return typeof process !== "undefined" && process.versions && process.versions.node;
}

function $fs() {
  if (!$nodeMu()) return null;
  try {
    return require("fs");
  } catch (e) {
    return null;
  }
}

function $dosyaOku(yol) {
  const fs = $fs();
  if (!fs) return null;
  try {
    return fs.readFileSync(yol, "utf8");
  } catch (e) {
    return null;
  }
}

function $dosyaYaz(yol, icerik) {
  const fs = $fs();
  if (!fs) return false;
  try {
    fs.writeFileSync(yol, icerik, "utf8");
    return true;
  } catch (e) {
    return false;
  }
}

function $dosyaEkle(yol, icerik) {
  const fs = $fs();
  if (!fs) return false;
  try {
    fs.appendFileSync(yol, icerik, "utf8");
    return true;
  } catch (e) {
    return false;
  }
}

function $dosyaVarMi(yol) {
  const fs = $fs();
  if (!fs) return false;
  try {
    return fs.existsSync(yol);
  } catch (e) {
    return false;
  }
}

function $dosyaSil(yol) {
  const fs = $fs();
  if (!fs) return false;
  try {
    fs.unlinkSync(yol);
    return true;
  } catch (e) {
    return false;
  }
}

function $klasorMu(yol) {
  const fs = $fs();
  if (!fs) return false;
  try {
    return fs.statSync(yol).isDirectory();
  } catch (e) {
    return false;
  }
}

function $klasorOlustur(yol) {
  const fs = $fs();
  if (!fs) return false;
  try {
    fs.mkdirSync(yol, {recursive: true});
    return true;
  } catch (e) {
    return false;
  }
}

function $klasorListele(yol) {
  const fs = $fs();
  if (!fs) return [];
  try {
    return fs.readdirSync(yol);
  } catch (e) {
    return [];
  }
}

// Girdi: ilk çağrıda tamamı okunur, sonra satır satır verilir.
let $girdiSatirlari = null;
let $girdiSirasi = 0;

function $tumGirdi() {
  if (!$nodeMu()) return "";
  const fs = $fs();
  if (!fs) return "";
  try {
    return fs.readFileSync(0, "utf8");
  } catch (e) {
    return "";
  }
}

function $satirOku() {
  if ($girdiSatirlari === null) {
    const ham = $tumGirdi();
    $girdiSatirlari = ham.length === 0 ? [] : ham.replace(/\r\n/g, "\n").split("\n");
    // Sondaki satır sonunun yarattığı boş satırı at.
    if ($girdiSatirlari.length > 0 &&
        $girdiSatirlari[$girdiSatirlari.length - 1] === "") {
      $girdiSatirlari.pop();
    }
  }
  if ($girdiSirasi >= $girdiSatirlari.length) return null;
  return $girdiSatirlari[$girdiSirasi++];
}

function $argumanlar() {
  if (!$nodeMu()) return [];
  return process.argv.slice(2);
}

function $cik(kod) {
  if ($nodeMu() && process.exit) process.exit(kod);
  $panic("çıkış istendi: " + kod);
}

function $simdi() {
  return Date.now();
}

function $zamanMetni() {
  const d = new Date();
  const iki = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + iki(d.getMonth() + 1) + "-" + iki(d.getDate()) +
         " " + iki(d.getHours()) + ":" + iki(d.getMinutes()) + ":" + iki(d.getSeconds());
}

// --- programın başlatılması ------------------------------------------------
function $bootstrap(main) {
  try {
    main();
  } catch (err) {
    if (err instanceof NarPanic) {
      const write = (s) => {
        if (typeof process !== "undefined" && process.stderr) process.stderr.write(s + "\n");
        else console.error(s);
      };
      write("panik: " + err.message);
      if (typeof process !== "undefined" && process.exit) process.exit(1);
      return;
    }
    throw err;
  }
}
