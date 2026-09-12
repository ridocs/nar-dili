"""Nar sözdizim çözümleyici (parser).

Özyinelemeli iniş + ikili operatörler için öncelik tırmanma.
Token akışını `nar_ast` düğümlerine çevirir.
"""

from __future__ import annotations

from . import nar_ast as A
from .diagnostics import NarError, Span
from .lexer import Token, tokenize

# İkili operatör öncelikleri (büyük sayı = daha sıkı bağlar).
BINARY_PRECEDENCE = {
    # Boru en gevşek bağlar: `a + b |> f` önce toplar, sonra borular.
    # `??` ile aynı seviyede ve soldan birleşiyor: `x |> f |> g`.
    "|>": 1,
    "??": 1,
    "||": 2,
    "&&": 3,
    "==": 4, "!=": 4,
    "<": 5, "<=": 5, ">": 5, ">=": 5,
    "..": 6, "..=": 6,
    "+": 7, "-": 7,
    "*": 8, "/": 8, "%": 8,
}

ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%="}


class Parser:
    def __init__(self, tokens: list[Token], filename: str, source: str = "") -> None:
        self.tokens = tokens
        self.filename = filename
        self.source = source
        self.pos = 0
        # `if`/`while`/`for` başlıklarında `{` blok başlangıcıdır; orada
        # struct ve eşleme literali yazılamaz. Bu bayrak onu engeller.
        self.no_struct_lit = False

    # ------------------------------------------------------------ yardımcılar
    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 0) -> Token:
        j = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[j]

    def at(self, *kinds: str) -> bool:
        return self.cur.kind in kinds

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.kind != "eof":
            self.pos += 1
        return tok

    def match(self, *kinds: str) -> Token | None:
        if self.cur.kind in kinds:
            return self.advance()
        return None

    def expect(self, kind: str, what: str | None = None) -> Token:
        if self.cur.kind == kind:
            return self.advance()
        found = self._describe(self.cur)
        raise NarError(
            f"{what or repr(kind)} bekleniyordu, {found} bulundu",
            self.cur.span,
        )

    @staticmethod
    def _describe(tok: Token) -> str:
        if tok.kind == "eof":
            return "dosya sonu"
        if tok.kind == "newline":
            return "satır sonu"
        if tok.kind == "ident":
            return f"tanımlayıcı {tok.value!r}"
        if tok.kind in ("int", "float"):
            return f"sayı {tok.value}"
        if tok.kind == "string":
            return "metin literali"
        return f"{tok.value!r}"

    def skip_newlines(self) -> None:
        while self.cur.kind == "newline":
            self.advance()

    def end_stmt(self) -> None:
        """Bir deyimin bittiğini doğrular: satır sonu, `;`, `}` ya da dosya sonu."""
        if self.match("newline", ";"):
            self.skip_newlines()
            return
        if self.at("}", "eof"):
            return
        raise NarError(
            f"deyim sonu bekleniyordu, {self._describe(self.cur)} bulundu",
            self.cur.span,
            hint="her deyim kendi satırında olmalı",
        )

    # ----------------------------------------------------------------- modül
    def parse_module(self) -> A.Module:
        span = self.cur.span
        items: list[A.Node] = []
        self.skip_newlines()
        while not self.at("eof"):
            items.append(self.parse_item())
            self.skip_newlines()
        return A.Module(span, self.filename, items)

    def parse_item(self) -> A.Node:
        if self.at("import"):
            return self.parse_import()
        if self.at("fn"):
            return self.parse_fn()
        if self.at("struct"):
            return self.parse_struct()
        if self.at("enum"):
            return self.parse_enum()
        if self.at("interface"):
            return self.parse_interface()
        if self.at("type"):
            return self.parse_type_alias()
        if self.at("let", "var"):
            stmt = self.parse_let()
            self.end_stmt()
            return stmt
        raise NarError(
            f"üst düzeyde bildirim bekleniyordu ({self._describe(self.cur)} bulundu)",
            self.cur.span,
            hint="üst düzeyde yalnızca import, fn, struct, enum, type, let/var olabilir",
        )

    def parse_import(self) -> A.Import:
        span = self.expect("import").span
        tok = self.expect("string", "içe aktarılacak dosya yolu")
        parts = tok.value
        if len(parts) != 1 or not isinstance(parts[0], str):
            raise NarError("import yolu düz bir metin olmalı", tok.span)
        node = A.Import(span, parts[0])
        self.end_stmt()
        return node

    def parse_type_alias(self) -> A.TypeAlias:
        span = self.expect("type").span
        name = self.expect("ident", "tip adı").value
        self.expect("=", "'='")
        target = self.parse_type()
        node = A.TypeAlias(span, name, target)
        self.end_stmt()
        return node

    # --------------------------------------------------------------- tipler
    def parse_type(self) -> A.TypeExpr:
        ty = self.parse_base_type()
        while self.at("?"):
            span = self.advance().span
            ty = A.OptionalType(span, ty)
        return ty

    def parse_type_params(self) -> tuple[list[str], dict]:
        """Bildirimdeki tip parametreleri.

        `struct Kutu<T, U>` → (["T", "U"], {})
        `fn f<T: Yazdirilabilir>` → (["T"], {"T": ["Yazdirilabilir"]})
        """
        if not self.at("<"):
            return [], {}
        self.advance()
        adlar: list[str] = []
        sinirlar: dict = {}
        while True:
            ad = self.expect("ident", "tip parametresi adı").value
            adlar.append(ad)
            if self.match(":"):
                bagli = [self.expect("ident", "arayüz adı").value]
                while self.match("+"):
                    bagli.append(self.expect("ident", "arayüz adı").value)
                sinirlar[ad] = bagli
            if not self.match(","):
                break
        self.expect(">", "tip parametrelerini kapatan '>'")
        if not adlar:
            raise NarError("tip parametre listesi boş olamaz", self.cur.span)
        return adlar, sinirlar

    def parse_interface_list(self) -> list[str]:
        """`struct Nokta: Yazdirilabilir, Karsilastirilabilir {`"""
        if not self.match(":"):
            return []
        adlar = [self.expect("ident", "arayüz adı").value]
        while self.match(","):
            adlar.append(self.expect("ident", "arayüz adı").value)
        return adlar

    def parse_interface(self) -> A.InterfaceDecl:
        span = self.expect("interface").span
        name = self.expect("ident", "arayüz adı").value
        self.expect("{", "'{'")
        self.skip_newlines()

        methods: list[A.FnDecl] = []
        while not self.at("}"):
            if self.at("eof"):
                raise NarError("kapatılmamış interface: '}' bekleniyor", span)
            methods.append(self.parse_interface_method(name))
            self.skip_newlines()

        self.expect("}", "'}'")
        if not methods:
            raise NarError(
                f"'{name}' arayüzü en az bir metot içermeli",
                span,
                hint="örnek: interface Yazdirilabilir { fn yaz() -> String }",
            )
        return A.InterfaceDecl(span, name, methods)

    def parse_interface_method(self, owner: str) -> A.FnDecl:
        """Arayüzdeki metot yalnızca imzadır; gövdesi yoktur."""
        span = self.expect("fn", "arayüz içinde 'fn'").span
        name = self.expect("ident", "metot adı").value
        self.expect("(", "'('")
        params = self.parse_params()
        self.expect(")", "')'")
        ret_type = None
        if self.match("->"):
            ret_type = self.parse_type()
        if self.at("{"):
            raise NarError(
                f"'{owner}.{name}' arayüzde gövde alamaz",
                self.cur.span,
                hint="arayüz yalnızca imzayı söyler; gövdeyi tipler yazar",
            )
        return A.FnDecl(span, name, params, ret_type, A.Block(span, []), True, owner)

    def parse_type_args(self) -> list[A.TypeExpr]:
        """Kullanımdaki tip argümanları: `Kutu<Int>` → [Int]

        `<` her zaman tip argümanı demek değildir (`a < b` de olabilir);
        bu yüzden yalnızca tip bağlamında çağrılır.
        """
        if not self.at("<"):
            return []
        self.advance()
        args: list[A.TypeExpr] = []
        while True:
            args.append(self.parse_type())
            if not self.match(","):
                break
        self.expect(">", "tip argümanlarını kapatan '>'")
        return args

    def parse_base_type(self) -> A.TypeExpr:
        tok = self.cur

        if tok.kind == "ident":
            self.advance()
            args = self.parse_type_args()
            return A.NamedType(tok.span, tok.value, args)

        if tok.kind == "[":
            self.advance()
            elem = self.parse_type()
            self.expect("]", "']'")
            return A.ListType(tok.span, elem)

        if tok.kind == "{":
            self.advance()
            key = self.parse_type()
            self.expect(":", "':'")
            value = self.parse_type()
            self.expect("}", "'}'")
            return A.MapType(tok.span, key, value)

        if tok.kind == "(":
            self.advance()
            params: list[A.TypeExpr] = []
            if not self.at(")"):
                params.append(self.parse_type())
                while self.match(","):
                    params.append(self.parse_type())
            self.expect(")", "')'")

            # `->` gelmiyorsa: tek tip parantez içindeyse gruplama
            # (`((Int) -> Bool)?`), birden çoksa tuple tipi.
            if not self.at("->"):
                if len(params) == 1:
                    return params[0]
                if len(params) >= 2:
                    return A.TupleType(tok.span, params)
                raise NarError(
                    "'->' (fonksiyon tipinin dönüş oku) bekleniyordu",
                    self.cur.span,
                    hint="parantez ya fonksiyon tipinin parametreleridir "
                         "ya da tek bir tipi gruplar",
                )

            self.advance()
            ret = self.parse_type()
            return A.FuncType(tok.span, params, ret)

        raise NarError(f"tip bekleniyordu, {self._describe(tok)} bulundu", tok.span)

    # ---------------------------------------------------------- bildirimler
    def parse_fn(self, is_method: bool = False, owner: str | None = None) -> A.FnDecl:
        span = self.expect("fn").span
        name = self.expect("ident", "fonksiyon adı").value
        type_params, type_bounds = self.parse_type_params()
        self.expect("(", "'('")
        params = self.parse_params()
        self.expect(")", "')'")

        ret_type = None
        if self.match("->"):
            ret_type = self.parse_type()

        # Kısa gövde:  fn kare(x: Int) -> Int = x * x
        if self.match("="):
            self.skip_newlines()
            value = self.parse_expr()
            body = A.Block(span, [A.Return(value.span, value)])
        else:
            body = self.parse_block()
        return A.FnDecl(span, name, params, ret_type, body, is_method, owner,
                        type_params, type_bounds)

    def parse_params(self) -> list[A.Param]:
        params: list[A.Param] = []
        self.skip_newlines()
        while not self.at(")"):
            tok = self.expect("ident", "parametre adı")
            self.expect(":", "parametre tipinden önce ':'")
            type_expr = self.parse_type()
            # `= ifade` varsa bu parametre çağrıda atlanabilir.
            varsayilan = None
            if self.match("="):
                varsayilan = self.parse_expr()
            params.append(A.Param(tok.span, tok.value, type_expr, varsayilan))
            self.skip_newlines()
            if not self.match(","):
                break
            self.skip_newlines()
        self.skip_newlines()
        return params

    def parse_struct(self) -> A.StructDecl:
        span = self.expect("struct").span
        name = self.expect("ident", "struct adı").value
        type_params, _ = self.parse_type_params()
        interfaces = self.parse_interface_list()
        self.expect("{", "'{'")
        self.skip_newlines()

        fields: list[A.FieldDecl] = []
        methods: list[A.FnDecl] = []
        while not self.at("}"):
            if self.at("fn"):
                methods.append(self.parse_fn(is_method=True, owner=name))
            else:
                mutable = self.match("var") is not None
                self.match("let")
                tok = self.expect("ident", "alan adı")
                self.expect(":", "alan tipinden önce ':'")
                type_expr = self.parse_type()
                # `var n: Int = 0` — kurarken yazılmazsa bu değer kullanılır.
                varsayilan = None
                if self.match("="):
                    varsayilan = self.parse_expr()
                fields.append(
                    A.FieldDecl(tok.span, tok.value, type_expr, mutable, varsayilan))
            self.skip_newlines()

        self.expect("}", "'}'")
        return A.StructDecl(span, name, fields, methods, type_params, interfaces)

    def parse_enum(self) -> A.EnumDecl:
        span = self.expect("enum").span
        name = self.expect("ident", "enum adı").value
        type_params, _ = self.parse_type_params()
        interfaces = self.parse_interface_list()
        self.expect("{", "'{'")
        self.skip_newlines()

        variants: list[A.VariantDecl] = []
        methods: list[A.FnDecl] = []
        while not self.at("}"):
            if self.at("fn"):
                methods.append(self.parse_fn(is_method=True, owner=name))
            else:
                tok = self.expect("ident", "varyant adı")
                payload: list[A.TypeExpr] = []
                if self.match("("):
                    payload.append(self.parse_type())
                    while self.match(","):
                        payload.append(self.parse_type())
                    self.expect(")", "')'")
                variants.append(A.VariantDecl(tok.span, tok.value, payload))
            self.skip_newlines()

        self.expect("}", "'}'")
        return A.EnumDecl(span, name, variants, methods, type_params, interfaces)

    # ------------------------------------------------------------- deyimler
    def parse_block(self) -> A.Block:
        span = self.expect("{", "'{'").span
        self.skip_newlines()
        stmts: list[A.Stmt] = []
        while not self.at("}"):
            if self.at("eof"):
                raise NarError("kapatılmamış blok: '}' bekleniyor", span)
            stmts.append(self.parse_stmt())
            self.skip_newlines()
        self.expect("}", "'}'")
        return A.Block(span, stmts)

    def parse_stmt(self) -> A.Stmt:
        if self.at("let", "var"):
            stmt = self.parse_let()
            self.end_stmt()
            return stmt
        if self.at("return"):
            span = self.advance().span
            value = None
            if not self.at("newline", "}", ";", "eof"):
                value = self.parse_expr()
            stmt = A.Return(span, value)
            self.end_stmt()
            return stmt
        if self.at("if"):
            return self.parse_if()
        if self.at("while"):
            return self.parse_while()
        if self.at("for"):
            return self.parse_for()
        if self.at("match"):
            return self.parse_match()
        if self.at("break"):
            stmt = A.Break(self.advance().span)
            self.end_stmt()
            return stmt
        if self.at("continue"):
            stmt = A.Continue(self.advance().span)
            self.end_stmt()
            return stmt

        expr = self.parse_expr()
        if self.cur.kind in ASSIGN_OPS:
            op_tok = self.advance()
            value = self.parse_expr()
            if not isinstance(expr, (A.Ident, A.FieldAccess, A.Index)):
                raise NarError(
                    "bu ifadeye atama yapılamaz",
                    expr.span,
                    hint="atamanın sol tarafı değişken, alan ya da dizin olmalı",
                )
            stmt = A.Assign(op_tok.span, expr, value, op_tok.kind)
        else:
            stmt = A.ExprStmt(expr.span, expr)
        self.end_stmt()
        return stmt

    def parse_let(self) -> A.LetStmt:
        tok = self.advance()  # let | var
        mutable = tok.kind == "var"

        # `let (a, b) = ifade` — tuple'ı adlarına açar.
        if self.at("("):
            self.advance()
            adlar = [self.expect("ident", "değişken adı").value]
            while self.match(","):
                adlar.append(self.expect("ident", "değişken adı").value)
            self.expect(")", "')'")
            self.expect("=", "'='")
            deger = self.parse_expr()
            if len(adlar) < 2:
                raise NarError(
                    "tuple açmak için en az iki ad gerekir",
                    tok.span,
                    hint="tek değer için: let a = ifade",
                )
            return A.LetStmt(tok.span, "", None, deger, mutable, adlar)

        name = self.expect("ident", "değişken adı").value
        type_expr = None
        if self.match(":"):
            type_expr = self.parse_type()
        value = None
        if self.match("="):
            value = self.parse_expr()
        if value is None and type_expr is None:
            raise NarError(
                f"'{name}' için tip ya da başlangıç değeri gerekli",
                tok.span,
                hint="örnek: let x = 0   ya da   var x: Int = 0",
            )
        if value is None and not mutable:
            raise NarError(
                f"değişmez '{name}' bildiriminde başlangıç değeri zorunlu",
                tok.span,
                hint="'let' yerine 'var' kullan ya da bir değer ata",
            )
        return A.LetStmt(tok.span, name, type_expr, value, mutable)

    def parse_condition(self) -> A.Expr:
        """Koşul ifadesi: `{` blok başlangıcı sayıldığı için literal kapalıdır."""
        saved = self.no_struct_lit
        self.no_struct_lit = True
        try:
            return self.parse_expr()
        finally:
            self.no_struct_lit = saved

    def parse_if(self) -> A.If:
        span = self.expect("if").span

        # `if let ad = ifade`: değeri açarak dallan.
        bag_ad = ""
        bag_ifade = None
        cond: A.Expr = None  # type: ignore[assignment]
        if self.at("let"):
            self.advance()
            bag_ad = self.expect("ident", "değişken adı").value
            self.expect("=", "'='")
            bag_ifade = self.parse_condition()
        else:
            cond = self.parse_condition()

        then = self.parse_block()

        otherwise = None
        # `}` ile `else` arasındaki satır sonunu hoş gör.
        save = self.pos
        self.skip_newlines()
        if self.at("else"):
            self.advance()
            if self.at("if"):
                otherwise = self.parse_if()
                return A.If(span, cond, then, otherwise, bag_ad, bag_ifade)
            otherwise = self.parse_block()
        else:
            self.pos = save

        return A.If(span, cond, then, otherwise, bag_ad, bag_ifade)

    def parse_while(self) -> A.While:
        span = self.expect("while").span

        # `while let ad = ifade`: değer geldiği sürece dön.
        if self.at("let"):
            self.advance()
            bag_ad = self.expect("ident", "değişken adı").value
            self.expect("=", "'='")
            bag_ifade = self.parse_condition()
            body = self.parse_block()
            return A.While(span, None, body, bag_ad, bag_ifade)

        cond = self.parse_condition()
        body = self.parse_block()
        return A.While(span, cond, body)

    def parse_for(self) -> A.For:
        span = self.expect("for").span
        names: list[str] = []
        if self.match("("):
            names.append(self.expect("ident", "döngü değişkeni").value)
            while self.match(","):
                names.append(self.expect("ident", "döngü değişkeni").value)
            self.expect(")", "')'")
        else:
            names.append(self.expect("ident", "döngü değişkeni").value)
        self.expect("in", "'in'")
        iterable = self.parse_condition()
        body = self.parse_block()
        return A.For(span, names, iterable, body)

    def parse_match(self) -> A.Match:
        span = self.expect("match").span
        subject = self.parse_condition()
        self.expect("{", "'{'")
        self.skip_newlines()

        arms: list[A.MatchArm] = []
        while not self.at("}"):
            if self.at("eof"):
                raise NarError("kapatılmamış match: '}' bekleniyor", span)
            pattern = self.parse_pattern()
            guard = self.parse_arm_guard()
            arrow = self.expect("->", "desenden sonra '->'")
            if self.at("{"):
                body = self.parse_block()
            else:
                body = self.parse_stmt()
            arms.append(A.MatchArm(arrow.span, pattern, body, guard))
            self.skip_newlines()

        self.expect("}", "'}'")
        if not arms:
            raise NarError("match en az bir dal içermeli", span)
        return A.Match(span, subject, arms)

    def parse_arm_guard(self):
        """`desen if koşul ->` — koşullu kol.

        Desen değişken bağladıysa koşul onu kullanabilir; bu yüzden
        `if` desenden sonra, oktan önce gelir.
        """
        if not self.at("if"):
            return None
        self.advance()
        return self.parse_condition()

    def aralik_deseni(self, tok, alt):
        """Sabit desenden sonra `..` ya da `..=` gelirse aralıktır."""
        if not self.at("..", "..="):
            return A.LiteralPat(tok.span, alt)
        kapsayan = self.cur.kind == "..="
        self.advance()
        if self.cur.kind == "-":
            ust = self.parse_unary()
        else:
            ust = self.parse_primary()
        return A.RangePat(tok.span, alt, ust, kapsayan)

    def parse_pattern(self) -> A.Pattern:
        tok = self.cur

        # `_` lexer'da tanımlayıcı olarak gelir (ident başlangıcı sayılır),
        # ama desende her zaman jokerdir: bir değere bağlanmaz.
        if tok.kind == "ident" and tok.value == "_":
            self.advance()
            return A.WildcardPat(tok.span)

        if tok.kind in ("int", "float", "string", "true", "false", "none"):
            value = self.parse_primary()
            return self.aralik_deseni(tok, value)

        if tok.kind == "-" and self.peek(1).kind in ("int", "float"):
            value = self.parse_unary()
            return self.aralik_deseni(tok, value)

        if tok.kind == ".":  # `.Varyant` — enum adı bağlamdan çıkarılır
            self.advance()
            variant = self.expect("ident", "varyant adı").value
            return A.EnumPat(tok.span, None, variant, self.parse_subpatterns())

        if tok.kind == "ident":
            self.advance()
            if self.match("."):
                variant = self.expect("ident", "varyant adı").value
                return A.EnumPat(tok.span, tok.value, variant, self.parse_subpatterns())
            if self.at("("):
                return A.EnumPat(tok.span, None, tok.value, self.parse_subpatterns())
            return A.BindPat(tok.span, tok.value)

        raise NarError(f"desen bekleniyordu, {self._describe(tok)} bulundu", tok.span)

    def parse_subpatterns(self) -> list[A.Pattern]:
        if not self.match("("):
            return []
        subs: list[A.Pattern] = []
        if not self.at(")"):
            subs.append(self.parse_pattern())
            while self.match(","):
                subs.append(self.parse_pattern())
        self.expect(")", "')'")
        return subs

    # ------------------------------------------------------------- ifadeler
    def parse_expr(self, min_prec: int = 0) -> A.Expr:
        left = self.parse_unary()

        while True:
            kind = self.cur.kind
            prec = BINARY_PRECEDENCE.get(kind)
            if prec is None or prec < min_prec:
                break
            op_tok = self.advance()
            self.skip_newlines()  # operatörden sonra satır bölünebilir

            if kind in ("..", "..="):
                right = self.parse_expr(prec + 1)
                left = A.RangeExpr(op_tok.span, left, right, kind == "..=")
                continue

            if kind == "|>":
                # `x |> f` -> `f(x)`, `x |> f(a)` -> `f(x, a)`.
                # Burada çağrıya çevriliyor; ileride hiçbir aşama boruyu
                # ayrıca bilmek zorunda kalmıyor.
                right = self.parse_expr(prec + 1)
                if isinstance(right, A.Call):
                    right.args.insert(0, left)
                    if getattr(right, "arg_names", None):
                        right.arg_names.insert(0, None)
                    left = right
                else:
                    left = A.Call(op_tok.span, right, [left], [None])
                continue

            right = self.parse_expr(prec + 1)
            left = A.Binary(op_tok.span, kind, left, right)

        return left

    def parse_unary(self) -> A.Expr:
        if self.at("-", "!"):
            tok = self.advance()
            operand = self.parse_unary()
            return A.Unary(tok.span, tok.kind, operand)
        return self.parse_postfix()

    def parse_postfix(self) -> A.Expr:
        expr = self.parse_primary()

        while True:
            tok = self.cur

            if tok.kind == ".":
                self.advance()
                # `t.0` — tuple öğesi sırasıyla okunur.
                if self.cur.kind == "int":
                    sira = self.advance()
                    expr = A.FieldAccess(tok.span, expr, str(sira.value),
                                         safe=False)
                    continue
                name = self.expect("ident", "alan ya da metot adı").value
                expr = A.FieldAccess(tok.span, expr, name, safe=False)

            elif tok.kind == "?.":
                self.advance()
                name = self.expect("ident", "alan ya da metot adı").value
                expr = A.FieldAccess(tok.span, expr, name, safe=True)

            elif tok.kind == "(":
                self.advance()
                args, adlar = self.parse_args()
                expr = A.Call(tok.span, expr, args, adlar)

            elif tok.kind == "[":
                self.advance()
                self.skip_newlines()
                index = self.parse_expr()
                self.skip_newlines()
                self.expect("]", "']'")
                expr = A.Index(tok.span, expr, index)

            elif tok.kind == "?":
                self.advance()
                expr = A.Propagate(tok.span, expr)

            elif tok.kind == "!":
                self.advance()
                expr = A.Unwrap(tok.span, expr)

            elif tok.kind == "{" and self._struct_literal_ahead(expr):
                expr = self.parse_struct_literal(expr)

            elif tok.kind == "<" and self._generic_struct_literal_ahead(expr):
                type_args = self.parse_type_args()
                expr = self.parse_struct_literal(expr, type_args)

            else:
                break

        return expr

    def _struct_literal_ahead(self, expr: A.Expr) -> bool:
        """`Nokta { x: 1 }` mi, yoksa `{` bir blok mu?

        Yalnızca büyük harfle başlayan bir tip adından sonra ve içerik
        `}` ya da `ad :` desenine uyuyorsa struct literali sayılır.
        """
        if self.no_struct_lit:
            return False
        if not isinstance(expr, A.Ident) or not expr.name[:1].isupper():
            return False
        j = 1
        while self.peek(j).kind == "newline":
            j += 1
        if self.peek(j).kind == "}":
            return True
        return self.peek(j).kind == "ident" and self.peek(j + 1).kind == ":"

    def _generic_struct_literal_ahead(self, expr: A.Expr) -> bool:
        """`Kutu<Int> {` mi, yoksa `a < b` mi?

        `<` hem karşılaştırma hem tip argümanı listesi olabilir. Ayrım için
        tip listesini denemeli okur; `>` ardından `{` gelmiyorsa geri sarar.
        """
        if self.no_struct_lit:
            return False
        if not isinstance(expr, A.Ident) or not expr.name[:1].isupper():
            return False

        kayit = self.pos
        try:
            self.parse_type_args()
        except NarError:
            self.pos = kayit
            return False

        j = 0
        while self.peek(j).kind == "newline":
            j += 1
        uygun = self.peek(j).kind == "{"
        self.pos = kayit
        return uygun

    def parse_struct_literal(self, type_expr: A.Expr,
                             type_args: list | None = None) -> A.StructLit:
        assert isinstance(type_expr, A.Ident)
        self.skip_newlines()
        span = self.expect("{", "'{'").span
        self.skip_newlines()
        fields: list[tuple[str, A.Expr]] = []

        saved = self.no_struct_lit
        self.no_struct_lit = False
        try:
            while not self.at("}"):
                name = self.expect("ident", "alan adı").value
                self.expect(":", "alan değerinden önce ':'")
                self.skip_newlines()
                fields.append((name, self.parse_expr()))
                self.skip_newlines()
                if not self.match(","):
                    break
                self.skip_newlines()
        finally:
            self.no_struct_lit = saved

        self.skip_newlines()
        self.expect("}", "'}'")
        return A.StructLit(span, type_expr.name, fields, type_args or [])

    def parse_args(self) -> tuple[list[A.Expr], list[str | None]]:
        """Çağrı argümanları ve (varsa) adları.

        `f(1, ad: 2)` — ad, parametreyi sırasından bağımsız seçer. Adsız
        argümanlar için ad listesinde None durur.
        """
        args: list[A.Expr] = []
        adlar: list[str | None] = []
        saved = self.no_struct_lit
        self.no_struct_lit = False
        try:
            self.skip_newlines()
            while not self.at(")"):
                # `ad:` yalnızca tanımlayıcının hemen ardından ':' gelirse
                # adlandırılmış argümandır; `a ? b : c` gibi bir şey değil.
                ad = None
                if self.cur.kind == "ident" and self.peek(1).kind == ":":
                    ad = self.cur.value
                    self.advance()
                    self.advance()
                    self.skip_newlines()
                adlar.append(ad)
                args.append(self.parse_expr())
                self.skip_newlines()
                if not self.match(","):
                    break
                self.skip_newlines()
            self.skip_newlines()
        finally:
            self.no_struct_lit = saved
        self.expect(")", "')'")
        return args, adlar

    def parse_primary(self) -> A.Expr:
        tok = self.cur

        if tok.kind == "int":
            self.advance()
            return A.IntLit(tok.span, tok.value)

        if tok.kind == "float":
            self.advance()
            return A.FloatLit(tok.span, tok.value)

        if tok.kind in ("true", "false"):
            self.advance()
            return A.BoolLit(tok.span, tok.kind == "true")

        if tok.kind == "none":
            self.advance()
            return A.NoneLit(tok.span)

        if tok.kind == "string":
            self.advance()
            return self.build_string(tok)

        if tok.kind == "self":
            self.advance()
            return A.SelfExpr(tok.span)

        if tok.kind == "ident":
            self.advance()
            return A.Ident(tok.span, tok.value)

        if tok.kind == "(":
            self.advance()
            saved = self.no_struct_lit
            self.no_struct_lit = False
            tuple_ogeleri = None
            try:
                self.skip_newlines()
                inner = self.parse_expr()
                self.skip_newlines()
                # Virgül varsa bu bir gruplama değil, tuple: `(a, b)`.
                if self.at(","):
                    tuple_ogeleri = [inner]
                    while self.match(","):
                        self.skip_newlines()
                        if self.at(")"):
                            break
                        tuple_ogeleri.append(self.parse_expr())
                        self.skip_newlines()
            finally:
                self.no_struct_lit = saved
            self.expect(")", "')'")
            if tuple_ogeleri is not None:
                return A.TupleLit(tok.span, tuple_ogeleri)
            return inner

        if tok.kind == "[":
            return self.parse_list_literal()

        if tok.kind == "{" and not self.no_struct_lit:
            return self.parse_map_literal()

        if tok.kind == "if":
            return self.parse_if_expr()

        if tok.kind == "match":
            return self.parse_match_expr()

        if tok.kind in ("|", "||"):
            return self.parse_lambda()

        if tok.kind == "fn":
            decl = self.parse_fn()
            return A.Lambda(
                decl.span,
                decl.params,
                decl.body,
                decl.ret_type,
            )

        raise NarError(f"ifade bekleniyordu, {self._describe(tok)} bulundu", tok.span)

    def parse_list_literal(self) -> A.ListLit:
        span = self.expect("[", "'['").span
        items: list[A.Expr] = []
        saved = self.no_struct_lit
        self.no_struct_lit = False
        try:
            self.skip_newlines()
            while not self.at("]"):
                # `[...digerleri, 3]` — yayma yalnız liste içinde geçerli.
                if self.at(".."):
                    nokta = self.advance()
                    if not self.match("."):
                        raise NarError(
                            "yayma için üç nokta gerekir: '...liste'",
                            nokta.span,
                        )
                    items.append(A.Spread(nokta.span, self.parse_expr()))
                    self.skip_newlines()
                    if not self.match(","):
                        break
                    self.skip_newlines()
                    continue
                items.append(self.parse_expr())
                self.skip_newlines()
                if not self.match(","):
                    break
                self.skip_newlines()
            self.skip_newlines()
        finally:
            self.no_struct_lit = saved
        self.expect("]", "']'")
        return A.ListLit(span, items)

    def parse_map_literal(self) -> A.MapLit:
        span = self.expect("{", "'{'").span
        entries: list[tuple[A.Expr, A.Expr]] = []
        saved = self.no_struct_lit
        self.no_struct_lit = False
        try:
            self.skip_newlines()
            while not self.at("}"):
                key = self.parse_expr()
                self.expect(":", "eşleme değerinden önce ':'")
                self.skip_newlines()
                entries.append((key, self.parse_expr()))
                self.skip_newlines()
                if not self.match(","):
                    break
                self.skip_newlines()
            self.skip_newlines()
        finally:
            self.no_struct_lit = saved
        self.expect("}", "'}'")
        return A.MapLit(span, entries)

    def parse_braced_expr(self) -> A.Expr:
        """`{ ifade }` ya da `{ deyimler...  son_ifade }` — dal gövdesi."""
        span = self.cur.span
        block = self.parse_block_body()
        return self.blok_ifadesi(block, span)

    def parse_block_body(self) -> A.Block:
        """Dal gövdesini blok olarak okur. `{` ... `}`"""
        span = self.expect("{", "'{'").span
        self.skip_newlines()
        saved = self.no_struct_lit
        self.no_struct_lit = False
        stmts: list[A.Stmt] = []
        try:
            while not self.at("}"):
                if self.at("eof"):
                    raise NarError("kapatılmamış dal: '}' bekleniyor", span)
                stmts.append(self.parse_stmt())
                self.skip_newlines()
        finally:
            self.no_struct_lit = saved
        self.expect("}", "'}'")
        return A.Block(span, stmts)

    @staticmethod
    def blok_ifadesi(block: A.Block, span) -> A.Expr:
        """Tek ifadelik blok doğrudan o ifadedir; çoklu blok BlockExpr olur.

        Tek ifade durumunu sarmalamamak hem üretilen kodu sade tutar hem de
        bu özellik eklenmeden önce yazılmış ağaçlarla aynı kalmasını sağlar.
        """
        if len(block.stmts) == 1 and isinstance(block.stmts[0], A.ExprStmt):
            return block.stmts[0].expr
        return A.BlockExpr(span, block)

    def parse_if_expr(self) -> A.IfExpr:
        span = self.expect("if").span
        cond = self.parse_condition()
        then = self.parse_braced_expr()

        self.skip_newlines()
        if not self.at("else"):
            raise NarError(
                "değer üreten 'if' için 'else' zorunlu",
                span,
                hint="her iki durumda da bir değer üretilmeli",
            )
        self.advance()
        if self.at("if"):
            otherwise: A.Expr = self.parse_if_expr()
        else:
            otherwise = self.parse_braced_expr()
        return A.IfExpr(span, cond, then, otherwise)

    def parse_match_expr(self) -> A.MatchExpr:
        span = self.expect("match").span
        subject = self.parse_condition()
        self.expect("{", "'{'")
        self.skip_newlines()

        arms: list[A.MatchArm] = []
        while not self.at("}"):
            if self.at("eof"):
                raise NarError("kapatılmamış match: '}' bekleniyor", span)
            pattern = self.parse_pattern()
            guard = self.parse_arm_guard()
            arrow = self.expect("->", "desenden sonra '->'")
            body = self.parse_arm_value()
            arms.append(A.MatchArm(arrow.span, pattern, body, guard))
            self.skip_newlines()

        self.expect("}", "'}'")
        if not arms:
            raise NarError("match en az bir dal içermeli", span)
        return A.MatchExpr(span, subject, arms)

    def parse_arm_value(self) -> A.Expr:
        """match *ifadesi* kolunun gövdesi.

        `{` iki anlama gelebilir: blok gövdesi ya da eşleme literali
        (`Bir -> {"a": 1}`). Önce blok denenir; deyim olarak okunamıyorsa
        geri sarılıp ifade olarak okunur.
        """
        saved_pos = self.pos
        saved_flag = self.no_struct_lit
        if self.at("{"):
            span = self.cur.span
            try:
                block = self.parse_block_body()
                # Boş `{}` blok değil, boş eşleme literalidir.
                if block.stmts:
                    return self.blok_ifadesi(block, span)
                self.pos = saved_pos
                self.no_struct_lit = saved_flag
            except NarError:
                self.pos = saved_pos
                self.no_struct_lit = saved_flag

        self.no_struct_lit = False
        try:
            return self.parse_expr()
        finally:
            self.no_struct_lit = saved_flag

    def parse_lambda(self) -> A.Lambda:
        tok = self.advance()  # `|` ya da `||` (parametresiz)
        params: list[A.Param] = []

        if tok.kind == "|":
            while not self.at("|"):
                name_tok = self.expect("ident", "lambda parametresi")
                type_expr = None
                if self.match(":"):
                    type_expr = self.parse_type()
                params.append(A.Param(name_tok.span, name_tok.value, type_expr))
                if not self.match(","):
                    break
            self.expect("|", "lambda parametrelerini kapatan '|'")

        ret_type = None
        if self.match("->"):
            ret_type = self.parse_type()

        if self.at("{"):
            body = self.parse_block()
        else:
            body = self.parse_expr()
        return A.Lambda(tok.span, params, body, ret_type)

    def build_string(self, tok: Token) -> A.Expr:
        """Metin literali; `${...}` gömmeleri özyinelemeli çözümlenir."""
        parts: list[object] = []
        for part in tok.value:
            if isinstance(part, str):
                parts.append(part)
                continue
            _, src, line, col = part
            sub_tokens = tokenize(src, self.filename)
            sub = Parser(sub_tokens, self.filename, src)
            sub.pos = 0
            sub.skip_newlines()
            try:
                expr = sub.parse_expr()
                sub.skip_newlines()
                if not sub.at("eof"):
                    raise NarError("gömmede fazladan token var", tok.span)
            except NarError as err:
                # Gömme içindeki konumu ana dosyaya taşı.
                raise NarError(
                    f"metin gömmesinde hata: {err.message}",
                    Span(self.filename, line, col, max(1, len(src))),
                ) from None
            _shift_spans(expr, self.filename, line, col)
            parts.append(expr)
        return A.StringLit(tok.span, parts)


def _shift_spans(node: object, filename: str, line: int, col: int) -> None:
    """Alt çözümleyiciden gelen düğümlerin konumunu gömmenin başlangıcına taşır."""
    if isinstance(node, A.Node):
        object.__setattr__(node, "span", Span(filename, line, col, 1))
        for value in vars(node).values():
            _shift_spans(value, filename, line, col)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _shift_spans(value, filename, line, col)


def parse(source: str, filename: str = "<kaynak>") -> A.Module:
    return Parser(tokenize(source, filename), filename, source).parse_module()
