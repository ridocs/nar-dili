"""AST'yi S-ifadesine (parantezli metne) çevirir.

Tek amacı **karşılaştırma**: Nar diliyle yazılan çözümleyici de aynı biçimi
üretir, böylece iki çözümleyicinin aynı ağacı kurup kurmadığı metin
karşılaştırmasıyla anlaşılır.

Konum (span) bilgisi yazılmaz — iki çözümleyicinin konumları birebir aynı
olmak zorunda değil, ağacın *yapısı* aynı olmak zorunda.

Biçim:
    (ad alt1 alt2 ...)      düğüm
    [a b c]                  liste
    "metin"                  metin (kaçışlı)
    true / false             mantıksal
    -                        yok (None)
"""

from __future__ import annotations

from . import nar_ast as A


def kacir(s: str) -> str:
    """Metni tırnak içinde, kaçışlarıyla yazar."""
    out = ['"']
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


# Konumun yazılıp yazılmayacağı. Nar tarafındaki `KONUM_YAZ` ile aynı rol.
_KONUM_YAZ = False


def konumla(metin: str, span) -> str:
    """Konumlu modda düğümün sonuna `@satır:sütun` ekler."""
    if not _KONUM_YAZ or span is None:
        return metin
    return f"{metin}@{span.line}:{span.col}"


def dugum(ad: str, *parcalar: str) -> str:
    if not parcalar:
        return f"({ad})"
    return f"({ad} " + " ".join(parcalar) + ")"


def liste(parcalar) -> str:
    return "[" + " ".join(parcalar) + "]"


def sayi_metni(deger) -> str:
    """Sayıyı iki tarafın da aynı yazacağı biçimde verir.

    Nar tarafında sayılar ham metin olarak taşınır; Python tarafında
    ayrıştırılmış hâlde. Ortak zemin: Python'un yazımı, ondalıkta `.0` eki.
    """
    if isinstance(deger, bool):
        return "true" if deger else "false"
    if isinstance(deger, float):
        metin = repr(deger)
        return metin
    return str(deger)


# --------------------------------------------------------------- tip yazımı
def tip(t) -> str:
    if t is None:
        return "-"
    return konumla(_tip(t), getattr(t, "span", None))


def _tip(t) -> str:
    if isinstance(t, A.NamedType):
        if t.args:
            return dugum("tad", kacir(t.name), liste(tip(a) for a in t.args))
        return dugum("tad", kacir(t.name))
    if isinstance(t, A.ListType):
        return dugum("tliste", tip(t.elem))
    if isinstance(t, A.MapType):
        return dugum("tesleme", tip(t.key), tip(t.value))
    if isinstance(t, A.OptionalType):
        return dugum("topsiyonel", tip(t.inner))
    if isinstance(t, A.FuncType):
        return dugum("tislev", liste(tip(p) for p in t.params), tip(t.ret))
    raise AssertionError(f"bilinmeyen tip düğümü: {type(t).__name__}")


def parametre(p: A.Param) -> str:
    return konumla(
        dugum("parametre", kacir(p.name), tip(p.type_expr), ifade(p.default)),
        p.span)


# ----------------------------------------------------------------- ifadeler
def ifade(e) -> str:
    if e is None:
        return "-"
    return konumla(_ifade(e), getattr(e, "span", None))


