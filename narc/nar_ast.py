"""Nar soyut sözdizim ağacı (AST).

Modül adı `nar_ast`, Python'un standart `ast` modülüyle çakışmasın diye.
Her düğüm kaynaktaki konumunu (`span`) taşır; tip denetleyici ayrıca
`ty` alanını doldurur, kod üreteci bunu okur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .diagnostics import Span


@dataclass
class Node:
    span: Span


# ---------------------------------------------------------------- tip yazımı
@dataclass
class TypeExpr(Node):
    """Kaynakta yazılmış tip ifadesi (henüz çözümlenmemiş)."""


@dataclass
class NamedType(TypeExpr):
    name: str = ""
    # `Kutu<Int>` gibi kullanımlarda tip argümanları
    args: list[TypeExpr] = field(default_factory=list)


@dataclass
class ListType(TypeExpr):
    elem: TypeExpr = None  # type: ignore[assignment]


@dataclass
class MapType(TypeExpr):
    key: TypeExpr = None    # type: ignore[assignment]
    value: TypeExpr = None  # type: ignore[assignment]


@dataclass
class OptionalType(TypeExpr):
    inner: TypeExpr = None  # type: ignore[assignment]


@dataclass
class FuncType(TypeExpr):
    params: list[TypeExpr] = field(default_factory=list)
    ret: Optional[TypeExpr] = None


# ----------------------------------------------------------------- ifadeler
@dataclass
class Expr(Node):
    ty: object = field(default=None, init=False, repr=False)  # checker doldurur


@dataclass
class IntLit(Expr):
    value: int = 0


@dataclass
class FloatLit(Expr):
    value: float = 0.0


@dataclass
class BoolLit(Expr):
    value: bool = False


@dataclass
class NoneLit(Expr):
    pass


@dataclass
class StringLit(Expr):
    """parts: düz metin (str) ve gömülü ifade (Expr) karışımı."""
    parts: list = field(default_factory=list)


@dataclass
class Ident(Expr):
    name: str = ""


@dataclass
class SelfExpr(Expr):
    pass


@dataclass
class ListLit(Expr):
    items: list[Expr] = field(default_factory=list)


@dataclass
class MapLit(Expr):
    entries: list[tuple[Expr, Expr]] = field(default_factory=list)


@dataclass
class StructLit(Expr):
    type_name: str = ""
    fields: list[tuple[str, Expr]] = field(default_factory=list)
    # `Kutu<Int> { ... }` biçiminde açıkça yazılan tip argümanları
    type_args: list = field(default_factory=list)


@dataclass
class Unary(Expr):
    op: str = ""
    operand: Expr = None  # type: ignore[assignment]


@dataclass
class Binary(Expr):
    op: str = ""
    left: Expr = None   # type: ignore[assignment]
    right: Expr = None  # type: ignore[assignment]


@dataclass
class RangeExpr(Expr):
    start: Expr = None  # type: ignore[assignment]
    end: Expr = None    # type: ignore[assignment]
    inclusive: bool = False


@dataclass
class Call(Expr):
    callee: Expr = None  # type: ignore[assignment]
    args: list[Expr] = field(default_factory=list)
    # `f(1, ad: 2)` — her argümanın adı; adsız verilenlerde None.
    # Denetleyici bunları parametre sırasına dizer, üretilen kodda ad kalmaz.
    arg_names: list[Optional[str]] = field(default_factory=list)


@dataclass
class Index(Expr):
    obj: Expr = None    # type: ignore[assignment]
    index: Expr = None  # type: ignore[assignment]


@dataclass
class FieldAccess(Expr):
    obj: Expr = None  # type: ignore[assignment]
    name: str = ""
    safe: bool = False  # `?.` ise True


@dataclass
class Propagate(Expr):
    """`ifade?` — none ise fonksiyondan none döner, değilse değeri açar."""
    operand: Expr = None  # type: ignore[assignment]


@dataclass
class Unwrap(Expr):
    """`x!` — opsiyoneli zorla açar, `none` ise çalışma zamanı hatası."""
    operand: Expr = None  # type: ignore[assignment]


@dataclass
class Param(Node):
    name: str = ""
    type_expr: Optional[TypeExpr] = None
    # `fn f(a: Int, b: Int = 5)` — verilmezse kullanılacak değer.
    default: Optional[Expr] = None
    ty: object = field(default=None, init=False, repr=False)


@dataclass
class Lambda(Expr):
    params: list[Param] = field(default_factory=list)
    body: object = None          # Block ya da Expr
    ret_type: Optional[TypeExpr] = None


@dataclass
class IfExpr(Expr):
    """`if kosul { deger } else { deger }` — değer üreten if. `else` zorunlu."""
    cond: Expr = None       # type: ignore[assignment]
    then: Expr = None       # type: ignore[assignment]
    otherwise: Expr = None  # IfExpr ya da Expr


@dataclass
class BlockExpr(Expr):
    """`{ deyimler...  son_ifade }` — değer üreten blok.

    `if` ve `match` ifadelerinin dallarında kullanılır. Bloğun son deyimi
    bir ifade olmalıdır; bloğun değeri odur.
    """
    block: object = None  # Block


@dataclass
class MatchExpr(Expr):
    """`match x { desen -> deger  ... }` — değer üreten match."""
    subject: Expr = None  # type: ignore[assignment]
    arms: list = field(default_factory=list)  # list[MatchArm], gövdeler Expr


# ------------------------------------------------------------------ desenler
@dataclass
class Pattern(Node):
    pass


@dataclass
class WildcardPat(Pattern):
    pass


@dataclass
class BindPat(Pattern):
    name: str = ""


@dataclass
class LiteralPat(Pattern):
    value: Expr = None  # type: ignore[assignment]


@dataclass
class EnumPat(Pattern):
    enum_name: Optional[str] = None
    variant: str = ""
    subpatterns: list[Pattern] = field(default_factory=list)


# ------------------------------------------------------------------ deyimler
@dataclass
class Stmt(Node):
    pass


@dataclass
class Block(Node):
    stmts: list[Stmt] = field(default_factory=list)


@dataclass
class LetStmt(Stmt):
    name: str = ""
    type_expr: Optional[TypeExpr] = None
    value: Optional[Expr] = None
    mutable: bool = False
    ty: object = field(default=None, init=False, repr=False)


@dataclass
class Assign(Stmt):
    target: Expr = None  # Ident | FieldAccess | Index
    value: Expr = None   # type: ignore[assignment]
    op: str = "="        # "=", "+=", "-=", ...


@dataclass
class ExprStmt(Stmt):
    expr: Expr = None  # type: ignore[assignment]


@dataclass
class Return(Stmt):
    value: Optional[Expr] = None


@dataclass
class If(Stmt):
    cond: Expr = None       # type: ignore[assignment]
    then: Block = None      # type: ignore[assignment]
    otherwise: object = None  # Block | If | None
    # `if let ad = ifade`: koşul yerine bir opsiyonel açılır. `bag_ad`
    # boşsa sıradan bir `if`tir.
    bag_ad: str = ""
    bag_ifade: Optional[Expr] = None


@dataclass
class While(Stmt):
    cond: Expr = None   # type: ignore[assignment]
    body: Block = None  # type: ignore[assignment]


@dataclass
class For(Stmt):
    names: list[str] = field(default_factory=list)  # 1 ad, ya da eşleme için (k, v)
    iterable: Expr = None  # type: ignore[assignment]
    body: Block = None     # type: ignore[assignment]
    kind: str = ""         # checker doldurur: "range" | "list" | "map" | "string"


@dataclass
class MatchArm(Node):
    pattern: Pattern = None  # type: ignore[assignment]
    body: object = None      # Block | Expr


@dataclass
class Match(Stmt):
    subject: Expr = None  # type: ignore[assignment]
    arms: list[MatchArm] = field(default_factory=list)


@dataclass
class Break(Stmt):
    pass


@dataclass
class Continue(Stmt):
    pass


# ---------------------------------------------------------- üst düzey öğeler
@dataclass
class FnDecl(Node):
    name: str = ""
    params: list[Param] = field(default_factory=list)
    ret_type: Optional[TypeExpr] = None
    body: Block = None  # type: ignore[assignment]
    is_method: bool = False
    owner: Optional[str] = None  # metotsa sahibi olan tipin adı
    type_params: list[str] = field(default_factory=list)
    # Tip parametresi sınırlamaları: `fn f<T: Yazdirilabilir>` → {"T": ["Yazdirilabilir"]}
    type_bounds: dict = field(default_factory=dict)
    ty: object = field(default=None, init=False, repr=False)


@dataclass
class FieldDecl(Node):
    name: str = ""
    type_expr: TypeExpr = None  # type: ignore[assignment]
    mutable: bool = False
    # `var sayfa: Int = 1` — kurarken verilmezse kullanılacak değer.
    default: Optional[Expr] = None
    ty: object = field(default=None, init=False, repr=False)


@dataclass
class StructDecl(Node):
    name: str = ""
    fields: list[FieldDecl] = field(default_factory=list)
    methods: list[FnDecl] = field(default_factory=list)
    type_params: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)


@dataclass
class VariantDecl(Node):
    name: str = ""
    payload: list[TypeExpr] = field(default_factory=list)
    tys: list = field(default_factory=list, repr=False)


@dataclass
class EnumDecl(Node):
    name: str = ""
    variants: list[VariantDecl] = field(default_factory=list)
    methods: list[FnDecl] = field(default_factory=list)
    type_params: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)


@dataclass
class InterfaceDecl(Node):
    """`interface Ad { fn m() -> T ... }` — gövdesiz metot imzaları."""
    name: str = ""
    methods: list[FnDecl] = field(default_factory=list)


@dataclass
class TypeAlias(Node):
    name: str = ""
    target: TypeExpr = None  # type: ignore[assignment]


@dataclass
class Import(Node):
    path: str = ""


@dataclass
class Module(Node):
    filename: str = ""
    items: list[Node] = field(default_factory=list)
