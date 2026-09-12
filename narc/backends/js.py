"""JavaScript kod üreteci.

Denetlenmiş AST'yi okunabilir, `"use strict"` altında çalışan JavaScript'e
çevirir. Tip notları (`node.ty`, `node.resolved`) kod seçimlerini yönlendirir:
örneğin `Int` bölmesi `$idiv`, `Float` bölmesi düz `/` olur.
"""

from __future__ import annotations

from pathlib import Path

from .. import nar_ast as A
from .. import runtime_budama
from ..checker import Checker
from ..types import (
    ELEMENT, FLOAT, INT, ISTEK, KOMUT, OLAY, STRING, YANIT, EnumT, ListT, MapT, OptT,
    Prim, StructT, TupleT, Type, TypeVar, unwrap_optional,
)

RUNTIME_PATH = Path(__file__).resolve().parent.parent / "runtime" / "nar_runtime.js"

JS_RESERVED = {
    "abstract", "arguments", "await", "boolean", "break", "byte", "case",
    "catch", "char", "class", "const", "continue", "debugger", "default",
    "delete", "do", "double", "else", "enum", "eval", "export", "extends",
    "false", "final", "finally", "float", "for", "function", "goto", "if",
    "implements", "import", "in", "instanceof", "int", "interface", "let",
    "long", "native", "new", "null", "package", "private", "protected",
    "public", "return", "short", "static", "super", "switch", "synchronized",
    "this", "throw", "throws", "transient", "true", "try", "typeof", "var",
    "void", "volatile", "while", "with", "yield", "undefined", "NaN",
    "Infinity", "globalThis", "console", "process", "Math", "Map", "Array",
    "Object", "String", "Number", "Boolean", "JSON", "Symbol", "Promise",
}

# Metin metotları → JS karşılığı. `{0}` alıcı, `{1}`.. argümanlar.
STRING_METHODS = {
    "len": "$len({0})",
    "upper": "{0}.toUpperCase()",
    "lower": "{0}.toLowerCase()",
    "upperTr": "$upperTr({0})",
    "lowerTr": "$lowerTr({0})",
    "trim": "{0}.trim()",
    "split": "$strSplit({0}, {1})",
    "contains": "{0}.includes({1})",
    "replace": "{0}.split({1}).join({2})",
    "startsWith": "{0}.startsWith({1})",
    "endsWith": "{0}.endsWith({1})",
    "slice": "$strSlice({0}, {1}, {2})",
    "charAt": "$strGet({0}, {1})",
    "indexOf": "$strIndexOf({0}, {1})",
    "repeat": "$strRepeat({0}, {1})",
    "kodu": "$karakterKodu({0})",
}

LIST_METHODS = {
    "len": "$len({0})",
    "push": "{0}.push({1})",
    "pop": "$listPop({0})",
    "contains": "$listContains({0}, {1})",
    "indexOf": "$listIndexOf({0}, {1})",
    "slice": "$listSlice({0}, {1}, {2})",
    "reverse": "$listReverse({0})",
    "sort": "$listSort({0})",
    "first": "$listFirst({0})",
    "last": "$listLast({0})",
    "map": "{0}.map({1})",
    "filter": "{0}.filter({1})",
    "reduce": "$listReduce({0}, {1}, {2})",
    "join": "{0}.join({1})",
    # Lambda gerektirmeyen kolay işlemler
    "benzersiz": "$listBenzersiz({0})",
    "say": "$listSay({0}, {1})",
    "toplam": "$listToplam({0})",
    "carpim": "$listCarpim({0})",
    "ortalama": "$listOrtalama({0})",
    "enBuyuk": "$listEnBuyuk({0})",
    "enKucuk": "$listEnKucuk({0})",
    "kat": "$listKat({0}, {1})",
    "artir": "$listArtir({0}, {1})",
    "buyukler": "$listBuyukler({0}, {1})",
    "kucukler": "$listKucukler({0}, {1})",
    "ciftler": "$listCiftler({0})",
    "tekler": "$listTekler({0})",
    "buyukHarf": "$listBuyukHarf({0})",
    "kucukHarf": "$listKucukHarf({0})",
    "icerenler": "$listIcerenler({0}, {1})",
}

ELEMENT_METHODS = {
    "metin": "{0}.textContent",
    "metinYaz": "{0}.textContent = {1}",
    "html": "{0}.innerHTML",
    "htmlYaz": "{0}.innerHTML = {1}",
    "deger": "$ogeDeger({0})",
    "degerYaz": "{0}.value = {1}",
    "sinifEkle": "{0}.classList.add({1})",
    "sinifSil": "{0}.classList.remove({1})",
    "sinifVarMi": "{0}.classList.contains({1})",
    "ozellik": "$ogeOzellik({0}, {1})",
    "ozellikYaz": "{0}.setAttribute({1}, {2})",
    "stil": "$ogeStil({0}, {1}, {2})",
    "dinle": "{0}.addEventListener({1}, {2})",
    "ekle": "{0}.appendChild({1})",
    "cikar": "$ogeCikar({0})",
    "temizle": "$ogeTemizle({0})",
    "odaklan": "{0}.focus()",
    "bul": "$ogeBul({0}, {1})",
    "bulHepsi": "$ogeBulHepsi({0}, {1})",
    "secimBasi": "({0}.selectionStart || 0)",
    "secimSonu": "({0}.selectionEnd || 0)",
    "secimYap": "{0}.setSelectionRange({1}, {2})",
    "yaziEkle": "$ogeYaziEkle({0}, {1})",
    "kaydirmaUst": "({0}.scrollTop || 0)",
    "kaydirmaUstYaz": "{0}.scrollTop = {1}",
    "kaydirmaSol": "({0}.scrollLeft || 0)",
    # Onay kutusu: `checked` bir özellik (property), nitelik (attribute)
    # değil; setAttribute ile yazmak çalışmaz.
    "isaretli": "({0}.checked === true)",
    "isaretliYaz": "{0}.checked = {1}",
}

