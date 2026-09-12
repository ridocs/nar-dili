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


@dataclass(eq=True, frozen=True)
class TypeVar(Type):
    """Bir tip parametresi: `struct Kutu<T>` içindeki `T`."""
    name: str

    def __str__(self) -> str:
        return self.name


def _arg_metni(args: tuple) -> str:
    return f"<{', '.join(str(a) for a in args)}>" if args else ""


class StructT(Type):
    """Bir struct tipi.

    Generic bir struct uygulandığında (`Kutu<Int>`) alanlar **tembel**
    hesaplanır. Bu şart: `struct Dugum<T> { sonraki: Dugum<T>? }` gibi
    kendine başvuran tiplerde hemen hesaplamak sonsuz döngüye girer.
    """

    def __init__(self, name: str, fields: dict | None = None,
                 mutable_fields: set | None = None, methods: dict | None = None,
                 type_params: tuple = (), type_args: tuple = (),
                 sablon: "StructT | None" = None,
                 interfaces: tuple = ()) -> None:
        self.name = name
        self.interfaces = interfaces
        self._fields = fields if fields is not None else {}
        self.mutable_fields = mutable_fields if mutable_fields is not None else set()
        self._methods = methods if methods is not None else {}
        self.type_params = type_params
        self.type_args = type_args
        self.sablon = sablon
        self._cozulmus_fields: dict | None = None
        self._cozulmus_methods: dict | None = None

    def _esleme(self) -> dict:
        kok = self.sablon
        return _param_eslemesi(kok.type_params, self.type_args) if kok else {}

    @property
    def fields(self) -> dict:
        if self.sablon is None:
            return self._fields
        if self._cozulmus_fields is None:
            esleme = self._esleme()
            self._cozulmus_fields = {
                ad: subst(t, esleme) for ad, t in self.sablon._fields.items()
            }
        return self._cozulmus_fields

    @fields.setter
    def fields(self, deger: dict) -> None:
        self._fields = deger
        self._cozulmus_fields = None

    @property
    def methods(self) -> dict:
        if self.sablon is None:
            return self._methods
        if self._cozulmus_methods is None:
            esleme = self._esleme()
            self._cozulmus_methods = {
                ad: subst(t, esleme) for ad, t in self.sablon._methods.items()
            }
        return self._cozulmus_methods

    @methods.setter
    def methods(self, deger: dict) -> None:
        self._methods = deger
        self._cozulmus_methods = None

    def __str__(self) -> str:
        return self.name + _arg_metni(self.type_args)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, StructT) and other.name == self.name
                and other.type_args == self.type_args)

    def __hash__(self) -> int:
        return hash(("struct", self.name, self.type_args))


class EnumT(Type):
    """Bir enum tipi. Varyant yükleri, StructT gibi tembel çözülür."""

    def __init__(self, name: str, variants: dict | None = None,
                 methods: dict | None = None, type_params: tuple = (),
                 type_args: tuple = (), sablon: "EnumT | None" = None,
                 interfaces: tuple = ()) -> None:
        self.name = name
        self.interfaces = interfaces
        self._variants = variants if variants is not None else {}
        self._methods = methods if methods is not None else {}
        self.type_params = type_params
        self.type_args = type_args
        self.sablon = sablon
        self._cozulmus_variants: dict | None = None
        self._cozulmus_methods: dict | None = None

    def _esleme(self) -> dict:
        kok = self.sablon
        return _param_eslemesi(kok.type_params, self.type_args) if kok else {}

    @property
    def variants(self) -> dict:
        if self.sablon is None:
            return self._variants
        if self._cozulmus_variants is None:
            esleme = self._esleme()
            self._cozulmus_variants = {
                ad: tuple(subst(t, esleme) for t in yuk)
                for ad, yuk in self.sablon._variants.items()
            }
        return self._cozulmus_variants

    @variants.setter
    def variants(self, deger: dict) -> None:
        self._variants = deger
        self._cozulmus_variants = None

    @property
    def methods(self) -> dict:
        if self.sablon is None:
            return self._methods
        if self._cozulmus_methods is None:
            esleme = self._esleme()
            self._cozulmus_methods = {
                ad: subst(t, esleme) for ad, t in self.sablon._methods.items()
            }
        return self._cozulmus_methods

    @methods.setter
    def methods(self, deger: dict) -> None:
        self._methods = deger
        self._cozulmus_methods = None

    def __str__(self) -> str:
        return self.name + _arg_metni(self.type_args)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, EnumT) and other.name == self.name
                and other.type_args == self.type_args)

    def __hash__(self) -> int:
        return hash(("enum", self.name, self.type_args))


