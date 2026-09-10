"""Nar tip sistemi.

Tipler yapısal olarak karşılaştırılır; `struct` ve `enum` ise adlarıyla
(nominal) karşılaştırılır. Örtük dönüşüm yoktur — tek istisna, sayı
literallerinin beklenen tip `Float` olduğunda `Float` sayılmasıdır.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class Type:
    def __str__(self) -> str:  # pragma: no cover - alt sınıflar uygular
        return self.__class__.__name__

    def __repr__(self) -> str:
        return str(self)


@dataclass(eq=True, frozen=True)
class Prim(Type):
    name: str  # Int | Float | Bool | String | Void

    def __str__(self) -> str:
        return self.name


@dataclass(eq=True, frozen=True)
class ListT(Type):
    elem: Type

    def __str__(self) -> str:
        return f"[{self.elem}]"


@dataclass(eq=True, frozen=True)
class MapT(Type):
    key: Type
    value: Type

    def __str__(self) -> str:
        return f"{{{self.key}: {self.value}}}"


@dataclass(eq=True, frozen=True)
class OptT(Type):
    inner: Type

    def __str__(self) -> str:
        return f"{self.inner}?"


@dataclass(eq=True, frozen=True)
class FnT(Type):
    params: tuple[Type, ...]
    ret: Type

    def __str__(self) -> str:
        return f"({', '.join(str(p) for p in self.params)}) -> {self.ret}"


@dataclass(eq=True, frozen=True)
class RangeT(Type):
    """`a..b` ifadesinin tipi. Yalnızca `for` döngüsünde kullanılabilir."""
    elem: Type

    def __str__(self) -> str:
        return f"Range<{self.elem}>"


@dataclass(eq=False)
class StructT(Type):
    name: str
    fields: dict[str, Type] = field(default_factory=dict)
    mutable_fields: set[str] = field(default_factory=set)
    methods: dict[str, FnT] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StructT) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("struct", self.name))


@dataclass(eq=False)
class EnumT(Type):
    name: str
    variants: dict[str, tuple[Type, ...]] = field(default_factory=dict)
    methods: dict[str, FnT] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EnumT) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("enum", self.name))


@dataclass(eq=True, frozen=True)
class NoneT(Type):
    """Yalnızca `none` literalinin tipi. Her `T?` içine atanabilir."""

    def __str__(self) -> str:
        return "none"


@dataclass(eq=True, frozen=True)
class NeverT(Type):
    """`panic()` gibi geri dönmeyen ifadelerin tipi; her yere atanabilir."""

    def __str__(self) -> str:
        return "Never"


@dataclass(eq=True, frozen=True)
class AnyT(Type):
    """Yalnızca `print`/`str` gibi yerleşiklerin parametrelerinde kullanılır."""

    def __str__(self) -> str:
        return "Any"


INT = Prim("Int")
FLOAT = Prim("Float")
BOOL = Prim("Bool")
STRING = Prim("String")
VOID = Prim("Void")
# Sayfadaki bir öğe. Yalnızca tarayıcı hedefinde anlamlıdır; Node ile
# çalıştırılan bir programda `bul(...)` her zaman `none` döner.
ELEMENT = Prim("Element")
# Bir olayın ayrıntıları: hangi tuşa basıldı, Ctrl basılı mıydı...
OLAY = Prim("Olay")
NONE = NoneT()
NEVER = NeverT()
ANY = AnyT()

PRIMITIVES = {"Int": INT, "Float": FLOAT, "Bool": BOOL, "String": STRING,
              "Void": VOID, "Element": ELEMENT, "Olay": OLAY}
NUMERIC = (INT, FLOAT)
ORDERED = (INT, FLOAT, STRING)


def unwrap_optional(t: Type) -> Type:
    return t.inner if isinstance(t, OptT) else t


def is_optional(t: Type) -> bool:
    return isinstance(t, (OptT, NoneT))


def assignable(target: Type, source: Type) -> bool:
    """`source` tipindeki bir değer `target` bekleyen yere konabilir mi?"""
    if isinstance(source, NeverT):
        return True
    if isinstance(target, AnyT) or isinstance(source, AnyT):
        return True
    if target == source:
        return True
    if isinstance(target, OptT):
        if isinstance(source, NoneT):
            return True
        if assignable(target.inner, source):
            return True
        # T?? gibi iç içe opsiyoneller düzleştirilir
        if isinstance(source, OptT) and assignable(target.inner, source.inner):
            return True

    # Daha az parametre alan bir fonksiyon, daha çok parametre bekleyen yere
    # verilebilir; fazlası yok sayılır. Olay dinleyicilerinde işe yarar:
    # `dinle("click", || { ... })` yazmak için olayı almak zorunda kalmazsın.
    if isinstance(target, FnT) and isinstance(source, FnT):
        if len(source.params) <= len(target.params):
            eslesiyor = all(
                assignable(s, t)
                for s, t in zip(source.params, target.params[:len(source.params)])
            )
            if eslesiyor and assignable(target.ret, source.ret):
                return True
            # Dönüş değeri kullanılmıyorsa (Void bekleniyorsa) tip serbesttir.
            if eslesiyor and isinstance(target.ret, Prim) and target.ret.name == "Void":
                return True
    return False


def common_type(a: Type, b: Type) -> Type | None:
    """İki dalın ortak tipi (örneğin `??` ve liste literalleri için)."""
    if assignable(a, b):
        return a
    if assignable(b, a):
        return b
    if isinstance(a, NoneT):
        return OptT(b)
    if isinstance(b, NoneT):
        return OptT(a)
    if isinstance(a, OptT) and assignable(a.inner, b):
        return a
    if isinstance(b, OptT) and assignable(b.inner, a):
        return b
    return None