ISTEK_METHODS = {
    "yontem": "{0}.yontem",
    "yol": "{0}.yol",
    "sorgu": "$istekSorgu({0}, {1})",
    "baslik": "$istekBaslik({0}, {1})",
    "govde": "{0}.govde",
    "ip": "{0}.ip",
}

YANIT_METHODS = {
    "baslikYaz": "$yanitBaslik({0}, {1}, {2})",
    "durumYaz": "$yanitDurum({0}, {1})",
}

KOMUT_METHODS = {
    "cikis": "{0}.cikis",
    "cikti": "{0}.cikti",
    "hata": "{0}.hata",
}

OLAY_METHODS = {
    "tus": "({0}.key || \"\")",
    "ctrl": "(({0}.ctrlKey || {0}.metaKey) === true)",
    "shift": "({0}.shiftKey === true)",
    "alt": "({0}.altKey === true)",
    "engelle": "{0}.preventDefault()",
    "durdur": "{0}.stopPropagation()",
    "kaynak": "($olayKaynagi({0}))",
    "x": "(({0}.offsetX | 0))",
    "y": "(({0}.offsetY | 0))",
}

# Dosya, girdi ve zaman yerleşiklerinin çalışma zamanı karşılıkları.
SISTEM_ISLEVLERI = {
    "komutCalistir": "$komutCalistir",
    "dosyaOku": "$dosyaOku",
    "dosyaYaz": "$dosyaYaz",
    "dosyaEkle": "$dosyaEkle",
    "dosyaVarMi": "$dosyaVarMi",
    "dosyaSil": "$dosyaSil",
    "klasorListele": "$klasorListele",
    "klasorMu": "$klasorMu",
    "klasorOlustur": "$klasorOlustur",
    "satirOku": "$satirOku",
    "tumGirdi": "$tumGirdi",
    "argumanlar": "$argumanlar",
    "cik": "$cik",
    "simdi": "$simdi",
    "zamanMetni": "$zamanMetni",
    "koddan": "$koddanKarakter",
    "odaklanan": "$odaklanan",
    "medyaEslesir": "$medyaEslesir",
    "medyaDinle": "$medyaDinle",
    "sunucu": "$sunucu",
    "yanit": "$yanit",
    "icerikTipi": "$icerikTipi",
    "ortam": "$ortam",
    "rastgeleMetin": "$rastgeleMetin",
    "sha256": "$sha256",
}

# Kısayol yanıtlar: içerik tipi birlikte gelir.
YANIT_KISAYOLLARI = {
    "yanitMetin": '$yanit(200, {0}, "text/plain; charset=utf-8")',
    "yanitHtml": '$yanit(200, {0}, "text/html; charset=utf-8")',
    "yanitJson": '$yanit(200, {0}, "application/json; charset=utf-8")',
    "yanitDosya": "$yanitDosya({0})",
    "yonlendir": '$yanitBaslik($yanit(302, "", "text/plain; charset=utf-8"), '
                 '"Location", {0})',
}

MAP_METHODS = {
    "len": "$len({0})",
    "get": "$mapGet({0}, {1})",
    "set": "{0}.set({1}, {2})",
    "has": "{0}.has({1})",
    "remove": "$mapRemove({0}, {1})",
    "keys": "$mapKeys({0})",
    "values": "$mapValues({0})",
}


def js_string(text: str) -> str:
    """Metni JSON kaçışlarıyla JS literaline çevirir (Unicode korunur)."""
    out = ['"']
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        elif ch in (" ", " "):
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def type_code(ty: Type | None) -> str:
    """Tipin çalışma zamanı biçimleyicisine geçirilecek JS gösterimi."""
    if ty is None:
        return "undefined"
    if isinstance(ty, Prim):
        return js_string(ty.name)
    if isinstance(ty, OptT):
        return f'["o", {type_code(ty.inner)}]'
    if isinstance(ty, ListT):
        return f'["l", {type_code(ty.elem)}]'
    if isinstance(ty, MapT):
        return f'["m", {type_code(ty.key)}, {type_code(ty.value)}]'
    if isinstance(ty, (StructT, EnumT)):
        if ty.type_args:
            # Uygulanmış generic: tip argümanları da taşınır ki çalışma
            # zamanı alan tiplerini (örneğin Float'ı) bilebilsin.
            argler = ", ".join(type_code(a) for a in ty.type_args)
            return f'["u", {js_string(ty.name)}, [{argler}]]'
        return js_string(ty.name)
    if isinstance(ty, TypeVar):
        return js_string(ty.name)
    return "undefined"