class InterfaceT(Type):
    """Ortak davranış tanımı: hangi metotların bulunması gerektiğini söyler.

    Bir struct ya da enum, bildiriminde arayüzü adıyla üstlenir
    (`struct Nokta: Yazdirilabilir`). Böylece uyum tesadüfe değil,
    yazılı bir söze dayanır.
    """

    def __init__(self, name: str, methods: dict | None = None) -> None:
        self.name = name
        self.methods = methods if methods is not None else {}

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InterfaceT) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("interface", self.name))


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
# Sunucuya gelen bir HTTP isteği. Yalnızca Node hedefinde anlamlıdır.
ISTEK = Prim("Istek")
# Sunucudan dönen HTTP yanıtı. `yanit(...)` ailesiyle üretilir.
YANIT = Prim("Yanit")
# Çalıştırılan bir programın sonucu: çıkış kodu, çıktısı ve hata akışı.
# Yalnızca Node hedefinde anlamlıdır.
KOMUT = Prim("Komut")
NONE = NoneT()
NEVER = NeverT()
ANY = AnyT()

PRIMITIVES = {"Int": INT, "Float": FLOAT, "Bool": BOOL, "String": STRING,
              "Void": VOID, "Element": ELEMENT, "Olay": OLAY,
              "Istek": ISTEK, "Yanit": YANIT, "Komut": KOMUT}
NUMERIC = (INT, FLOAT)
ORDERED = (INT, FLOAT, STRING)


def subst(ty: Type, esleme: dict[str, Type]) -> Type:
    """Tip içindeki tip değişkenlerini verilen tiplerle değiştirir.

    `subst(Kutu<T>, {"T": Int})` → `Kutu<Int>`
    """
    if not esleme:
        return ty

    if isinstance(ty, TypeVar):
        return esleme.get(ty.name, ty)
    if isinstance(ty, OptT):
        ic = subst(ty.inner, esleme)
        return ic if isinstance(ic, OptT) else OptT(ic)
    if isinstance(ty, ListT):
        return ListT(subst(ty.elem, esleme))
    if isinstance(ty, MapT):
        return MapT(subst(ty.key, esleme), subst(ty.value, esleme))
    if isinstance(ty, FnT):
        return FnT(tuple(subst(p, esleme) for p in ty.params), subst(ty.ret, esleme))
    if isinstance(ty, RangeT):
        return RangeT(subst(ty.elem, esleme))

    if isinstance(ty, StructT):
        if not ty.type_params and not ty.type_args:
            return ty
        yeni_args = tuple(subst(a, esleme) for a in ty.type_args)
        if yeni_args == ty.type_args:
            return ty
        return uygula_struct(ty, yeni_args)

    if isinstance(ty, EnumT):
        if not ty.type_params and not ty.type_args:
            return ty
        yeni_args = tuple(subst(a, esleme) for a in ty.type_args)
        if yeni_args == ty.type_args:
            return ty
        return uygula_enum(ty, yeni_args)

    return ty


def _param_eslemesi(params: tuple[str, ...], args: tuple[Type, ...]) -> dict[str, Type]:
    return {ad: tip for ad, tip in zip(params, args)}


def uygula_struct(sablon: StructT, args: tuple[Type, ...]) -> StructT:
    """Generic bir struct'ı verilen tip argümanlarıyla uygular.

    Alanlar burada hesaplanmaz; ilk erişimde çözülür (bkz. StructT).
    """
    kok = sablon.sablon or sablon
    return StructT(
        name=kok.name,
        mutable_fields=kok.mutable_fields,
        type_params=kok.type_params,
        type_args=args,
        sablon=kok,
        interfaces=kok.interfaces,
    )


def uygula_enum(sablon: EnumT, args: tuple[Type, ...]) -> EnumT:
    """Generic bir enum'u verilen tip argümanlarıyla uygular.

    Varyant yükleri burada hesaplanmaz; ilk erişimde çözülür.
    """
    kok = sablon.sablon or sablon
    return EnumT(
        name=kok.name,
        type_params=kok.type_params,
        type_args=args,
        sablon=kok,
        interfaces=kok.interfaces,
    )


def tipdegiskenlerini_serbest_birak(ty: Type, koru: set | None = None) -> Type:
    """Çözülmemiş tip değişkenlerini `Any` yapar.

    Kısmen çözülmüş bir imzayı ipucu olarak kullanmak için gerekir:
    `(T) -> U` içinde T çözülmüşse `(Int) -> Any` verilir; böylece lambda
    parametresinin tipi bilinir, dönüş tipi ise gövdeden çıkarılır.
    """
    koru = koru or set()
    if isinstance(ty, TypeVar):
        return ty if ty.name in koru else ANY
    if isinstance(ty, OptT):
        return OptT(tipdegiskenlerini_serbest_birak(ty.inner, koru))
    if isinstance(ty, ListT):
        return ListT(tipdegiskenlerini_serbest_birak(ty.elem, koru))
    if isinstance(ty, MapT):
        return MapT(tipdegiskenlerini_serbest_birak(ty.key, koru),
                    tipdegiskenlerini_serbest_birak(ty.value, koru))
    if isinstance(ty, FnT):
        return FnT(tuple(tipdegiskenlerini_serbest_birak(p, koru) for p in ty.params),
                   tipdegiskenlerini_serbest_birak(ty.ret, koru))
    if isinstance(ty, StructT):
        if not ty.type_args:
            return ty
        return uygula_struct(ty, tuple(
            tipdegiskenlerini_serbest_birak(a, koru) for a in ty.type_args))
    if isinstance(ty, EnumT):
        if not ty.type_args:
            return ty
        return uygula_enum(ty, tuple(
            tipdegiskenlerini_serbest_birak(a, koru) for a in ty.type_args))
    return ty