def _ifade(e) -> str:

    if isinstance(e, A.IntLit):
        return dugum("int", sayi_metni(e.value))
    if isinstance(e, A.FloatLit):
        return dugum("float", sayi_metni(e.value))
    if isinstance(e, A.BoolLit):
        return dugum("bool", "true" if e.value else "false")
    if isinstance(e, A.NoneLit):
        return dugum("none")

    if isinstance(e, A.StringLit):
        parcalar = []
        for p in e.parts:
            if isinstance(p, str):
                parcalar.append(dugum("duz", kacir(p)))
            else:
                parcalar.append(dugum("gomme", ifade(p)))
        return dugum("metin", liste(parcalar))

    if isinstance(e, A.Ident):
        return dugum("ad", kacir(e.name))
    if isinstance(e, A.SelfExpr):
        return dugum("self")

    if isinstance(e, A.ListLit):
        return dugum("liste", liste(ifade(i) for i in e.items))
    if isinstance(e, A.MapLit):
        return dugum("esleme", liste(
            dugum("cift", ifade(k), ifade(v)) for k, v in e.entries))

    if isinstance(e, A.StructLit):
        return dugum(
            "structlit",
            kacir(e.type_name),
            liste(tip(t) for t in e.type_args),
            liste(dugum("alan", kacir(ad), ifade(v)) for ad, v in e.fields),
        )

    if isinstance(e, A.Unary):
        return dugum("tekli", kacir(e.op), ifade(e.operand))
    if isinstance(e, A.Binary):
        return dugum("ikili", kacir(e.op), ifade(e.left), ifade(e.right))
    if isinstance(e, A.RangeExpr):
        return dugum("aralik", ifade(e.start), ifade(e.end),
                     "true" if e.inclusive else "false")

    if isinstance(e, A.Call):
        return dugum("cagri", ifade(e.callee), liste(ifade(a) for a in e.args),
                     liste(kacir(a) if a else "-"
                           for a in (getattr(e, "arg_names", None) or [])))
    if isinstance(e, A.Index):
        return dugum("dizin", ifade(e.obj), ifade(e.index))
    if isinstance(e, A.FieldAccess):
        return dugum("alanerisim", ifade(e.obj), kacir(e.name),
                     "true" if e.safe else "false")
    if isinstance(e, A.Propagate):
        return dugum("soru", ifade(e.operand))
    if isinstance(e, A.Unwrap):
        return dugum("ac", ifade(e.operand))

    if isinstance(e, A.Lambda):
        return dugum("lambda", liste(parametre(p) for p in e.params),
                     tip(e.ret_type), govde(e.body))

    if isinstance(e, A.IfExpr):
        return dugum("egerifade", ifade(e.cond), ifade(e.then), ifade(e.otherwise))
    if isinstance(e, A.BlockExpr):
        return dugum("blokifade", blok(e.block))

    if isinstance(e, A.MatchExpr):
        return dugum("matchifade", ifade(e.subject),
                     liste(kol(a) for a in e.arms))

    raise AssertionError(f"bilinmeyen ifade düğümü: {type(e).__name__}")


def govde(b) -> str:
    """Lambda/match gövdesi: blok, tek deyim ya da tek ifade.

    Deyim match kolundan gelir (`Kirmizi -> print("x")`); lambda gövdesi
    ise ya blok ya ifadedir.
    """
    if isinstance(b, A.Block):
        return blok(b)
    if isinstance(b, A.Stmt):
        return deyim(b)
    return ifade(b)


# ----------------------------------------------------------------- desenler
def desen(p) -> str:
    return konumla(_desen(p), getattr(p, "span", None))


def _desen(p) -> str:
    if isinstance(p, A.WildcardPat):
        return dugum("joker")
    if isinstance(p, A.BindPat):
        return dugum("baglama", kacir(p.name))
    if isinstance(p, A.LiteralPat):
        return dugum("deger", ifade(p.value))
    if isinstance(p, A.RangePat):
        return dugum("aralik", ifade(p.low), ifade(p.high),
                     "true" if p.inclusive else "false")
    if isinstance(p, A.EnumPat):
        enum_adi = kacir(p.enum_name) if p.enum_name is not None else "-"
        return dugum("varyant", enum_adi, kacir(p.variant),
                     liste(desen(s) for s in p.subpatterns))
    raise AssertionError(f"bilinmeyen desen: {type(p).__name__}")


def kol(a: A.MatchArm) -> str:
    return konumla(
        dugum("kol", desen(a.pattern), govde(a.body), ifade(a.guard)), a.span)


# ----------------------------------------------------------------- deyimler
def blok(b: A.Block) -> str:
    return konumla(dugum("blok", liste(deyim(s) for s in b.stmts)), b.span)


def deyim(s) -> str:
    return konumla(_deyim(s), getattr(s, "span", None))