class JsBackend:
    def __init__(self, module: A.Module, checker: Checker,
                 kutuphane: bool = False) -> None:
        self.module = module
        self.checker = checker
        # Kütüphane modunda `main` çağrılmaz; fonksiyonlar dışa açılır.
        self.kutuphane = kutuphane
        self.lines: list[str] = []
        self.indent = 0
        self.tmp = 0
        # `?` gibi ifade içinde durup deyim üreten şeylerin bıraktığı
        # satırlar; bir sonraki `write` onları kendinden önce boşaltır.
        self.bekleyen: list[str] = []
        # Koşullu match kolunda desenin bağladığı adların karşılıkları.
        self.desen_baglari: dict | None = None

    # ------------------------------------------------------------ yardımcılar
    def write(self, text: str = "") -> None:
        # Bekleyenler önce yazılır: `write(f"... {self.expr(x)} ...")`
        # çağrısında `expr` bu satırdan önce koşmuştur.
        if self.bekleyen:
            bekleyen, self.bekleyen = self.bekleyen, []
            for satir in bekleyen:
                self.lines.append("  " * self.indent + satir)
        self.lines.append(("  " * self.indent + text) if text else "")

    def yukselt(self, satir: str) -> None:
        """Bir deyimi, içinde bulunduğumuz deyimin önüne koyar."""
        self.bekleyen.append(satir)

    def name(self, ident: str) -> str:
        return f"{ident}_" if ident in JS_RESERVED else ident

    def fresh(self, prefix: str = "t") -> str:
        self.tmp += 1
        return f"${prefix}{self.tmp}"

    # ------------------------------------------------------------------ giriş
    def emit(self) -> str:
        """Önce gövdeyi üretir, sonra çalışma zamanının gereken kısmını.

        Sıra önemli: hangi yardımcının gerektiği ancak üretilmiş koda
        bakılarak bilinir. Tamamını gömmek `print("Merhaba")` için
        26 KB demekti ve neredeyse hepsi hiç çalışmayan koddu.
        """
        govde = self.govde_uret()
        calisma = runtime_budama.buda(
            RUNTIME_PATH.read_text(encoding="utf-8"), govde)
        return calisma + "\n\n" + govde

    def govde_uret(self) -> str:
        self.write("// " + "-" * 66)
        self.write("// Nar kaynağından üretildi — elle düzenlemeyin.")
        self.write("// " + "-" * 66)
        self.write()

        for item in self.module.items:
            if isinstance(item, A.StructDecl):
                self.emit_struct(item)
            elif isinstance(item, A.EnumDecl):
                self.emit_enum(item)

        for item in self.module.items:
            if isinstance(item, A.FnDecl):
                self.emit_fn(item)

        globals_ = [i for i in self.module.items if isinstance(i, A.LetStmt)]
        if globals_:
            for item in globals_:
                self.emit_let(item)
            self.write()

        if self.kutuphane:
            self.emit_disa_ac()
        else:
            self.write("$bootstrap(main);")
        return "\n".join(self.lines) + "\n"

    def emit_disa_ac(self) -> None:
        """Kütüphane modunda üst düzey adları `globalThis.Nar` altına koyar."""
        adlar: list[str] = []
        for item in self.module.items:
            if isinstance(item, A.FnDecl):
                adlar.append(item.name)
            elif isinstance(item, (A.StructDecl, A.EnumDecl)):
                adlar.append(item.name)

        self.write("// Dışa açılan adlar — tarayıcıda `Nar.<ad>` ile çağrılır.")
        self.write("globalThis.Nar = Object.assign(globalThis.Nar || {}, {")
        self.indent += 1
        for ad in adlar:
            js_ad = self.name(ad)
            self.write(f"{js_ad}: {js_ad},")
        self.indent -= 1
        self.write("});")
        self.write("if (typeof module !== \"undefined\" && module.exports) {")
        self.indent += 1
        self.write("module.exports = globalThis.Nar;")
        self.indent -= 1
        self.write("}")

    # ------------------------------------------------------------ bildirimler
    def emit_struct(self, decl: A.StructDecl) -> None:
        cls = self.name(decl.name)
        field_names = [self.name(f.name) for f in decl.fields]
        self.write(f"class {cls} {{")
        self.indent += 1
        self.write(f"constructor({', '.join(field_names)}) {{")
        self.indent += 1
        for f in field_names:
            self.write(f"this.{f} = {f};")
        if not field_names:
            self.write("// alansız struct")
        self.indent -= 1
        self.write("}")
        for m in decl.methods:
            self.write()
            self.emit_method(m)
        self.indent -= 1
        self.write("}")
        self.write(f"{cls}.$narName = {js_string(decl.name)};")
        pairs = ", ".join(
            f"{js_string(f.name)}: {type_code(f.ty)}" for f in decl.fields
        )
        params = ", ".join(js_string(p) for p in decl.type_params)
        self.write(f"$defType({js_string(decl.name)}, "
                   f"{{ params: [{params}], fields: {{{pairs}}} }});")
        self.write()

    def emit_enum(self, decl: A.EnumDecl) -> None:
        cls = self.name(decl.name)
        self.write(f"class {cls} {{")
        self.indent += 1
        self.write("constructor(tag, values) {")
        self.indent += 1
        self.write("this.$tag = tag;")
        self.write("this.$values = values;")
        self.indent -= 1
        self.write("}")

        for v in decl.variants:
            self.write()
            if v.payload:
                args = ", ".join(f"v{i}" for i in range(len(v.payload)))
                self.write(f"static {self.name(v.name)}({args}) {{")
                self.indent += 1
                self.write(f"return new {cls}({js_string(v.name)}, [{args}]);")
                self.indent -= 1
                self.write("}")
            else:
                self.write(f"static get {self.name(v.name)}() {{")
                self.indent += 1
                self.write(f"return new {cls}({js_string(v.name)}, []);")
                self.indent -= 1
                self.write("}")

        for m in decl.methods:
            self.write()
            self.emit_method(m)
        self.indent -= 1
        self.write("}")
        self.write(f"{cls}.$narName = {js_string(decl.name)};")
        pairs = ", ".join(
            f"{js_string(v.name)}: [{', '.join(type_code(t) for t in v.tys)}]"
            for v in decl.variants
        )
        params = ", ".join(js_string(p) for p in decl.type_params)
        self.write(f"$defType({js_string(decl.name)}, "
                   f"{{ params: [{params}], variants: {{{pairs}}} }});")
        self.write()

    def emit_method(self, decl: A.FnDecl) -> None:
        params = self.param_listesi(decl.params)
        self.write(f"{self.name(decl.name)}({params}) {{")
        self.indent += 1
        self.emit_body(decl.body)
        self.indent -= 1
        self.write("}")

    def param_listesi(self, params) -> str:
        # Varsayılanlar çağrı yerinde dolduruluyor; imzada yer almazlar.
        return ", ".join(self.name(p.name) for p in params)

    def emit_fn(self, decl: A.FnDecl) -> None:
        params = self.param_listesi(decl.params)
        self.write(f"function {self.name(decl.name)}({params}) {{")
        self.indent += 1
        self.emit_body(decl.body)
        self.indent -= 1
        self.write("}")
        self.write()

    def emit_body(self, block: A.Block) -> None:
        for stmt in block.stmts:
            self.emit_stmt(stmt)

    # ---------------------------------------------------------------- deyimler
    def emit_block(self, block: A.Block) -> None:
        self.write("{")
        self.indent += 1
        self.emit_body(block)
        self.indent -= 1
        self.write("}")

    def emit_stmt(self, stmt: A.Stmt) -> None:
        if isinstance(stmt, A.LetStmt) and stmt.names:
            # `let (a, b) = ifade` — JavaScript'in dizi açması birebir uyar.
            adlar = ", ".join(self.name(a) for a in stmt.names)
            anahtar = "let" if stmt.mutable else "const"
            self.write(f"{anahtar} [{adlar}] = {self.expr(stmt.value)};")
            return

        if isinstance(stmt, A.LetStmt):
            self.emit_let(stmt)

        elif isinstance(stmt, A.ExprStmt):
            self.write(self.expr(stmt.expr) + ";")

        elif isinstance(stmt, A.Assign):
            self.emit_assign(stmt)

        elif isinstance(stmt, A.Return):
            if stmt.value is None:
                self.write("return;")
            else:
                self.write(f"return {self.expr(stmt.value)};")

        elif isinstance(stmt, A.If):
            self.emit_if(stmt)

        elif isinstance(stmt, A.While):
            if stmt.bag_ad:
                # `while let`: değer her turda yeniden hesaplanır, `null`
                # gelince döngü biter. Atama döngü koşulunun içinde durur
                # ki ad gövdeye taze gelsin.
                ad = self.name(stmt.bag_ad)
                self.write(f"for (let {ad}; ({ad} = "
                           f"{self.expr(stmt.bag_ifade)}) !== null;) {{")
            else:
                self.write(f"while ({self.expr(stmt.cond)}) {{")
            self.indent += 1
            self.emit_body(stmt.body)
            self.indent -= 1
            self.write("}")

        elif isinstance(stmt, A.For):
            self.emit_for(stmt)

        elif isinstance(stmt, A.Match):
            self.emit_match(stmt)

        elif isinstance(stmt, A.Break):
            self.write("break;")

        elif isinstance(stmt, A.Continue):
            self.write("continue;")

        else:  # pragma: no cover
            raise AssertionError(f"üretilemeyen deyim: {type(stmt).__name__}")

    def emit_let(self, stmt: A.LetStmt) -> None:
        keyword = "let" if stmt.mutable else "const"
        target = self.name(stmt.name)
        if stmt.value is None:
            self.write(f"let {target};")
        else:
            self.write(f"{keyword} {target} = {self.expr(stmt.value)};")

    def emit_assign(self, stmt: A.Assign) -> None:
        value = self.expr(stmt.value)
        op = stmt.op

        # Liste ve eşleme dizinine atama sınır/kap kontrolünden geçer.
        if isinstance(stmt.target, A.Index):
            obj_ty = stmt.target.obj.ty
            obj = self.expr(stmt.target.obj)
            idx = self.expr(stmt.target.index)
            if op != "=":
                current = self.index_read(obj_ty, obj, idx)
                value = self.binary_js(op[0], stmt.target.ty, current, value)
            if isinstance(obj_ty, MapT):
                self.write(f"{obj}.set({idx}, {value});")
            else:
                self.write(f"$listSet({obj}, {idx}, {value});")
            return

        target = self.expr(stmt.target)
        if op == "=":
            self.write(f"{target} = {value};")
            return
        if op == "+=" and unwrap_optional(stmt.target.ty) == STRING:
            self.write(f"{target} = {target} + {self.to_string(stmt.value)};")
            return
        self.write(f"{target} = {self.binary_js(op[0], stmt.target.ty, target, value)};")

    def emit_if(self, stmt: A.If) -> None:
        if stmt.bag_ad:
            self.emit_if_bagli(stmt)
            return
        self.write(f"if ({self.expr(stmt.cond)}) {{")
        self.indent += 1
        self.emit_body(stmt.then)
        self.indent -= 1
        if stmt.otherwise is None:
            self.write("}")
        elif isinstance(stmt.otherwise, A.If):
            self.write("} else {")
            self.indent += 1
            self.emit_if(stmt.otherwise)
            self.indent -= 1
            self.write("}")
        else:
            self.write("} else {")
            self.indent += 1
            self.emit_body(stmt.otherwise)
            self.indent -= 1
            self.write("}")

    def emit_for(self, stmt: A.For) -> None:
        if stmt.kind == "range":
            rng = stmt.iterable
            assert isinstance(rng, A.RangeExpr)
            var = self.name(stmt.names[0])
            end_var = self.fresh("son")
            self.write(f"const {end_var} = {self.expr(rng.end)};")
            cmp = "<=" if rng.inclusive else "<"
            self.write(f"for (let {var} = {self.expr(rng.start)}; {var} {cmp} {end_var}; {var}++) {{")
        elif stmt.kind == "map":
            k, v = (self.name(n) for n in stmt.names)
            self.write(f"for (const [{k}, {v}] of {self.expr(stmt.iterable)}) {{")
        elif stmt.kind == "list_indeksli":
            i, var = (self.name(n) for n in stmt.names)
            self.write(
                f"for (const [{i}, {var}] of "
                f"{self.expr(stmt.iterable)}.entries()) {{")
        elif stmt.kind == "string_indeksli":
            # Metin karakter karakter dönülür; `entries()` UTF-16 kod
            # birimlerine bakar, oysa Nar'ın döngüsü karakterlere bakar.
            i, var = (self.name(n) for n in stmt.names)
            sayac = self.fresh("i")
            self.write(f"let {sayac} = 0;")
            self.write(f"for (const {var} of {self.expr(stmt.iterable)}) {{")
            self.indent += 1
            self.write(f"const {i} = {sayac}++;")
            self.indent -= 1
        elif stmt.kind == "string":
            var = self.name(stmt.names[0])
            self.write(f"for (const {var} of {self.expr(stmt.iterable)}) {{")
        else:
            var = self.name(stmt.names[0])
            self.write(f"for (const {var} of {self.expr(stmt.iterable)}) {{")

        self.indent += 1
        self.emit_body(stmt.body)
        self.indent -= 1
        self.write("}")

    def emit_if_bagli(self, stmt: A.If) -> None:
        """`if let`: değeri bir kez hesaplar, adı bloğa kapatır.

        Dış bir blok açılır ki ad `if`in dışına sızmasın.
        """
        ad = self.name(stmt.bag_ad)
        self.write("{")
        self.indent += 1
        self.write(f"const {ad} = {self.expr(stmt.bag_ifade)};")
        self.write(f"if ({ad} !== null) {{")
        self.indent += 1
        self.emit_body(stmt.then)
        self.indent -= 1
        if stmt.otherwise is None:
            self.write("}")
        else:
            self.write("} else {")
            self.indent += 1
            if isinstance(stmt.otherwise, A.If):
                self.emit_if(stmt.otherwise)
            else:
                self.emit_body(stmt.otherwise)
            self.indent -= 1
            self.write("}")
        self.indent -= 1
        self.write("}")

    def emit_match(self, stmt: A.Match) -> None:
        subject_var = self.fresh("m")
        self.write("{")
        self.indent += 1
        self.write(f"const {subject_var} = {self.expr(stmt.subject)};")

        first = True
        closed = False
        for arm in stmt.arms:
            test, bindings = self.pattern_test(arm.pattern, subject_var, stmt.subject.ty)
            test = self.guardli_test(arm, test, bindings, subject_var)
            if test is None:  # her şeyi kapsayan dal
                if first:
                    self.write("{")
                else:
                    self.write("} else {")
                self.indent += 1
                for line in bindings:
                    self.write(line)
                self.emit_arm_body(arm)
                self.indent -= 1
                self.write("}")
                closed = True
                break

            keyword = "if" if first else "} else if"
            self.write(f"{keyword} ({test}) {{")
            self.indent += 1
            for line in bindings:
                self.write(line)
            self.emit_arm_body(arm)
            self.indent -= 1
            first = False

        if not closed:
            self.write("} else {")
            self.indent += 1
            self.write('$panic("eşleşen match dalı yok: " + $str(' + subject_var + "));")
            self.indent -= 1
            self.write("}")

        self.indent -= 1
        self.write("}")

    def emit_arm_body(self, arm: A.MatchArm) -> None:
        if isinstance(arm.body, A.Block):
            self.emit_body(arm.body)
        elif isinstance(arm.body, A.Stmt):
            self.emit_stmt(arm.body)
        else:  # pragma: no cover
            self.write(self.expr(arm.body) + ";")

    def guardli_test(self, arm, test, bindings, subject: str) -> str | None:
        """Kolun testi ile koşulunu birleştirir.

        Koşul, desenin bağladığı adları kullanabilir; bunlar henüz
        değişkene atanmadığı için üretim sırasında doğrudan değerleriyle
        karşılanır (`self.desen_baglari`).
        """
        if arm.guard is None:
            return test
        eslesme = {}
        for satir in bindings:
            # "const x = ifade;" biçimindeki bağları ada göre ayır.
            if satir.startswith("const ") and " = " in satir:
                ad, _, deger = satir[len("const "):].partition(" = ")
                eslesme[ad.strip()] = deger.rstrip(";").strip()
        onceki = self.desen_baglari
        self.desen_baglari = {**(onceki or {}), **eslesme}
        try:
            kosul = self.expr(arm.guard)
        finally:
            self.desen_baglari = onceki
        return kosul if test is None else f"{test} && ({kosul})"

    def pattern_test(self, pat: A.Pattern, subject: str, subject_ty: Type | None):
        """(koşul, bağlama satırları) döndürür. Koşul None ise dal her zaman eşleşir."""
        if isinstance(pat, A.WildcardPat):
            return None, []

        if isinstance(pat, A.BindPat):
            enum_name = pat.__dict__.get("as_enum")
            if enum_name is not None:  # yüksüz varyant adı
                return f"{subject}.$tag === {js_string(pat.name)}", []
            return None, [f"const {self.name(pat.name)} = {subject};"]

        if isinstance(pat, A.LiteralPat):
            if isinstance(pat.value, A.NoneLit):
                return f"{subject} === null", []
            return f"$eq({subject}, {self.expr(pat.value)})", []

        if isinstance(pat, A.RangePat):
            ust = "<=" if pat.inclusive else "<"
            return (f"({subject} >= {self.expr(pat.low)} && "
                    f"{subject} {ust} {self.expr(pat.high)})"), []

        if isinstance(pat, A.EnumPat):
            tests = [f"{subject}.$tag === {js_string(pat.variant)}"]
            bindings: list[str] = []
            for i, sub in enumerate(pat.subpatterns):
                slot = f"{subject}.$values[{i}]"
                if isinstance(sub, A.WildcardPat):
                    continue
                if isinstance(sub, A.BindPat) and sub.__dict__.get("as_enum") is None:
                    bindings.append(f"const {self.name(sub.name)} = {slot};")
                    continue
                sub_test, sub_bind = self.pattern_test(sub, slot, None)
                if sub_test is not None:
                    tests.append(sub_test)
                bindings.extend(sub_bind)
            return " && ".join(tests), bindings

        raise AssertionError(f"üretilemeyen desen: {type(pat).__name__}")  # pragma: no cover

    # ---------------------------------------------------------------- ifadeler
    def expr(self, node: A.Expr) -> str:
        if isinstance(node, A.IntLit):
            return str(node.value)

        if isinstance(node, A.FloatLit):
            text = repr(node.value)
            return text if ("." in text or "e" in text or "n" in text) else text + ".0"

        if isinstance(node, A.BoolLit):
            return "true" if node.value else "false"

        if isinstance(node, A.NoneLit):
            return "null"

        if isinstance(node, A.StringLit):
            return self.string_lit(node)

        if isinstance(node, A.BlockExpr):
            return self.block_expr(node)

        if isinstance(node, A.SelfExpr):
            return "this"

        if isinstance(node, A.Ident):
            # Enum adı yazılmadan kullanılan yüksüz varyant: `Cizgi`
            if node.__dict__.get("resolved") == "enum_variant":
                enum_name = self.name(node.__dict__["enum_name"])
                return f"{enum_name}.{self.name(node.name)}"
            # Koşullu match kolunda (`desen if koşul ->`) desenin bağladığı
            # adlar henüz değişkene yazılmamıştır: koşul, testin içinde
            # değerlendirilir. Bu yüzden ad, değerin kendisiyle karşılanır.
            if self.desen_baglari and node.name in self.desen_baglari:
                return self.desen_baglari[node.name]
            return self.name(node.name)

        if isinstance(node, A.TupleLit):
            # Tuple bir dizidir: `.0` erişimi `[0]` olur, ek bir çalışma
            # zamanı yapısı gerekmez.
            return "[" + ", ".join(self.expr(i) for i in node.items) + "]"

        if isinstance(node, A.ListLit):
            return "[" + ", ".join(self.expr(i) for i in node.items) + "]"

        if isinstance(node, A.MapLit):
            pairs = ", ".join(f"[{self.expr(k)}, {self.expr(v)}]" for k, v in node.entries)
            return f"new Map([{pairs}])"

        if isinstance(node, A.StructLit):
            return self.struct_lit(node)

        if isinstance(node, A.Unary):
            inner = self.expr(node.operand)
            return f"(!{inner})" if node.op == "!" else f"(-{inner})"

        if isinstance(node, A.Binary):
            return self.binary(node)

        if isinstance(node, A.Propagate):
            # Değer bir kez hesaplanır: `f()?` çağrıyı iki kez yapmamalı.
            t = self.fresh("s")
            self.yukselt(f"const {t} = {self.expr(node.operand)};")
            self.yukselt(f"if ({t} === null) return null;")
            return t

        if isinstance(node, A.Unwrap):
            # Değer zaten opsiyonel değilse açma işlemi gereksizdir; kontrolü
            # üretmeyip doğrudan değeri kullanırız.
            if node.__dict__.get("gereksiz"):
                return self.expr(node.operand)
            where = f"{node.span.line}:{node.span.col}"
            return f"$unwrap({self.expr(node.operand)}, {js_string(where)})"

        if isinstance(node, A.Index):
            return self.index_read(node.obj.ty, self.expr(node.obj), self.expr(node.index))

        if isinstance(node, A.FieldAccess):
            return self.field(node)

        if isinstance(node, A.Call):
            return self.call(node)

        if isinstance(node, A.Lambda):
            return self.lambda_(node)

        if isinstance(node, A.IfExpr):
            return (f"({self.expr(node.cond)} ? {self.expr(node.then)}"
                    f" : {self.expr(node.otherwise)})")

        if isinstance(node, A.MatchExpr):
            return self.match_expr(node)

        if isinstance(node, A.RangeExpr):  # pragma: no cover - checker engelliyor
            raise AssertionError("aralık yalnızca 'for' içinde kullanılabilir")

        raise AssertionError(f"üretilemeyen ifade: {type(node).__name__}")  # pragma: no cover

    def string_lit(self, node: A.StringLit) -> str:
        if len(node.parts) == 1 and isinstance(node.parts[0], str):
            return js_string(node.parts[0])

        chunks: list[str] = ["`"]
        for part in node.parts:
            if isinstance(part, str):
                chunks.append(
                    part.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                )
            else:
                chunks.append("${" + self.to_string(part) + "}")
        chunks.append("`")
        return "".join(chunks)

    def to_string(self, node: A.Expr, code: str | None = None) -> str:
        """Bir ifadeyi metne çevirirken tipe uygun biçimleyiciyi seçer.

        `code` verilirse ifade yeniden üretilmez. Bunu atlamak pahalıya
        mal oluyordu: `a + b + c + ...` gibi bir zincirde her düğüm alt
        ağacını ikinci kez üretiyor, maliyet zincir uzunluğunda üstel
        büyüyordu (40 parçalı bir metin dakikalarca derleniyordu).
        """
        if code is None:
            code = self.expr(node)
        ty = node.ty
        if ty == STRING:
            return code
        if ty is not None and unwrap_optional(ty) == FLOAT:
            return f"$strFloat({code})"
        tc = type_code(ty)
        if tc == "undefined":
            return f"$str({code})"
        return f"$fmt({code}, {tc}, false)"

    def struct_lit(self, node: A.StructLit) -> str:
        st = self.checker.structs.get(node.type_name)
        given = dict(node.fields)
        if st is None:  # pragma: no cover - checker hata verdi
            args = ", ".join(self.expr(v) for _, v in node.fields)
        else:
            args = ", ".join(
                self.expr(given[f]) if f in given else "null" for f in st.fields
            )
        return f"new {self.name(node.type_name)}({args})"

    def binary(self, node: A.Binary) -> str:
        left = self.expr(node.left)
        right = self.expr(node.right)

        if node.op == "??":
            return f"({left} ?? {right})"
        if node.op in ("&&", "||"):
            return f"({left} {node.op} {right})"
        if node.op in ("==", "!="):
            operand_ty = node.left.ty
            if self.needs_deep_eq(operand_ty) or self.needs_deep_eq(node.right.ty):
                call = f"$eq({left}, {right})"
                return f"(!{call})" if node.op == "!=" else call
            return f"({left} {'===' if node.op == '==' else '!=='} {right})"

        # Metin birleştirmede sayı/liste/struct tarafı otomatik yazıya dökülür.
        # Üretilmiş kod yeniden kullanılır; `expr` ikinci kez çağrılmaz.
        if node.op == "+" and node.ty == STRING:
            return (f"({self.to_string(node.left, left)} + "
                    f"{self.to_string(node.right, right)})")

        return self.binary_js(node.op, node.ty, left, right)

    def binary_js(self, op: str, result_ty: Type | None, left: str, right: str) -> str:
        # Sonuç tipine bakılır: `Int / Int` tam bölmedir, karışık işlemin
        # sonucu Float olduğu için orada düz bölme kullanılır.
        base = unwrap_optional(result_ty) if result_ty is not None else None
        if op == "/":
            return f"$idiv({left}, {right})" if base == INT else f"({left} / {right})"
        if op == "%":
            return f"$imod({left}, {right})" if base == INT else f"({left} % {right})"
        if op == "+" and isinstance(base, ListT):
            # JavaScript'te dizi toplaması metne çevirir; birleştirme gerekir.
            return f"$listConcat({left}, {right})"
        return f"({left} {op} {right})"

    @staticmethod
    def needs_deep_eq(ty: Type | None) -> bool:
        base = unwrap_optional(ty) if ty is not None else None
        return isinstance(base, (StructT, EnumT, ListT, MapT, TupleT))

    def index_read(self, obj_ty: Type | None, obj: str, idx: str) -> str:
        base = unwrap_optional(obj_ty) if obj_ty is not None else None
        if isinstance(base, MapT):
            return f"$mapGet({obj}, {idx})"
        if base == STRING:
            return f"$strGet({obj}, {idx})"
        return f"$listGet({obj}, {idx})"

    def block_expr(self, node) -> str:
        """Değer üreten blok, hemen çağrılan bir ok işleviyle üretilir.

        Satırlar ana akıştan ayrı toplanır: ifade üretilirken doğrudan
        `self.lines`'a yazmak, ifadenin içinde bulunduğu satırı bozardı.
        """
        yedek_lines, yedek_indent = self.lines, self.indent
        self.lines, self.indent = [], yedek_indent + 1
        try:
            stmts = node.block.stmts
            for s in stmts[:-1]:
                self.emit_stmt(s)
            son = stmts[-1]
            if isinstance(son, A.ExprStmt):
                self.write(f"return {self.expr(son.expr)};")
            else:
                self.emit_stmt(son)
            ic = "\n".join(self.lines)
        finally:
            self.lines, self.indent = yedek_lines, yedek_indent
        return "(() => {\n" + ic + "\n" + "  " * self.indent + "})()"

    def field(self, node: A.FieldAccess) -> str:
        resolved = node.__dict__.get("resolved")

        if resolved == "enum_variant":
            enum_name = self.name(node.__dict__["enum_name"])
            return f"{enum_name}.{self.name(node.name)}"

        obj = self.expr(node.obj)
        if resolved == "tuple":
            # Tuple bir dizi olarak saklanıyor; `t.0` -> `t[0]`.
            return f"{obj}?.[{node.name}]" if node.safe else f"{obj}[{node.name}]"
        if node.safe:
            return f"{obj}?.{self.name(node.name)}"
        return f"{obj}.{self.name(node.name)}"

    def match_expr(self, node: A.MatchExpr) -> str:
        """Değer üreten match, desen bağlamalarını taşıyabilmek için hemen
        çağrılan bir ok fonksiyonuna derlenir."""
        subject = self.fresh("m")
        pad = "  " * (self.indent + 1)
        satirlar: list[str] = []
        kapandi = False

        for arm in node.arms:
            test, bindings = self.pattern_test(arm.pattern, subject, node.subject.ty)
            test = self.guardli_test(arm, test, bindings, subject)
            govde = "".join(f"{b} " for b in bindings)
            if test is None:
                satirlar.append(f"{pad}  {govde}return {self.expr(arm.body)};")
                kapandi = True
                break
            satirlar.append(
                f"{pad}  if ({test}) {{ {govde}return {self.expr(arm.body)}; }}"
            )

        if not kapandi:
            satirlar.append(
                f'{pad}  $panic("eşleşen match dalı yok: " + $str({subject}));'
            )

        govde_metni = "\n".join(satirlar)
        return (f"(({subject}) => {{\n{govde_metni}\n{pad}}})"
                f"({self.expr(node.subject)})")

    def lambda_(self, node: A.Lambda) -> str:
        params = self.param_listesi(node.params)
        if isinstance(node.body, A.Block):
            saved, self.lines = self.lines, []
            saved_indent, self.indent = self.indent, 1
            saved_bekleyen, self.bekleyen = self.bekleyen, []
            self.emit_body(node.body)
            body_lines = self.lines
            self.lines, self.indent = saved, saved_indent
            self.bekleyen = saved_bekleyen
            pad = "  " * self.indent
            inner = "\n".join(pad + line for line in body_lines)
            return f"(({params}) => {{\n{inner}\n{pad}}})"
        return f"(({params}) => {self.expr(node.body)})"

    # ----------------------------------------------------------------- çağrılar
    def arg_listesi(self, node: A.Call) -> str:
        # Denetleyici adlandırılmış argümanları sıraya dizip eksikleri
        # varsayılanlarıyla doldurdu; burada yapacak bir şey kalmıyor.
        return ", ".join(self.expr(a) for a in node.args)

    def call(self, node: A.Call) -> str:
        resolved = node.__dict__.get("resolved")

        if resolved == "builtin":
            return self.builtin_call(node)

        callee = node.callee
        if isinstance(callee, A.Ident) and resolved == "enum_variant":
            # Enum adı yazılmadan çağrılan varyant: `Metin("a")`
            enum_name = self.name(node.__dict__["enum_name"])
            args = self.arg_listesi(node)
            return f"{enum_name}.{self.name(callee.name)}({args})"

        if isinstance(callee, A.FieldAccess):
            inner = callee.__dict__.get("resolved")

            if inner == "enum_variant":
                enum_name = self.name(callee.__dict__["enum_name"])
                args = self.arg_listesi(node)
                return f"{enum_name}.{self.name(callee.name)}({args})"

            if inner == "builtin_method":
                return self.builtin_method_call(node, callee)

            obj = self.expr(callee.obj)
            args = self.arg_listesi(node)
            sep = "?." if callee.safe else "."
            return f"{obj}{sep}{self.name(callee.name)}({args})"

        args = self.arg_listesi(node)
        return f"{self.expr(callee)}({args})"

    def builtin_method_call(self, node: A.Call, callee: A.FieldAccess) -> str:
        base = unwrap_optional(callee.obj.ty) if callee.obj.ty is not None else None
        if base == STRING:
            table = STRING_METHODS
        elif base == ELEMENT:
            table = ELEMENT_METHODS
        elif base == ISTEK:
            table = ISTEK_METHODS
        elif base == YANIT:
            table = YANIT_METHODS
        elif base == KOMUT:
            table = KOMUT_METHODS
        elif base == OLAY:
            table = OLAY_METHODS
        elif isinstance(base, MapT):
            table = MAP_METHODS
        else:
            table = LIST_METHODS

        template = table.get(callee.name)
        if template is None:  # pragma: no cover - checker engelliyor
            raise AssertionError(f"bilinmeyen yerleşik metot: {callee.name}")

        obj = self.expr(callee.obj)
        args = [self.expr(a) for a in node.args]

        if callee.safe:
            tmp = self.fresh("o")
            inner = template.format(tmp, *args)
            return f"$opt({obj}, ({tmp}) => {inner})"

        # Alıcı karmaşık bir ifadeyse şablonda birden çok kez geçmediği için
        # doğrudan yerleştirmek güvenlidir (tüm şablonlar {0}'ı bir kez kullanır).
        return template.format(obj, *args)

    def builtin_call(self, node: A.Call) -> str:
        name = node.callee.name  # type: ignore[union-attr]
        args = node.args

        if name == "print":
            return "console.log(" + ", ".join(self.to_string(a) for a in args) + ")"

        if name == "str":
            return self.to_string(args[0])

        if name == "len":
            return f"$len({self.expr(args[0])})"

        if name in ("int", "float"):
            conv = node.__dict__.get("conv")
            code = self.expr(args[0])
            if conv == "parse":
                return f"$parseIntOpt({code})" if name == "int" else f"$parseFloatOpt({code})"
            return f"$toInt({code})" if name == "int" else f"$toFloat({code})"

        if name == "abs":
            return f"Math.abs({self.expr(args[0])})"
        if name == "min":
            return f"Math.min({self.expr(args[0])}, {self.expr(args[1])})"
        if name == "max":
            return f"Math.max({self.expr(args[0])}, {self.expr(args[1])})"
        if name == "sqrt":
            return f"Math.sqrt({self.expr(args[0])})"
        if name == "pow":
            return f"Math.pow({self.expr(args[0])}, {self.expr(args[1])})"
        if name == "floor":
            return f"Math.floor({self.expr(args[0])})"
        if name == "ceil":
            return f"Math.ceil({self.expr(args[0])})"
        if name == "round":
            return f"Math.round({self.expr(args[0])})"
        if name == "random":
            return "Math.random()"

        # --- sayfa (DOM) işlemleri ---
        if name == "bul":
            return f"$bul({self.expr(args[0])})"
        if name == "bulHepsi":
            return f"$bulHepsi({self.expr(args[0])})"
        if name == "olustur":
            return f"$olustur({self.expr(args[0])})"
        if name == "govde":
            return "$govde()"
        if name == "zamanla":
            return f"$zamanla({self.expr(args[0])}, {self.expr(args[1])})"
        if name == "istek":
            arglar = ", ".join(self.expr(a) for a in args)
            return f"$istek({arglar})"

        # --- dosya, girdi ve zaman ---
        if name in YANIT_KISAYOLLARI:
            arglar = [self.expr(a) for a in args]
            return YANIT_KISAYOLLARI[name].format(*arglar)

        if name in SISTEM_ISLEVLERI:
            arglar = ", ".join(self.expr(a) for a in args)
            return f"{SISTEM_ISLEVLERI[name]}({arglar})"
        if name == "panic":
            return f"$panic({self.expr(args[0])})"
        if name == "assert":
            cond = self.expr(args[0])
            msg = self.expr(args[1]) if len(args) > 1 else js_string("assert başarısız")
            return f"$assert({cond}, {msg})"

        raise AssertionError(f"bilinmeyen yerleşik: {name}")  # pragma: no cover


def generate(module: A.Module, checker: Checker, kutuphane: bool = False) -> str:
    return JsBackend(module, checker, kutuphane).emit()