def tipdegiskenleri(ty: Type, toplam: set | None = None) -> set:
    """Tipte geçen tip değişkenlerinin adları."""
    toplam = toplam if toplam is not None else set()
    if isinstance(ty, TypeVar):
        toplam.add(ty.name)
    elif isinstance(ty, OptT):
        tipdegiskenleri(ty.inner, toplam)
    elif isinstance(ty, ListT):
        tipdegiskenleri(ty.elem, toplam)
    elif isinstance(ty, RangeT):
        tipdegiskenleri(ty.elem, toplam)
    elif isinstance(ty, MapT):
        tipdegiskenleri(ty.key, toplam)
        tipdegiskenleri(ty.value, toplam)
    elif isinstance(ty, FnT):
        for p in ty.params:
            tipdegiskenleri(p, toplam)
        tipdegiskenleri(ty.ret, toplam)
    elif isinstance(ty, (StructT, EnumT)):
        for a in ty.type_args:
            tipdegiskenleri(a, toplam)
    return toplam


def tipdegiskeni_var_mi(ty: Type) -> bool:
    """Tipte çözülmemiş bir tip değişkeni kaldı mı?"""
    if isinstance(ty, TypeVar):
        return True
    if isinstance(ty, OptT):
        return tipdegiskeni_var_mi(ty.inner)
    if isinstance(ty, ListT):
        return tipdegiskeni_var_mi(ty.elem)
    if isinstance(ty, RangeT):
        return tipdegiskeni_var_mi(ty.elem)
    if isinstance(ty, MapT):
        return tipdegiskeni_var_mi(ty.key) or tipdegiskeni_var_mi(ty.value)
    if isinstance(ty, FnT):
        return any(tipdegiskeni_var_mi(p) for p in ty.params) or tipdegiskeni_var_mi(ty.ret)
    if isinstance(ty, (StructT, EnumT)):
        return any(tipdegiskeni_var_mi(a) for a in ty.type_args)
    return False


def birlestir(sablon: Type, somut: Type, esleme: dict[str, Type]) -> bool:
    """`sablon` içindeki tip değişkenlerini `somut` tipe göre çözer.

    Çözülen bağlamalar `esleme` sözlüğüne yazılır. Çelişki çıkarsa False.
    Bu, `Kutu { deger: 5 }` yazıldığında T'nin Int olduğunu bulmayı sağlar.
    """
    if isinstance(somut, (AnyT, NeverT)):
        return True

    if isinstance(sablon, TypeVar):
        onceki = esleme.get(sablon.name)
        if onceki is None:
            if isinstance(somut, NoneT):
                return True  # `none` tek başına tip belirlemez
            esleme[sablon.name] = somut
            return True
        if onceki == somut:
            return True
        ortak = common_type(onceki, somut)
        if ortak is None:
            return False
        esleme[sablon.name] = ortak
        return True

    if isinstance(sablon, OptT):
        if isinstance(somut, NoneT):
            return True
        hedef = somut.inner if isinstance(somut, OptT) else somut
        return birlestir(sablon.inner, hedef, esleme)

    if isinstance(sablon, ListT) and isinstance(somut, ListT):
        return birlestir(sablon.elem, somut.elem, esleme)
    if isinstance(sablon, MapT) and isinstance(somut, MapT):
        return (birlestir(sablon.key, somut.key, esleme)
                and birlestir(sablon.value, somut.value, esleme))
    if isinstance(sablon, FnT) and isinstance(somut, FnT):
        if len(sablon.params) != len(somut.params):
            return False
        for s, k in zip(sablon.params, somut.params):
            if not birlestir(s, k, esleme):
                return False
        return birlestir(sablon.ret, somut.ret, esleme)

    if isinstance(sablon, StructT) and isinstance(somut, StructT):
        if sablon.name != somut.name:
            return False
        if len(sablon.type_args) != len(somut.type_args):
            return False
        return all(birlestir(s, k, esleme)
                   for s, k in zip(sablon.type_args, somut.type_args))

    if isinstance(sablon, EnumT) and isinstance(somut, EnumT):
        if sablon.name != somut.name:
            return False
        if len(sablon.type_args) != len(somut.type_args):
            return False
        return all(birlestir(s, k, esleme)
                   for s, k in zip(sablon.type_args, somut.type_args))

    # Tip değişkeni içermeyen kısımlar doğrudan uyuşmalı
    return assignable(sablon, somut) or sablon == somut


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
    # Arayüzü bildiriminde üstlenen bir tip, o arayüzün beklendiği yere geçer.
    if isinstance(target, InterfaceT):
        if isinstance(source, InterfaceT):
            return source.name == target.name
        if isinstance(source, (StructT, EnumT)):
            return target.name in source.interfaces

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