def _deyim(s) -> str:
    if isinstance(s, A.LetStmt):
        return dugum("let", kacir(s.name), tip(s.type_expr), ifade(s.value),
                     "true" if s.mutable else "false")
    if isinstance(s, A.Assign):
        return dugum("atama", kacir(s.op), ifade(s.target), ifade(s.value))
    if isinstance(s, A.ExprStmt):
        return dugum("ifadedeyimi", ifade(s.expr))
    if isinstance(s, A.Return):
        return dugum("donus", ifade(s.value))
    if isinstance(s, A.If):
        if s.bag_ad:
            return dugum("egerbag", kacir(s.bag_ad), ifade(s.bag_ifade),
                         blok(s.then), yoksa(s.otherwise))
        return dugum("eger", ifade(s.cond), blok(s.then), yoksa(s.otherwise))
    if isinstance(s, A.While):
        return dugum("while", ifade(s.cond), blok(s.body),
                     kacir(s.bag_ad) if s.bag_ad else "-",
                     ifade(s.bag_ifade))
    if isinstance(s, A.For):
        return dugum("for", liste(kacir(n) for n in s.names),
                     ifade(s.iterable), blok(s.body))
    if isinstance(s, A.Match):
        return dugum("match", ifade(s.subject), liste(kol(a) for a in s.arms))
    if isinstance(s, A.Break):
        return dugum("break")
    if isinstance(s, A.Continue):
        return dugum("continue")
    raise AssertionError(f"bilinmeyen deyim: {type(s).__name__}")


def yoksa(o) -> str:
    if o is None:
        return "-"
    if isinstance(o, A.Block):
        return blok(o)
    return deyim(o)  # else if


# ---------------------------------------------------------- üst düzey öğeler
def tip_sinirlari(bounds: dict) -> str:
    """`{"T": ["Arayuz"]}` → sıralı liste; sözlük sırası iki tarafta aynı olmayabilir."""
    return liste(
        dugum("sinir", kacir(ad), liste(kacir(i) for i in sorted(bounds[ad])))
        for ad in sorted(bounds)
    )


def fn(d: A.FnDecl) -> str:
    return konumla(_fn(d), d.span)


def _fn(d: A.FnDecl) -> str:
    return dugum(
        "fn",
        kacir(d.name),
        liste(kacir(t) for t in d.type_params),
        tip_sinirlari(d.type_bounds),
        liste(parametre(p) for p in d.params),
        tip(d.ret_type),
        blok(d.body) if d.body is not None else "-",
    )


def oge(o) -> str:
    return konumla(_oge(o), getattr(o, "span", None))


def _oge(o) -> str:
    if isinstance(o, A.Import):
        return dugum("import", kacir(o.path))
    if isinstance(o, A.TypeAlias):
        return dugum("typealias", kacir(o.name), tip(o.target))
    if isinstance(o, A.FnDecl):
        # Konumu dıştaki `oge` ekler; burada ikinci kez sarmalanmamalı.
        return _fn(o)
    if isinstance(o, A.StructDecl):
        return dugum(
            "struct",
            kacir(o.name),
            liste(kacir(t) for t in o.type_params),
            liste(kacir(i) for i in o.interfaces),
            liste(konumla(dugum("alandecl", kacir(f.name), tip(f.type_expr),
                                "true" if f.mutable else "false",
                                ifade(f.default)), f.span)
                  for f in o.fields),
            liste(fn(m) for m in o.methods),
        )
    if isinstance(o, A.EnumDecl):
        return dugum(
            "enum",
            kacir(o.name),
            liste(kacir(t) for t in o.type_params),
            liste(kacir(i) for i in o.interfaces),
            liste(konumla(dugum("varyantdecl", kacir(v.name),
                                liste(tip(t) for t in v.payload)), v.span)
                  for v in o.variants),
            liste(fn(m) for m in o.methods),
        )
    if isinstance(o, A.InterfaceDecl):
        return dugum("interface", kacir(o.name), liste(fn(m) for m in o.methods))
    if isinstance(o, A.LetStmt):
        return _deyim(o)
    raise AssertionError(f"bilinmeyen üst düzey öğe: {type(o).__name__}")


def modul(m: A.Module) -> str:
    return dugum("modul", liste(oge(o) for o in m.items))


def yaz(m: A.Module) -> str:
    """Konumsuz S-ifadesi: ağacın *yapısını* karşılaştırır."""
    global _KONUM_YAZ
    _KONUM_YAZ = False
    return modul(m)


def yaz_konumlu(m: A.Module) -> str:
    """Konumlu S-ifadesi: satır/sütun hesabını da karşılaştırır."""
    global _KONUM_YAZ
    _KONUM_YAZ = True
    try:
        return modul(m)
    finally:
        _KONUM_YAZ = False
