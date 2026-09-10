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

function $str(v) {
  return $fmt(v, undefined, false);
}

function $print(v) {
  console.log($str(v));
}

// --- uzunluk ve dizinleme --------------------------------------------------
function $len(v) {
  if (v === null || v === undefined) $panic("'none' üzerinde len çağrıldı");
  if (typeof v === "string") return Array.from(v).length;
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

function $strGet(s, i) {
  const chars = Array.from(s);
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

// --- metin metotları -------------------------------------------------------
function $strSlice(s, a, b) {
  return Array.from(s).slice(a, b).join("");
}

function $strSplit(s, sep) {
  return sep === "" ? Array.from(s) : s.split(sep);
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
