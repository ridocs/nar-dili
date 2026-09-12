"""Nar tip denetleyici.

İki geçişli çalışır:
  1. Tüm üst düzey bildirimlerin imzaları toplanır (sıraya bağımlılık olmaz).
  2. Gövdeler denetlenir; her ifade düğümüne `ty`, çözümlenen çağrılara
     `resolved` notu düşülür — kod üreteci bu notları okur.

Denetim "iki yönlüdür": beklenen tip aşağı doğru taşınır (`expected`),
bu sayede `[]`, `none` ve lambda parametreleri tip yazmadan çalışır.
"""

from __future__ import annotations

import copy

from . import nar_ast as A
from .diagnostics import NarError, NarErrors, NarUyari, duzenle
from .types import (
    ANY, BOOL, ELEMENT, FLOAT, INT, ISTEK, KOMUT, NEVER, NONE, NUMERIC, OLAY,
    ORDERED,
    PRIMITIVES, STRING, VOID, YANIT,
    AnyT, EnumT, FnT, InterfaceT, ListT, MapT, NeverT, NoneT, OptT, Prim,
    RangeT, StructT, TupleT,
    Type, TypeVar, assignable, birlestir, common_type, is_optional, subst,
    tipdegiskeni_var_mi, tipdegiskenleri, tipdegiskenlerini_serbest_birak,
    unwrap_optional, uygula_enum, uygula_struct,
)

BUILTIN_NAMES = {
    "print", "str", "len", "int", "float", "abs", "min", "max", "sqrt",
    "pow", "floor", "ceil", "round", "random", "panic", "assert",
    # Sayfa (DOM) işlemleri — yalnızca tarayıcı hedefinde anlamlıdır.
    "bul", "bulHepsi", "olustur", "govde", "zamanla", "istek", "odaklanan",
    "medyaEslesir", "medyaDinle",
    # Dosya ve program işlemleri — yalnızca Node hedefinde anlamlıdır.
    "dosyaOku", "dosyaYaz", "dosyaEkle", "dosyaVarMi", "dosyaSil",
    "klasorListele", "klasorMu", "klasorOlustur",
    "satirOku", "tumGirdi", "argumanlar", "cik", "komutCalistir",
    # Zaman — her ortamda çalışır.
    "simdi", "zamanMetni",
    # Sunucu — yalnızca Node hedefinde anlamlıdır.
    "sunucu", "yanit", "yanitMetin", "yanitHtml", "yanitJson", "yanitDosya",
    "yonlendir", "icerikTipi", "ortam", "rastgeleMetin", "sha256",
    # Karakter kodu dönüşümü.
    "koddan",
}

# Sayfa işlemlerinin imzaları. Bunlar `Element` tipiyle çalışır.
def _sayfa_imzalari() -> dict[str, FnT]:
    return {
        "odaklanan": FnT((), OptT(ELEMENT)),
        "medyaEslesir": FnT((STRING,), BOOL),
        "medyaDinle": FnT((STRING, FnT((BOOL,), VOID)), VOID),
        "bul": FnT((STRING,), OptT(ELEMENT)),
        "bulHepsi": FnT((STRING,), ListT(ELEMENT)),
        "olustur": FnT((STRING,), ELEMENT),
        "govde": FnT((), ELEMENT),
        "zamanla": FnT((INT, FnT((), VOID)), VOID),
        "istek": FnT((STRING, STRING, STRING, FnT((STRING,), VOID)), VOID),
    }


# Dosya, girdi ve zaman işlemleri.
def _sistem_imzalari() -> dict[str, FnT]:
    return {
        "dosyaOku": FnT((STRING,), OptT(STRING)),
        "dosyaYaz": FnT((STRING, STRING), BOOL),
        "dosyaEkle": FnT((STRING, STRING), BOOL),
        "dosyaVarMi": FnT((STRING,), BOOL),
        "dosyaSil": FnT((STRING,), BOOL),
        "klasorListele": FnT((STRING,), ListT(STRING)),
        "klasorMu": FnT((STRING,), BOOL),
        "klasorOlustur": FnT((STRING,), BOOL),
        "satirOku": FnT((), OptT(STRING)),
        "tumGirdi": FnT((), STRING),
        "argumanlar": FnT((), ListT(STRING)),
        "cik": FnT((INT,), NEVER),
        # Başka bir programı çalıştırır ve bitmesini bekler.
        "komutCalistir": FnT((STRING, ListT(STRING)), KOMUT),
        "simdi": FnT((), INT),
        "zamanMetni": FnT((), STRING),
        # Karakter kodundan metin: koddan(65) → "A"
        "koddan": FnT((INT,), STRING),
        # Sunucu
        "sunucu": FnT((INT, FnT((ISTEK,), YANIT)), VOID),
        "yanit": FnT((INT, STRING), YANIT),
        "yanitMetin": FnT((STRING,), YANIT),
        "yanitHtml": FnT((STRING,), YANIT),
        "yanitJson": FnT((STRING,), YANIT),
        "yanitDosya": FnT((STRING,), OptT(YANIT)),
        "yonlendir": FnT((STRING,), YANIT),
        "icerikTipi": FnT((STRING,), STRING),
        "ortam": FnT((STRING,), OptT(STRING)),
        "rastgeleMetin": FnT((INT,), STRING),
        "sha256": FnT((STRING,), STRING),
    }


def is_void(t: Type) -> bool:
    return isinstance(t, Prim) and t.name == "Void"


class Binding:
    __slots__ = ("ty", "mutable", "kind", "span", "okundu")

    def __init__(self, ty: Type, mutable: bool, kind: str = "var",
                 span=None) -> None:
        self.ty = ty
        self.mutable = mutable
        self.kind = kind  # "var" | "fn" | "self"
        # Tanımın yeri ve okunup okunmadığı: kullanılmayan değişken uyarısı
        # için. `span` yoksa (parametre, döngü değişkeni) uyarı verilmez.
        self.span = span
        self.okundu = False


class Env:
    def __init__(self, parent: "Env | None" = None) -> None:
        self.parent = parent
        self.names: dict[str, Binding] = {}

    def define(self, name: str, ty: Type, mutable: bool = False, kind: str = "var",
               span=None) -> None:
        self.names[name] = Binding(ty, mutable, kind, span)

    def lookup(self, name: str, oku: bool = True) -> Binding | None:
        """Adı bulur. `oku` açıkken bu bir kullanım sayılır; atama hedefi
        ya da yeniden tanım denetimi için kapatılır."""
        env: Env | None = self
        while env is not None:
            if name in env.names:
                b = env.names[name]
                if oku:
                    b.okundu = True
                return b
            env = env.parent
        return None

    def child(self) -> "Env":
        return Env(self)


class _SoruYasagi:
    """`?` yasağını bir kapsam boyunca açar, çıkışta eski hâline döndürür."""

    def __init__(self, denetci: "Checker", neden: str) -> None:
        self.denetci = denetci
        self.neden = neden
        self.onceki: str | None = None

    def __enter__(self) -> "_SoruYasagi":
        self.onceki = self.denetci.soru_yasak
        # İçteki yasak dıştakini gölgelemesin: ilk neden daha anlamlı.
        if self.onceki is None:
            self.denetci.soru_yasak = self.neden
        return self

    def __exit__(self, *_) -> None:
        self.denetci.soru_yasak = self.onceki


class Checker:
    def __init__(self, module: A.Module, source: str = "", kutuphane: bool = False) -> None:
        self.module = module
        self.source = source
        # Kütüphane derlemesinde `main` aranmaz; dosya başka koddan çağrılır.
        self.kutuphane = kutuphane
        self.structs: dict[str, StructT] = {}
        # Struct alanlarinin varsayilan ifadeleri: kurarken yazilmayan
        # alan bu ifadenin kopyasiyla doldurulur.
        self.struct_varsayilanlari: dict[str, dict] = {}
        self.enums: dict[str, EnumT] = {}
        # Varyant adı -> onu tanımlayan enum adları. Tek sahibi olan
        # varyantlar enum adı yazılmadan da kullanılabilir.
        self.varyant_sahipleri: dict[str, list[str]] = {}
        self.interfaces: dict[str, InterfaceT] = {}
        # Kapsamdaki tip parametrelerinin arayüz sınırlamaları
        self.tip_sinirlari: dict[str, list[str]] = {}
        self.aliases: dict[str, Type] = {}
        self.functions: dict[str, FnT] = {}
        self.fn_decls: dict[str, A.FnDecl] = {}
        self.globals = Env()
        self.errors: list[NarError] = []
        # Derlemeyi durdurmayan bildirimler; `check()` bunları fırlatmaz.
        self.warnings: list[NarError] = []
        # denetim durumu
        self.current_ret: Type = VOID
        self.self_type: Type | None = None
        self.loop_depth = 0
        # `?` koşullu değerlendirilen bir yerdeyse burada nedeni durur;
        # None ise kullanılabilir.
        self.soru_yasak: str | None = None
        # Kapsamdaki tip parametreleri: `struct Kutu<T>` içindeyken {"T": T}
        self.tip_degiskenleri: dict[str, Type] = {}

    # ------------------------------------------------------------ giriş noktası
    def check(self) -> None:
        self.collect()
        self.check_bodies()
        if self.errors:
            # Tüm hatalar birden bildirilir; kullanıcı hepsini tek seferde görür.
            raise NarErrors(duzenle(self.errors))

    def error(self, message: str, span, hint: str | None = None) -> None:
        self.errors.append(NarError(message, span, hint))

    def warn(self, message: str, span, hint: str | None = None) -> None:
        self.warnings.append(NarUyari(message, span, hint))

    def kullanilmayanlari_bildir(self, env: "Env") -> None:
        """Kapsam kapanırken hiç okunmamış let/var'ları bildirir."""
        for ad, b in env.names.items():
            if b.kind != "var" or b.okundu or b.span is None:
                continue
            if ad.startswith("_"):
                continue
            self.warn(
                f"'{ad}' tanımlanmış ama hiç kullanılmamış",
                b.span,
                hint=f"kullanmayacaksan sil ya da '_{ad}' diye adlandır",
            )

    # -------------------------------------------------------------- 1. geçiş
    def collect(self) -> None:
        # a) tip adlarını (henüz içleri boş) kaydet — karşılıklı başvuru için
        for item in self.module.items:
            if isinstance(item, A.StructDecl):
                if item.name in self.structs or item.name in self.enums:
                    self.error(f"'{item.name}' tipi zaten tanımlı", item.span)
                self.structs[item.name] = StructT(
                    item.name, type_params=tuple(item.type_params),
                    interfaces=tuple(item.interfaces))
            elif isinstance(item, A.EnumDecl):
                if item.name in self.structs or item.name in self.enums:
                    self.error(f"'{item.name}' tipi zaten tanımlı", item.span)
                self.enums[item.name] = EnumT(
                    item.name, type_params=tuple(item.type_params),
                    interfaces=tuple(item.interfaces))

        # a2) arayüzler ve metot imzaları
        for item in self.module.items:
            if isinstance(item, A.InterfaceDecl):
                if item.name in self.structs or item.name in self.enums                         or item.name in self.interfaces:
                    self.error(f"'{item.name}' tipi zaten tanımlı", item.span)
                self.interfaces[item.name] = InterfaceT(item.name)

        for item in self.module.items:
            if isinstance(item, A.InterfaceDecl):
                arayuz = self.interfaces[item.name]
                for m in item.methods:
                    if m.name in arayuz.methods:
                        self.error(
                            f"'{item.name}' içinde '{m.name}' metodu yinelendi", m.span)
                    arayuz.methods[m.name] = self.fn_signature(m)

        # b) tip takma adları
        for item in self.module.items:
            if isinstance(item, A.TypeAlias):
                if item.name in self.structs or item.name in self.enums:
                    self.error(f"'{item.name}' tipi zaten tanımlı", item.span)
                self.aliases[item.name] = self.resolve_type(item.target)

        # c) alanlar, varyantlar ve metot imzaları
        for item in self.module.items:
            if isinstance(item, A.StructDecl):
                st = self.structs[item.name]
                onceki = self.tip_kapsami_ac(item.type_params)
                for f in item.fields:
                    if f.name in st.fields:
                        self.error(f"'{item.name}' içinde '{f.name}' alanı yinelendi", f.span)
                    f.ty = self.resolve_type(f.type_expr)
                    st.fields[f.name] = f.ty
                    if f.mutable:
                        st.mutable_fields.add(f.name)
                    if f.default is not None:
                        self.struct_varsayilanlari.setdefault(
                            item.name, {})[f.name] = f.default
                for m in item.methods:
                    st.methods[m.name] = self.fn_signature(m)
                    if m.name in st.fields:
                        self.error(f"'{m.name}' hem alan hem metot olamaz", m.span)
                self.tip_kapsami_kapat(onceki)

            elif isinstance(item, A.EnumDecl):
                et = self.enums[item.name]
                onceki = self.tip_kapsami_ac(item.type_params)
                for v in item.variants:
                    if v.name in et.variants:
                        self.error(f"'{item.name}' içinde '{v.name}' varyantı yinelendi", v.span)
                    v.tys = [self.resolve_type(t) for t in v.payload]
                    et.variants[v.name] = tuple(v.tys)
                for m in item.methods:
                    et.methods[m.name] = self.fn_signature(m)
                self.tip_kapsami_kapat(onceki)

        # c2) çıplak varyant adları için indeks
        for ad, et in self.enums.items():
            for v in et.variants:
                self.varyant_sahipleri.setdefault(v, []).append(ad)

        # d) serbest fonksiyonlar
        for item in self.module.items:
            if isinstance(item, A.FnDecl):
                # Yerleşik bir adı yeniden tanımlamak serbesttir: kullanıcının
                # tanımı kazanır. Böylece dile yeni bir yerleşik eklemek
                # mevcut programları kırmaz.
                if item.name in self.functions:
                    self.error(f"'{item.name}' fonksiyonu zaten tanımlı", item.span)
                sig = self.fn_signature(item)
                self.functions[item.name] = sig
                self.fn_decls[item.name] = item
                self.globals.define(item.name, sig, False, "fn")

        # e) üst düzey değişkenler (sırayla, çünkü değer denetimi gerekir)
        for item in self.module.items:
            if isinstance(item, A.LetStmt):
                self.check_let(item, self.globals)

        # f) üstlenilen arayüzler gerçekten uygulanmış mı?
        for item in self.module.items:
            if isinstance(item, A.StructDecl):
                self.arayuz_uyumunu_dogrula(item, self.structs[item.name])
            elif isinstance(item, A.EnumDecl):
                self.arayuz_uyumunu_dogrula(item, self.enums[item.name])

        if "main" not in self.functions:
            if not self.kutuphane:
                self.error(
                    "programda 'main' fonksiyonu yok",
                    self.module.span,
                    hint="giriş noktası olarak `fn main() { ... }` ekle",
                )
        elif self.functions["main"].params:
            self.error("'main' parametre almamalı", self.fn_decls["main"].span)

    def arayuz_uyumunu_dogrula(self, decl, tip) -> None:
        """Bildirimde üstlenilen her arayüzün metotları gerçekten var mı?"""
        for arayuz_adi in decl.interfaces:
            arayuz = self.interfaces.get(arayuz_adi)
            if arayuz is None:
                self.error(
                    f"bilinmeyen arayüz: '{arayuz_adi}'",
                    decl.span,
                    hint=f"var olanlar: {', '.join(self.interfaces) or 'yok'}",
                )
                continue

            for metot_adi, beklenen in arayuz.methods.items():
                mevcut = tip.methods.get(metot_adi)
                if mevcut is None:
                    self.error(
                        f"'{decl.name}', '{arayuz_adi}' arayüzünü üstleniyor ama "
                        f"'{metot_adi}' metodu yok",
                        decl.span,
                        hint=f"eklenecek imza: fn {metot_adi}{beklenen}",
                    )
                    continue
                if mevcut != beklenen:
                    self.error(
                        f"'{decl.name}.{metot_adi}' imzası arayüzle uyuşmuyor: "
                        f"'{beklenen}' bekleniyordu, '{mevcut}' bulundu",
                        decl.span,
                    )

    def fn_signature(self, decl: A.FnDecl) -> FnT:
        onceki = self.tip_kapsami_ac(decl.type_params, decl.type_bounds)
        params = []
        seen: set[str] = set()
        for p in decl.params:
            if p.name in seen:
                self.error(f"'{p.name}' parametresi yinelendi", p.span)
            seen.add(p.name)
            p.ty = self.resolve_type(p.type_expr)
            params.append(p.ty)
        ret = self.resolve_type(decl.ret_type) if decl.ret_type else VOID
        # Varsayılanlı parametreler sonda olmalı: ortada bir varsayılan,
        # sonrasındaki zorunlu parametreyi çağrıda ulaşılmaz yapardı.
        zorunlu = len(decl.params)
        for i, p in enumerate(decl.params):
            if p.default is not None:
                zorunlu = i
                break
        for p in decl.params[zorunlu:]:
            if p.default is None:
                self.error(
                    f"'{p.name}' varsayılansız; varsayılanı olan parametrelerden "
                    "sonra gelemez",
                    p.span,
                    hint="varsayılanlı parametreleri listenin sonuna al",
                )
        sig = FnT(tuple(params), ret,
                  tuple(p.name for p in decl.params), zorunlu, decl)
        decl.ty = sig
        self.tip_kapsami_kapat(onceki)
        return sig

    # ------------------------------------------------------ generic yardımcı
    def genel_tipi_uygula(self, sablon, node: A.NamedType, struct_mu: bool) -> Type:
        """`Kutu<Int>` gibi bir kullanımı çözer, sayı uyuşmazlığını bildirir."""
        beklenen = len(sablon.type_params)
        args = [self.resolve_type(a) for a in node.args]

        if beklenen == 0:
            if args:
                self.error(f"'{sablon.name}' tip argümanı almaz", node.span)
            return sablon

        if not args:
            self.error(
                f"'{sablon.name}' {beklenen} tip argümanı bekler; "
                f"örnek: {sablon.name}<{', '.join(sablon.type_params)}>",
                node.span,
            )
            args = [ANY] * beklenen
        elif len(args) != beklenen:
            self.error(
                f"'{sablon.name}' {beklenen} tip argümanı bekler, "
                f"{len(args)} verildi",
                node.span,
            )
            args = (args + [ANY] * beklenen)[:beklenen]

        uygula = uygula_struct if struct_mu else uygula_enum
        return uygula(sablon, tuple(args))

    def tip_kapsami_ac(self, params, sinirlar: dict | None = None) -> tuple:
        """Tip parametrelerini kapsama alır, önceki kapsamı döndürür."""
        onceki = (self.tip_degiskenleri, self.tip_sinirlari)
        if params:
            self.tip_degiskenleri = dict(self.tip_degiskenleri)
            self.tip_sinirlari = dict(self.tip_sinirlari)
            for ad in params:
                self.tip_degiskenleri[ad] = TypeVar(ad)
                self.tip_sinirlari[ad] = list((sinirlar or {}).get(ad, []))
        return onceki

    def tip_kapsami_kapat(self, onceki: tuple) -> None:
        self.tip_degiskenleri, self.tip_sinirlari = onceki

    @staticmethod
    def sablon_ornegi(sablon):
        """Generic tipi kendi parametreleriyle uygular: `Kutu` → `Kutu<T>`.

        Metot gövdelerinde `self`in tipi budur.
        """
        if not sablon.type_params:
            return sablon
        args = tuple(TypeVar(p) for p in sablon.type_params)
        uygula = uygula_struct if isinstance(sablon, StructT) else uygula_enum
        return uygula(sablon, args)

    # ------------------------------------------------------- tip çözümlemesi
    def resolve_type(self, node: A.TypeExpr | None) -> Type:
        if node is None:
            return VOID

        if isinstance(node, A.NamedType):
            # Kapsamdaki tip parametresi (T, U…) her şeyden önce gelir.
            if node.name in self.tip_degiskenleri:
                if node.args:
                    self.error(f"'{node.name}' bir tip parametresi; "
                               "tip argümanı alamaz", node.span)
                return self.tip_degiskenleri[node.name]

            if node.name in PRIMITIVES:
                if node.args:
                    self.error(f"'{node.name}' tip argümanı almaz", node.span)
                return PRIMITIVES[node.name]

            if node.name in self.interfaces:
                if node.args:
                    self.error(f"'{node.name}' bir arayüz; tip argümanı almaz",
                               node.span)
                return self.interfaces[node.name]

            if node.name in self.structs:
                return self.genel_tipi_uygula(self.structs[node.name], node, True)
            if node.name in self.enums:
                return self.genel_tipi_uygula(self.enums[node.name], node, False)

            if node.name in self.aliases:
                if node.args:
                    self.error(f"'{node.name}' bir tip takma adı; "
                               "tip argümanı alamaz", node.span)
                return self.aliases[node.name]

            self.error(f"bilinmeyen tip: '{node.name}'", node.span)
            return ANY

        if isinstance(node, A.TupleType):
            return TupleT(tuple(self.resolve_type(e) for e in node.elems))

        if isinstance(node, A.ListType):
            return ListT(self.resolve_type(node.elem))
        if isinstance(node, A.MapType):
            key = self.resolve_type(node.key)
            if key not in (INT, STRING, BOOL, FLOAT):
                self.error(
                    f"eşleme anahtarı '{key}' olamaz",
                    node.span,
                    hint="anahtar Int, Float, Bool ya da String olmalı",
                )
            return MapT(key, self.resolve_type(node.value))
        if isinstance(node, A.OptionalType):
            inner = self.resolve_type(node.inner)
            return inner if isinstance(inner, OptT) else OptT(inner)
        if isinstance(node, A.FuncType):
            return FnT(tuple(self.resolve_type(p) for p in node.params),
                       self.resolve_type(node.ret))

        self.error("çözümlenemeyen tip", node.span)
        return ANY

    # -------------------------------------------------------------- 2. geçiş
    def check_bodies(self) -> None:
        for item in self.module.items:
            if isinstance(item, A.FnDecl):
                self.check_fn(item, None)
            elif isinstance(item, A.StructDecl):
                onceki = self.tip_kapsami_ac(item.type_params)
                ornek = self.sablon_ornegi(self.structs[item.name])
                for m in item.methods:
                    self.check_fn(m, ornek)
                self.tip_kapsami_kapat(onceki)
            elif isinstance(item, A.EnumDecl):
                onceki = self.tip_kapsami_ac(item.type_params)
                ornek = self.sablon_ornegi(self.enums[item.name])
                for m in item.methods:
                    self.check_fn(m, ornek)
                self.tip_kapsami_kapat(onceki)

    def check_fn(self, decl: A.FnDecl, owner: Type | None) -> None:
        onceki_tipler = self.tip_kapsami_ac(decl.type_params, decl.type_bounds)
        env = self.globals.child()
        prev_ret, prev_self = self.current_ret, self.self_type
        self.current_ret = decl.ty.ret if decl.ty else VOID
        self.self_type = owner
        if owner is not None:
            env.define("self", owner, False, "self")
        for p in decl.params:
            env.define(p.name, p.ty, False)

        self.check_block(decl.body, env)

        if not is_void(self.current_ret) and not self.terminates(decl.body):
            self.error(
                f"'{decl.name}' her yolda değer döndürmüyor "
                f"(dönüş tipi {self.current_ret})",
                decl.span,
                hint="eksik dalın sonuna 'return' ekle",
            )

        self.current_ret, self.self_type = prev_ret, prev_self
        self.tip_kapsami_kapat(onceki_tipler)

    # --------------------------------------------------------------- deyimler
    def check_block(self, block: A.Block, env: Env) -> None:
        inner = env.child()
        for stmt in block.stmts:
            self.check_stmt(stmt, inner)
        self.kullanilmayanlari_bildir(inner)

    def check_stmt(self, stmt: A.Stmt, env: Env) -> None:
        if isinstance(stmt, A.LetStmt):
            self.check_let(stmt, env)

        elif isinstance(stmt, A.ExprStmt):
            self.check_expr(stmt.expr, env)

        elif isinstance(stmt, A.Assign):
            self.check_assign(stmt, env)

        elif isinstance(stmt, A.Return):
            expected = self.current_ret
            void_ret = is_void(expected)
            if stmt.value is None:
                if not void_ret:
                    self.error(f"'{expected}' döndürülmeli ama return boş", stmt.span)
            else:
                got = self.check_expr(stmt.value, env, expected if not void_ret else None)
                if void_ret:
                    self.error("bu fonksiyon değer döndürmemeli", stmt.span)
                elif not assignable(expected, got):
                    self.error(
                        f"dönüş tipi uyuşmuyor: '{expected}' bekleniyordu, '{got}' bulundu",
                        stmt.value.span,
                    )

        elif isinstance(stmt, A.If):
            self.check_if(stmt, env)

        elif isinstance(stmt, A.While):
            if stmt.bag_ad:
                self.check_while_bagli(stmt, env)
            else:
                # Koşul her turda yeniden değerlendirilir; erken çıkış ise
                # döngüden önce bir kez konurdu.
                with self.yasakta("while koşulunda"):
                    cond = self.check_expr(stmt.cond, env, BOOL)
                self.expect_bool(cond, stmt.cond.span, "while koşulu")
                self.loop_depth += 1
                body_env = env.child()
                self.apply_narrowing(stmt.cond, body_env, True)
                self.check_block(stmt.body, body_env)
                self.loop_depth -= 1

        elif isinstance(stmt, A.For):
            self.check_for(stmt, env)

        elif isinstance(stmt, A.Match):
            self.check_match(stmt, env)

        elif isinstance(stmt, (A.Break, A.Continue)):
            if self.loop_depth == 0:
                word = "break" if isinstance(stmt, A.Break) else "continue"
                self.error(f"'{word}' yalnızca döngü içinde kullanılabilir", stmt.span)

        else:  # pragma: no cover
            self.error(f"denetlenemeyen deyim: {type(stmt).__name__}", stmt.span)

    def check_let_acma(self, stmt: A.LetStmt, env: Env) -> None:
        """`let (a, b) = ifade` — tuple'ı adlarına dağıtır."""
        got = self.check_expr(stmt.value, env)
        taban = unwrap_optional(got)
        if isinstance(taban, AnyT):
            for ad in stmt.names:
                env.define(ad, ANY, stmt.mutable, span=stmt.span)
            return
        if not isinstance(taban, TupleT):
            self.error(
                f"tuple açılabilir; '{got}' açılamaz",
                stmt.value.span,
                hint="sağ taraf (Int, String) gibi bir tuple olmalı",
            )
            for ad in stmt.names:
                env.define(ad, ANY, stmt.mutable, span=stmt.span)
            return
        if len(stmt.names) != len(taban.elems):
            self.error(
                f"{len(taban.elems)} öğeli tuple {len(stmt.names)} ada "
                "açılamaz",
                stmt.span,
                hint=f"ad sayısı öğe sayısıyla aynı olmalı: {taban}",
            )
        for i, ad in enumerate(stmt.names):
            tip = taban.elems[i] if i < len(taban.elems) else ANY
            if ad in env.names:
                self.error(f"'{ad}' bu kapsamda zaten tanımlı", stmt.span)
            env.define(ad, tip, stmt.mutable, span=stmt.span)

    def check_let(self, stmt: A.LetStmt, env: Env) -> None:
        if stmt.names:
            self.check_let_acma(stmt, env)
            return
        declared = self.resolve_type(stmt.type_expr) if stmt.type_expr else None

        if stmt.value is None:
            stmt.ty = declared or ANY
        else:
            got = self.check_expr(stmt.value, env, declared)
            if declared is None:
                if isinstance(got, (NoneT, NeverT)):
                    self.error(
                        f"'{stmt.name}' değişkeninin tipi çıkarılamıyor",
                        stmt.span,
                        hint=f"tipi yaz: let {stmt.name}: <Tip> = ...",
                    )
                    got = ANY
                if isinstance(got, RangeT):
                    self.error("aralık ifadesi değişkene atanamaz", stmt.value.span,
                               hint="aralık yalnızca 'for ... in' içinde kullanılır")
                    got = ANY
                stmt.ty = got
            else:
                if not assignable(declared, got):
                    self.error(
                        f"'{stmt.name}': '{declared}' bekleniyordu, '{got}' bulundu",
                        stmt.value.span,
                    )
                stmt.ty = declared

        if stmt.name in env.names:
            self.error(f"'{stmt.name}' bu kapsamda zaten tanımlı", stmt.span)
        env.define(stmt.name, stmt.ty, stmt.mutable, span=stmt.span)

    def check_assign(self, stmt: A.Assign, env: Env) -> None:
        target = stmt.target

        if isinstance(target, A.Ident):
            # Atama hedefi bir kullanım değildir: yazılıp hiç okunmayan
            # değişken yine "kullanılmamış" sayılır.
            binding = env.lookup(target.name, oku=False)
            if binding is None:
                self.error(f"tanımsız değişken: '{target.name}'", target.span)
                return
            if not binding.mutable:
                self.error(
                    f"'{target.name}' değişmez, değeri değiştirilemez",
                    target.span,
                    hint="bildirimde 'let' yerine 'var' kullan",
                )
            target.ty = binding.ty
            expected = binding.ty

        elif isinstance(target, A.FieldAccess):
            obj_ty = self.check_expr(target.obj, env)
            base = unwrap_optional(obj_ty)
            if not isinstance(base, StructT):
                self.error(f"'{obj_ty}' tipinde alana atama yapılamaz", target.span)
                return
            if target.name not in base.fields:
                self.error(f"'{base.name}' tipinde '{target.name}' alanı yok", target.span)
                return
            if target.name not in base.mutable_fields:
                self.error(
                    f"'{base.name}.{target.name}' değişmez bir alan",
                    target.span,
                    hint=f"struct içinde 'var {target.name}: ...' olarak tanımla",
                )
            expected = base.fields[target.name]
            target.ty = expected

        elif isinstance(target, A.Index):
            obj_ty = self.check_expr(target.obj, env)
            if isinstance(obj_ty, ListT):
                self.check_expr(target.index, env, INT)
                expected = obj_ty.elem
            elif isinstance(obj_ty, MapT):
                self.check_expr(target.index, env, obj_ty.key)
                expected = obj_ty.value
            else:
                self.error(f"'{obj_ty}' dizinlenemez", target.span)
                return
            target.ty = expected
        else:  # parser zaten engelliyor
            self.error("bu ifadeye atama yapılamaz", target.span)
            return

        if stmt.op == "=":
            got = self.check_expr(stmt.value, env, expected)
            if not assignable(expected, got):
                self.error(
                    f"atama tipi uyuşmuyor: '{expected}' bekleniyordu, '{got}' bulundu",
                    stmt.value.span,
                )
        else:
            op = stmt.op[0]
            got = self.check_expr(stmt.value, env, expected)
            result = self.binary_result(op, expected, got, stmt.span)
            if not assignable(expected, result):
                self.error(
                    f"'{stmt.op}' sonucu '{result}', '{expected}' bekleniyordu",
                    stmt.span,
                )

    def check_if(self, stmt: A.If, env: Env) -> None:
        if stmt.bag_ad:
            self.check_if_bagli(stmt, env)
            return

        cond = self.check_expr(stmt.cond, env, BOOL)
        self.expect_bool(cond, stmt.cond.span, "if koşulu")

        then_env = env.child()
        self.apply_narrowing(stmt.cond, then_env, True)
        self.check_block(stmt.then, then_env)

        if isinstance(stmt.otherwise, A.Block):
            else_env = env.child()
            self.apply_narrowing(stmt.cond, else_env, False)
            self.check_block(stmt.otherwise, else_env)
        elif isinstance(stmt.otherwise, A.If):
            else_env = env.child()
            self.apply_narrowing(stmt.cond, else_env, False)
            self.check_if(stmt.otherwise, else_env)

    def check_while_bagli(self, stmt: A.While, env: Env) -> None:
        """`while let ad = ifade` — değer geldiği sürece döner.

        İfade her turda yeniden hesaplanır; `none` gelince döngü biter.
        Açılmış değer yalnız gövdede görünür.
        """
        with self.yasakta("while koşulunda"):
            ty = self.check_expr(stmt.bag_ifade, env)
        if isinstance(ty, OptT):
            ic = ty.inner
        elif isinstance(ty, AnyT):
            ic = ANY
        else:
            self.error(
                f"'while let' opsiyonel bir değer bekler, '{ty}' bulundu",
                stmt.bag_ifade.span,
                hint="olmayabilen bir değer için tipi 'T?' olmalı",
            )
            ic = ty

        self.loop_depth += 1
        govde_env = env.child()
        govde_env.define(stmt.bag_ad, ic, False)
        self.check_block(stmt.body, govde_env)
        self.loop_depth -= 1

    def check_if_bagli(self, stmt: A.If, env: Env) -> None:
        """`if let ad = ifade` — açılmış değer yalnız `then` dalında görünür."""
        ty = self.check_expr(stmt.bag_ifade, env)
        if isinstance(ty, OptT):
            ic = ty.inner
        elif isinstance(ty, AnyT):
            ic = ANY
        else:
            self.error(
                f"'if let' opsiyonel bir değer bekler, '{ty}' bulundu",
                stmt.bag_ifade.span,
                hint="olmayabilen bir değer için tipi 'T?' olmalı",
            )
            ic = ty

        then_env = env.child()
        then_env.define(stmt.bag_ad, ic, False)
        self.check_block(stmt.then, then_env)

        # `else` dalında ad yok: orada değer zaten none.
        if isinstance(stmt.otherwise, A.Block):
            self.check_block(stmt.otherwise, env.child())
        elif isinstance(stmt.otherwise, A.If):
            self.check_if(stmt.otherwise, env.child())

    def check_for(self, stmt: A.For, env: Env) -> None:
        it_ty = self.check_expr(stmt.iterable, env)
        body_env = env.child()

        if isinstance(it_ty, RangeT):
            stmt.kind = "range"
            if len(stmt.names) == 2:
                self.error(
                    "aralık üzerinde tek değişken kullanılır",
                    stmt.span,
                    hint="aralık zaten sayı üretiyor: for i in 1..=10 { ... }",
                )
            self.bind_loop_names(stmt, [it_ty.elem], body_env)
        elif isinstance(it_ty, ListT):
            # İkinci değişken istenirse sıra numarasıdır; elle sayaç tutmak
            # gerekmesin diye.
            if len(stmt.names) == 2:
                stmt.kind = "list_indeksli"
                self.bind_loop_names(stmt, [INT, it_ty.elem], body_env)
            else:
                stmt.kind = "list"
                self.bind_loop_names(stmt, [it_ty.elem], body_env)
        elif isinstance(it_ty, MapT):
            stmt.kind = "map"
            if len(stmt.names) == 1:
                self.error(
                    "eşleme üzerinde dönerken iki değişken gerekir",
                    stmt.span,
                    hint="örnek: for (anahtar, deger) in sozluk { ... }",
                )
                body_env.define(stmt.names[0], it_ty.key, False)
            else:
                self.bind_loop_names(stmt, [it_ty.key, it_ty.value], body_env)
        elif it_ty == STRING:
            if len(stmt.names) == 2:
                stmt.kind = "string_indeksli"
                self.bind_loop_names(stmt, [INT, STRING], body_env)
            else:
                stmt.kind = "string"
                self.bind_loop_names(stmt, [STRING], body_env)
        elif isinstance(it_ty, AnyT):
            stmt.kind = "list"
            for name in stmt.names:
                body_env.define(name, ANY, False)
        else:
            self.error(
                f"'{it_ty}' üzerinde döngü kurulamaz",
                stmt.iterable.span,
                hint="aralık, liste, eşleme ya da metin gerekir",
            )
            stmt.kind = "list"
            for name in stmt.names:
                body_env.define(name, ANY, False)

        self.loop_depth += 1
        self.check_block(stmt.body, body_env)
        self.loop_depth -= 1

    def bind_loop_names(self, stmt: A.For, types: list[Type], env: Env) -> None:
        if len(stmt.names) != len(types):
            self.error(
                f"{len(types)} döngü değişkeni bekleniyordu, {len(stmt.names)} verildi",
                stmt.span,
            )
        for name, ty in zip(stmt.names, types):
            env.define(name, ty, False)

    # ------------------------------------------------------------------ match
    def kol_kosulu(self, arm, arm_env: Env, kapsiyor: bool) -> bool:
        """Koşullu kolun koşulunu denetler; kapsama hakkını düşürür.

        `x if x > 3 ->` deseni her değeri tutar ama koşul tutmayabilir;
        bu yüzden match'i tamamlamış sayılmaz. Yoksa derleyici eksik
        dalları görmezden gelirdi.
        """
        if arm.guard is None:
            return kapsiyor
        got = self.check_expr(arm.guard, arm_env, BOOL)
        if not assignable(BOOL, got):
            self.error(
                f"kol koşulu 'Bool' olmalı, '{got}' bulundu",
                arm.guard.span,
            )
        return False

    def check_match(self, stmt: A.Match, env: Env) -> None:
        subject = self.check_expr(stmt.subject, env)
        base = unwrap_optional(subject)
        covered: set[str] = set()
        has_catch_all = False

        for arm in stmt.arms:
            arm_env = env.child()
            kapsiyor = self.check_pattern(arm.pattern, subject, arm_env, covered)
            if self.kol_kosulu(arm, arm_env, kapsiyor):
                has_catch_all = True
            if isinstance(arm.body, A.Block):
                self.check_block(arm.body, arm_env)
            elif isinstance(arm.body, A.Stmt):
                self.check_stmt(arm.body, arm_env)
            else:  # pragma: no cover
                self.check_expr(arm.body, arm_env)

        if isinstance(base, EnumT) and not has_catch_all:
            missing = [v for v in base.variants if v not in covered]
            if missing:
                self.error(
                    f"match tam değil; kapsanmayan varyantlar: {', '.join(missing)}",
                    stmt.span,
                    hint="eksik dalları ekle ya da '_ -> ...' dalı koy",
                )
        if isinstance(subject, OptT) and not has_catch_all and "none" not in covered:
            self.error(
                "opsiyonel değer üzerinde match 'none' dalını içermeli",
                stmt.span,
                hint="'none -> ...' ya da '_ -> ...' ekle",
            )

    def check_pattern(self, pat: A.Pattern, subject: Type, env: Env, covered: set[str]) -> bool:
        """Deseni denetler; joker (her şeyi kapsayan) desense True döner."""
        if isinstance(pat, A.WildcardPat):
            return True

        if isinstance(pat, A.BindPat):
            base = unwrap_optional(subject)
            # Yükü olmayan varyant adı, bağlama değil desen sayılır.
            if isinstance(base, EnumT) and pat.name in base.variants:
                if base.variants[pat.name]:
                    self.error(
                        f"'{pat.name}' varyantı {len(base.variants[pat.name])} değer taşır",
                        pat.span,
                    )
                covered.add(pat.name)
                pat.__dict__["as_enum"] = base.name
                return False
            env.define(pat.name, subject, False)
            return True

        if isinstance(pat, A.LiteralPat):
            got = self.check_expr(pat.value, env, subject)
            if isinstance(got, NoneT):
                covered.add("none")
                return False
            if not assignable(unwrap_optional(subject), got) and not assignable(subject, got):
                self.error(
                    f"desen tipi '{got}', eşlenen değer '{subject}'",
                    pat.span,
                )
            return False

        if isinstance(pat, A.RangePat):
            # Aralık uçları eşlenen değerle aynı tipte olmalı ve
            # karşılaştırılabilir olmalı: sayı ya da metin.
            taban = unwrap_optional(subject)
            for uc in (pat.low, pat.high):
                got = self.check_expr(uc, env, taban)
                if not assignable(taban, got):
                    self.error(
                        f"aralık ucunun tipi '{got}', eşlenen değer '{subject}'",
                        uc.span,
                    )
                elif taban not in ORDERED and not isinstance(taban, AnyT):
                    self.error(
                        f"'{taban}' aralık deseninde kullanılamaz",
                        pat.span,
                        hint="aralık yalnız sayı ve metin için geçerli",
                    )
            return False

        if isinstance(pat, A.EnumPat):
            base = unwrap_optional(subject)
            if not isinstance(base, EnumT):
                self.error(f"'{subject}' bir enum değil; varyant deseni kullanılamaz", pat.span)
                return False
            if pat.enum_name is not None and pat.enum_name != base.name:
                self.error(
                    f"'{base.name}' bekleniyordu, '{pat.enum_name}' deseni verildi",
                    pat.span,
                )
            pat.enum_name = base.name
            if pat.variant not in base.variants:
                self.error(
                    f"'{base.name}' içinde '{pat.variant}' varyantı yok",
                    pat.span,
                    hint=f"var olanlar: {', '.join(base.variants)}",
                )
                return False
            covered.add(pat.variant)
            payload = base.variants[pat.variant]
            if pat.subpatterns and len(pat.subpatterns) != len(payload):
                self.error(
                    f"'{pat.variant}' {len(payload)} değer taşır, "
                    f"{len(pat.subpatterns)} desen verildi",
                    pat.span,
                )
            for sub, ty in zip(pat.subpatterns, payload):
                self.check_pattern(sub, ty, env, set())
            return False

        self.error("bilinmeyen desen", pat.span)  # pragma: no cover
        return False

    # -------------------------------------------------------- akış daraltma
    def apply_narrowing(self, cond: A.Expr, env: Env, positive: bool) -> None:
        """`if x != none` gibi koşullarda değişkenin tipini daraltır."""
        if isinstance(cond, A.Binary) and cond.op in ("!=", "=="):
            null_on_right = isinstance(cond.right, A.NoneLit)
            null_on_left = isinstance(cond.left, A.NoneLit)
            if null_on_right or null_on_left:
                target = cond.left if null_on_right else cond.right
                narrows = (cond.op == "!=") == positive
                if narrows and isinstance(target, A.Ident):
                    binding = env.lookup(target.name)
                    if binding is not None and isinstance(binding.ty, OptT):
                        env.define(target.name, binding.ty.inner, binding.mutable)
        elif isinstance(cond, A.Binary) and cond.op == "&&" and positive:
            self.apply_narrowing(cond.left, env, True)
            self.apply_narrowing(cond.right, env, True)
        elif isinstance(cond, A.Unary) and cond.op == "!":
            self.apply_narrowing(cond.operand, env, not positive)

    # ------------------------------------------------------- dönüş yolu analizi
    def terminates(self, node: object) -> bool:
        """Bu düğüm her yolda `return`/`panic` ile mi bitiyor?"""
        if isinstance(node, A.Block):
            return any(self.terminates(s) for s in node.stmts)
        if isinstance(node, A.Return):
            return True
        if isinstance(node, A.If):
            if node.otherwise is None:
                return False
            return self.terminates(node.then) and self.terminates(node.otherwise)
        if isinstance(node, A.Match):
            return all(self.terminates(arm.body) for arm in node.arms)
        if isinstance(node, A.ExprStmt):
            return isinstance(node.expr.ty, NeverT)
        if isinstance(node, A.While):
            # `while true { ... }` içinde break yoksa sonrası ölü koddur
            return isinstance(node.cond, A.BoolLit) and node.cond.value and not self.has_break(node.body)
        return False

    def has_break(self, node: object) -> bool:
        if isinstance(node, A.Break):
            return True
        if isinstance(node, A.Block):
            return any(self.has_break(s) for s in node.stmts)
        if isinstance(node, A.If):
            return self.has_break(node.then) or (node.otherwise is not None and self.has_break(node.otherwise))
        if isinstance(node, A.Match):
            return any(self.has_break(arm.body) for arm in node.arms)
        return False

    # --------------------------------------------------------------- ifadeler
    def expect_bool(self, ty: Type, span, what: str) -> None:
        if not assignable(BOOL, ty):
            self.error(f"{what} 'Bool' olmalı, '{ty}' bulundu", span)

    def check_expr(self, node: A.Expr, env: Env, expected: Type | None = None) -> Type:
        # `Any` beklentisi "bilgi yok" demektir; sonucu Any'ye zorlamamalı.
        # (Kısmen çözülmüş generic ipuçlarında Any yer tutucu olarak kullanılır.)
        if isinstance(expected, AnyT):
            expected = None
        ty = self._check_expr(node, env, expected)
        node.ty = ty
        return ty

    def _check_expr(self, node: A.Expr, env: Env, expected: Type | None) -> Type:
        if isinstance(node, A.IntLit):
            # Beklenen tip Float ise sayı literali Float sayılır (yalnızca literal).
            if expected is not None and unwrap_optional(expected) == FLOAT:
                return FLOAT
            return INT

        if isinstance(node, A.FloatLit):
            return FLOAT

        if isinstance(node, A.BoolLit):
            return BOOL

        if isinstance(node, A.NoneLit):
            if expected is not None and isinstance(expected, OptT):
                return expected
            return NONE

        if isinstance(node, A.StringLit):
            for part in node.parts:
                if isinstance(part, A.Expr):
                    self.check_expr(part, env)
            return STRING

        if isinstance(node, A.SelfExpr):
            if self.self_type is None:
                self.error("'self' yalnızca metot içinde kullanılabilir", node.span)
                return ANY
            return self.self_type

        if isinstance(node, A.Ident):
            binding = env.lookup(node.name)
            if binding is None:
                # Enum adı yazılmadan kullanılan varyant: `Cizgi`
                sahip = self.varyant_sahibi_bul(node.name, expected, node.span)
                if sahip is not None:
                    return self.varyant_tipi(node, sahip, node.name, expected)
                if node.name in self.structs or node.name in self.enums:
                    self.error(
                        f"'{node.name}' bir tip adı, değer değil",
                        node.span,
                        hint=f"örnek: {node.name} {{ ... }}" if node.name in self.structs
                        else f"örnek: {node.name}.Varyant",
                    )
                    return ANY
                if node.name in BUILTIN_NAMES:
                    self.error(f"yerleşik '{node.name}' yalnızca çağrılabilir", node.span)
                    return ANY
                self.error(f"tanımsız isim: '{node.name}'", node.span)
                return ANY
            return binding.ty

        if isinstance(node, A.TupleLit):
            return self.check_tuple_lit(node, env, expected)

        if isinstance(node, A.ListLit):
            return self.check_list_lit(node, env, expected)

        if isinstance(node, A.MapLit):
            return self.check_map_lit(node, env, expected)

        if isinstance(node, A.StructLit):
            return self.check_struct_lit(node, env, expected)

        if isinstance(node, A.Unary):
            return self.check_unary(node, env)

        if isinstance(node, A.Binary):
            return self.check_binary(node, env, expected)

        if isinstance(node, A.RangeExpr):
            start = self.check_expr(node.start, env, INT)
            end = self.check_expr(node.end, env, start if start == FLOAT else INT)
            if start != INT or end != INT:
                self.error("aralık sınırları 'Int' olmalı", node.span)
            return RangeT(INT)

        if isinstance(node, A.Propagate):
            return self.check_propagate(node, env)

        if isinstance(node, A.Unwrap):
            inner = self.check_expr(node.operand, env)
            if isinstance(inner, OptT):
                return inner.inner
            if isinstance(inner, (AnyT, NoneT)):
                return ANY
            # Değer zaten opsiyonel değilse `!` bir şey yapmaz. Bu genelde
            # akış daraltmasının işini görünmez biçimde yapmasından olur
            # (`if x != none { x!.f() }`); hata saymak kafa karıştırır.
            node.__dict__["gereksiz"] = True
            return inner

        if isinstance(node, A.Index):
            return self.check_index(node, env)

        if isinstance(node, A.FieldAccess):
            return self.check_field(node, env, expected)

        if isinstance(node, A.Call):
            return self.check_call(node, env, expected)

        if isinstance(node, A.Lambda):
            return self.check_lambda(node, env, expected)

        if isinstance(node, A.IfExpr):
            return self.check_if_expr(node, env, expected)

        if isinstance(node, A.BlockExpr):
            return self.check_block_expr(node, env, expected)

        if isinstance(node, A.MatchExpr):
            return self.check_match_expr(node, env, expected)

        self.error(f"denetlenemeyen ifade: {type(node).__name__}", node.span)  # pragma: no cover
        return ANY

    def check_tuple_lit(self, node: A.TupleLit, env: Env,
                        expected: Type | None) -> Type:
        """`(a, b)` — her öğe kendi tipini korur.

        Beklenen tip biliniyorsa öğelere ipucu olarak geçer; böylece
        `let t: (Int, Float) = (1, 2)` içindeki 2 float olur.
        """
        hedef = unwrap_optional(expected) if expected is not None else None
        ipuclari = hedef.elems if isinstance(hedef, TupleT) else ()
        tipler = []
        for i, oge in enumerate(node.items):
            ipucu = ipuclari[i] if i < len(ipuclari) else None
            tipler.append(self.check_expr(oge, env, ipucu))
        if len(tipler) > 4:
            self.warn(
                f"{len(tipler)} öğeli tuple okunması zor",
                node.span,
                hint="alanların adı anlam taşıyorsa struct kullan",
            )
        return TupleT(tuple(tipler))

    def check_list_lit(self, node: A.ListLit, env: Env, expected: Type | None) -> Type:
        hint = None
        if expected is not None and isinstance(unwrap_optional(expected), ListT):
            hint = unwrap_optional(expected).elem
        # `Any` ipucu "bilgi yok" demektir; sonucu Any'ye zorlamamalı.
        if isinstance(hint, AnyT):
            hint = None

        if not node.items:
            if hint is None:
                self.error(
                    "boş listenin eleman tipi çıkarılamıyor",
                    node.span,
                    hint="tipi yaz: let x: [Int] = []",
                )
                return ListT(ANY)
            return ListT(hint)

        # Eleman tipi yazılmışsa her eleman ona uymalıdır; elemanların
        # birbirine uyması gerekmez. `[Yazdirilabilir]` listesine farklı
        # tipler konabilmesi buna bağlı.
        if hint is not None:
            for item in node.items:
                got = self.check_expr(item, env, hint)
                if not assignable(hint, got):
                    self.error(
                        f"liste elemanı '{hint}' olmalı, '{got}' bulundu",
                        item.span,
                    )
            return ListT(hint)

        elem = self.check_expr(node.items[0], env, hint)
        for item in node.items[1:]:
            got = self.check_expr(item, env, hint or elem)
            merged = common_type(elem, got)
            if merged is None:
                self.error(
                    f"liste elemanları aynı tipte olmalı: '{elem}' ve '{got}'",
                    item.span,
                )
            else:
                elem = merged
        return ListT(hint if hint is not None and assignable(hint, elem) else elem)

    def check_map_lit(self, node: A.MapLit, env: Env, expected: Type | None) -> Type:
        base = unwrap_optional(expected) if expected else None
        key_hint = base.key if isinstance(base, MapT) else None
        val_hint = base.value if isinstance(base, MapT) else None
        if isinstance(key_hint, AnyT):
            key_hint = None
        if isinstance(val_hint, AnyT):
            val_hint = None

        if not node.entries:
            if key_hint is None or val_hint is None:
                self.error(
                    "boş eşlemenin tipi çıkarılamıyor",
                    node.span,
                    hint="tipi yaz: let m: {String: Int} = {}",
                )
                return MapT(ANY, ANY)
            return MapT(key_hint, val_hint)

        key_ty = self.check_expr(node.entries[0][0], env, key_hint)
        val_ty = self.check_expr(node.entries[0][1], env, val_hint)
        for k, v in node.entries[1:]:
            gk = self.check_expr(k, env, key_hint or key_ty)
            gv = self.check_expr(v, env, val_hint or val_ty)
            if not assignable(key_ty, gk):
                self.error(f"eşleme anahtarları aynı tipte olmalı: '{key_ty}' ve '{gk}'", k.span)
            merged = common_type(val_ty, gv)
            if merged is None:
                self.error(f"eşleme değerleri aynı tipte olmalı: '{val_ty}' ve '{gv}'", v.span)
            else:
                val_ty = merged
        return MapT(key_hint or key_ty, val_hint if val_hint is not None else val_ty)

    def check_struct_lit(self, node: A.StructLit, env: Env,
                         expected: Type | None = None) -> Type:
        sablon = self.structs.get(node.type_name)
        if sablon is not None and sablon.type_params:
            return self.check_generic_struct_lit(node, env, sablon, expected)
        st = sablon
        if st is None:
            if node.type_name in self.enums:
                self.error(
                    f"'{node.type_name}' bir enum; '{{...}}' ile oluşturulamaz",
                    node.span,
                    hint=f"örnek: {node.type_name}.Varyant",
                )
            else:
                self.error(f"bilinmeyen struct: '{node.type_name}'", node.span)
            for _, value in node.fields:
                self.check_expr(value, env)
            return ANY

        given: set[str] = set()
        for name, value in node.fields:
            if name not in st.fields:
                self.error(
                    f"'{st.name}' tipinde '{name}' alanı yok",
                    value.span,
                    hint=f"var olan alanlar: {', '.join(st.fields) or 'yok'}",
                )
                self.check_expr(value, env)
                continue
            if name in given:
                self.error(f"'{name}' alanı iki kez verildi", value.span)
            given.add(name)
            got = self.check_expr(value, env, st.fields[name])
            if not assignable(st.fields[name], got):
                self.error(
                    f"'{st.name}.{name}': '{st.fields[name]}' bekleniyordu, '{got}' bulundu",
                    value.span,
                )

        self.eksikleri_bildir(node, env, st, given)
        return st

    def check_generic_struct_lit(self, node: A.StructLit, env: Env,
                                 sablon: StructT, expected: Type | None) -> Type:
        """`Kutu<Int> { ... }` ya da `Kutu { ... }` (tip çıkarımıyla)."""
        params = sablon.type_params

        # 1) Açıkça yazılmışsa doğrudan onu kullan.
        if node.type_args:
            args = tuple(self.resolve_type(a) for a in node.type_args)
            if len(args) != len(params):
                self.error(
                    f"'{sablon.name}' {len(params)} tip argümanı bekler, "
                    f"{len(args)} verildi",
                    node.span,
                )
                args = (args + (ANY,) * len(params))[:len(params)]
            return self.struct_alanlarini_dogrula(node, env, uygula_struct(sablon, args))

        # 2) Beklenen tip aynı struct ise oradan al.
        hedef = unwrap_optional(expected) if expected is not None else None
        if isinstance(hedef, StructT) and hedef.name == sablon.name and hedef.type_args:
            return self.struct_alanlarini_dogrula(node, env, hedef)

        # 3) Verilen alan değerlerinden çıkar.
        esleme: dict[str, Type] = {}
        for ad, deger in node.fields:
            if ad not in sablon.fields:
                continue
            beklenen_alan = sablon.fields[ad]
            ipucu = subst(beklenen_alan, esleme)
            got = self.check_expr(deger, env, None if tipdegiskeni_var_mi(ipucu) else ipucu)
            birlestir(beklenen_alan, got, esleme)

        eksik = [p for p in params if p not in esleme]
        if eksik:
            self.error(
                f"'{sablon.name}' için tip argümanı çıkarılamadı: {', '.join(eksik)}",
                node.span,
                hint=f"açıkça yaz: {sablon.name}<{', '.join(params)}> {{ ... }}",
            )
            for p in eksik:
                esleme[p] = ANY

        args = tuple(esleme[p] for p in params)
        return self.struct_alanlarini_dogrula(node, env, uygula_struct(sablon, args),
                                              yeniden_denetleme=False)

    def struct_alanlarini_dogrula(self, node: A.StructLit, env: Env, st: StructT,
                                  yeniden_denetleme: bool = True) -> Type:
        """Alanların verilip verilmediğini ve tiplerini doğrular."""
        given: set[str] = set()
        for ad, deger in node.fields:
            if ad not in st.fields:
                self.error(
                    f"'{st.name}' tipinde '{ad}' alanı yok",
                    deger.span,
                    hint=f"var olan alanlar: {', '.join(st.fields) or 'yok'}",
                )
                if yeniden_denetleme:
                    self.check_expr(deger, env)
                continue
            if ad in given:
                self.error(f"'{ad}' alanı iki kez verildi", deger.span)
            given.add(ad)
            if yeniden_denetleme:
                got = self.check_expr(deger, env, st.fields[ad])
            else:
                got = deger.ty if deger.ty is not None else ANY
            if not assignable(st.fields[ad], got):
                self.error(
                    f"'{st.name}.{ad}': '{st.fields[ad]}' bekleniyordu, "
                    f"'{got}' bulundu",
                    deger.span,
                )

        self.eksikleri_bildir(node, env, st, given)
        return st

    def eksikleri_bildir(self, node: A.StructLit, env: Env, st: StructT,
                         verilen: set) -> None:
        """Yazılmayan alanları varsayılanlarıyla doldurur, kalanı hata sayar.

        Varsayılan ifadenin kopyası konur: aynı düğümü iki struct literaline
        koymak tip bilgisini paylaştırır, ikinci kullanımda yanlış tip
        çıkarımına yol açardı.
        """
        varsayilanlar = self.struct_varsayilanlari.get(st.name, {})
        eksik = []
        for f in st.fields:
            if f in verilen:
                continue
            if f in varsayilanlar:
                kopya = copy.deepcopy(varsayilanlar[f])
                got = self.check_expr(kopya, env, st.fields[f])
                if not assignable(st.fields[f], got):
                    self.error(
                        f"'{st.name}.{f}' varsayılanı: '{st.fields[f]}' "
                        f"bekleniyordu, '{got}' bulundu",
                        node.span,
                    )
                node.fields.append((f, kopya))
                continue
            eksik.append(f)
        if eksik:
            self.error(f"'{st.name}' için eksik alanlar: {', '.join(eksik)}",
                       node.span)

    def check_unary(self, node: A.Unary, env: Env) -> Type:
        if node.op == "!":
            ty = self.check_expr(node.operand, env, BOOL)
            self.expect_bool(ty, node.span, "'!' işlenen")
            return BOOL
        ty = self.check_expr(node.operand, env)
        if ty not in (INT, FLOAT) and not isinstance(ty, AnyT):
            self.error(f"tekli '-' sayı bekler, '{ty}' bulundu", node.span)
            return ANY
        return ty

    def check_binary(self, node: A.Binary, env: Env, expected: Type | None) -> Type:
        if node.op == "??":
            left = self.check_expr(node.left, env, expected if expected and isinstance(expected, OptT) else None)
            if not is_optional(left) and not isinstance(left, AnyT):
                self.error(
                    f"'??' solunda opsiyonel değer olmalı ('{left}' opsiyonel değil)",
                    node.span,
                )
                inner = left
            else:
                inner = unwrap_optional(left)
            with self.yasakta("'??' işlecinin sağında"):
                right = self.check_expr(
                    node.right, env,
                    inner if not isinstance(inner, NoneT) else expected)
            merged = common_type(inner, right)
            if merged is None:
                self.error(
                    f"'??' iki tarafı uyuşmuyor: '{inner}' ve '{right}'",
                    node.span,
                )
                return inner
            return merged

        if node.op in ("&&", "||"):
            left = self.check_expr(node.left, env, BOOL)
            self.expect_bool(left, node.left.span, f"'{node.op}' solu")
            right_env = env.child()
            if node.op == "&&":
                self.apply_narrowing(node.left, right_env, True)
            with self.yasakta(f"'{node.op}' işlecinin sağında"):
                right = self.check_expr(node.right, right_env, BOOL)
            self.expect_bool(right, node.right.span, f"'{node.op}' sağı")
            return BOOL

        left = self.check_expr(node.left, env)
        right = self.check_expr(node.right, env, left if left in (INT, FLOAT, STRING) else None)
        return self.binary_result(node.op, left, right, node.span)

    def binary_result(self, op: str, left: Type, right: Type, span) -> Type:
        if isinstance(left, AnyT) or isinstance(right, AnyT):
            return ANY

        # Int ve Float birlikte kullanılabilir; sonuç Float'a yükselir.
        # Yükseltme kayıpsızdır, bu yüzden tip güvenliğini bozmaz.
        sayisal = left in NUMERIC and right in NUMERIC
        sayi_sonucu = FLOAT if FLOAT in (left, right) else INT

        if op in ("==", "!="):
            if not sayisal and common_type(left, right) is None:
                self.error(
                    f"'{left}' ile '{right}' karşılaştırılamaz",
                    span,
                    hint="karşılaştırılan iki değer aynı tipte olmalı",
                )
            return BOOL

        if op in ("<", "<=", ">", ">="):
            if not sayisal:
                if left != right:
                    self.error(f"'{left}' ile '{right}' sıralanamaz", span)
                elif left not in ORDERED:
                    self.error(f"'{left}' sıralanabilir değil", span,
                               hint="Int, Float ya da String olmalı")
            return BOOL

        if op == "+":
            # Bir taraf metinse sonuç metindir; diğer taraf otomatik yazıya
            # dökülür. Böylece `"yaş: " + 25` için str(...) gerekmez.
            if left == STRING or right == STRING:
                return STRING
            if isinstance(left, ListT) and left == right:
                return left
            if sayisal:
                return sayi_sonucu
            self.error(
                f"'+' işlemi '{left}' ile '{right}' arasında tanımlı değil",
                span,
            )
            return left if left in NUMERIC else ANY

        if op in ("-", "*", "/", "%"):
            if sayisal:
                return sayi_sonucu
            self.error(
                f"'{op}' işlemi '{left}' ile '{right}' arasında tanımlı değil",
                span,
                hint="bu işlem yalnızca sayılar arasında yapılabilir",
            )
            return left if left in NUMERIC else ANY

        self.error(f"bilinmeyen operatör: '{op}'", span)  # pragma: no cover
        return ANY

    def check_propagate(self, node: A.Propagate, env: Env) -> Type:
        """`ifade?` — none ise fonksiyondan none döner, değilse değeri açar."""
        if self.soru_yasak is not None:
            self.error(
                f"'?' burada kullanılamaz: {self.soru_yasak}",
                node.span,
                hint="değeri önce bir değişkene al: let x = ...?",
            )

        inner = self.check_expr(node.operand, env)
        if isinstance(inner, OptT):
            ic = inner.inner
        elif isinstance(inner, (AnyT, NoneT)):
            ic = ANY
        else:
            self.error(
                f"'?' opsiyonel bir değer bekler, '{inner}' bulundu",
                node.operand.span,
                hint="olmayabilen bir değer için tipi 'T?' olmalı",
            )
            ic = inner

        if not is_optional(self.current_ret) and not isinstance(
                self.current_ret, AnyT):
            self.error(
                "'?' yalnızca opsiyonel döndüren bir fonksiyonda kullanılabilir "
                f"(bu fonksiyon '{self.current_ret}' döndürüyor)",
                node.span,
                hint="dönüş tipini 'T?' yap ya da '??' ile bir varsayılan ver",
            )
        return ic

    def yasakta(self, neden: str):
        """`?` için geçici yasak kapsamı."""
        return _SoruYasagi(self, neden)

    def check_index(self, node: A.Index, env: Env) -> Type:
        obj = self.check_expr(node.obj, env)
        if isinstance(obj, ListT):
            self.check_expr(node.index, env, INT)
            node.__dict__["resolved"] = "list"
            return obj.elem
        if isinstance(obj, MapT):
            self.check_expr(node.index, env, obj.key)
            node.__dict__["resolved"] = "map"
            return OptT(obj.value) if not isinstance(obj.value, OptT) else obj.value
        if obj == STRING:
            self.check_expr(node.index, env, INT)
            node.__dict__["resolved"] = "string"
            return STRING
        if isinstance(obj, AnyT):
            self.check_expr(node.index, env)
            node.__dict__["resolved"] = "list"
            return ANY
        if isinstance(obj, OptT):
            self.error(
                f"'{obj}' opsiyonel; önce açılmalı",
                node.span,
                hint="'x!' ya da 'x ?? varsayilan' kullan",
            )
            return ANY
        self.error(f"'{obj}' dizinlenemez", node.span)
        return ANY

    def varyant_tipi(self, node: A.Expr, enum_adi: str, varyant: str,
                     beklenen: Type | None) -> Type:
        """Bir enum varyantına başvurunun tipi.

        Yüklü varyant bir yapıcı işlevdir (`FnT`), yüksüz varyant doğrudan
        değerdir. `node` üzerine arka ucun okuduğu işaretler bırakılır.
        """
        sablon = self.enums[enum_adi]
        node.__dict__["resolved"] = "enum_variant"
        node.__dict__["enum_name"] = enum_adi

        if not sablon.type_params:
            payload = sablon.variants[varyant]
            return FnT(payload, sablon) if payload else sablon

        # Generic enum: beklenen tip biliniyorsa doğrudan uygula.
        hedef = unwrap_optional(beklenen) if beklenen is not None else None
        if isinstance(hedef, EnumT) and hedef.name == enum_adi and hedef.type_args:
            payload = hedef.variants[varyant]
            return FnT(payload, hedef) if payload else hedef

        # Bilinmiyorsa tip değişkenleriyle bırak; çağrı yerinde çıkarılır.
        ornek = self.sablon_ornegi(sablon)
        payload = ornek.variants[varyant]
        if payload:
            return FnT(payload, ornek)
        acikta = tipdegiskenleri(ornek) - set(self.tip_degiskenleri)
        if not acikta:
            return ornek
        self.error(
            f"'{enum_adi}.{varyant}' için tip argümanı çıkarılamıyor",
            node.span,
            hint=f"tipi yaz, örnek: let x: {enum_adi}"
                 f"<{', '.join(sablon.type_params)}> = {enum_adi}.{varyant}",
        )
        return ANY

    def varyant_sahibi_bul(self, ad: str, beklenen: Type | None,
                              span) -> str | None:
        """`Metin("a")` gibi enum adı yazılmadan kullanılan varyantın sahibi.

        Beklenen tip bir enum'a işaret ediyorsa o kazanır; yoksa varyant adı
        yalnızca tek bir enum'da geçiyorsa o seçilir. Birden çok enum aynı adı
        taşıyorsa karar programcınındır ve hata verilir.
        """
        adaylar = self.varyant_sahipleri.get(ad)
        if not adaylar:
            return None

        hedef = unwrap_optional(beklenen) if beklenen is not None else None
        if isinstance(hedef, EnumT) and hedef.name in adaylar:
            return hedef.name

        if len(adaylar) == 1:
            return adaylar[0]

        self.error(
            f"'{ad}' varyantı birden çok enum'da var: {', '.join(sorted(adaylar))}",
            span,
            hint=f"enum adını yaz, örnek: {sorted(adaylar)[0]}.{ad}",
        )
        return None

    def check_field(self, node: A.FieldAccess, env: Env,
                    beklenen: Type | None = None) -> Type:
        # Enum varyantı: `Sonuc.Tamam` / `Sonuc.Bos`
        if isinstance(node.obj, A.Ident) and env.lookup(node.obj.name) is None:
            name = node.obj.name
            if name in self.enums:
                if node.name not in self.enums[name].variants:
                    self.error(
                        f"'{name}' içinde '{node.name}' varyantı yok",
                        node.span,
                        hint=f"var olanlar: {', '.join(self.enums[name].variants)}",
                    )
                    return ANY
                return self.varyant_tipi(node, name, node.name, beklenen)

        obj = self.check_expr(node.obj, env)

        if node.safe:
            if not is_optional(obj) and not isinstance(obj, AnyT):
                self.error(
                    f"'?.' opsiyonel değer bekler ('{obj}' opsiyonel değil)",
                    node.span,
                    hint="düz '.' kullan",
                )
            base = unwrap_optional(obj)
            result = self.member_type(base, node, env)
            if isinstance(result, FnT):
                return result  # metot; çağrı yerinde sarılır
            return result if isinstance(result, OptT) else OptT(result)

        if isinstance(obj, OptT):
            self.error(
                f"'{obj}' opsiyonel; alanına doğrudan erişilemez",
                node.span,
                hint="'?.' kullan ya da '!' ile aç",
            )
            return ANY

        return self.member_type(obj, node, env)

    def member_type(self, base: Type, node: A.FieldAccess, env: Env) -> Type:
        if isinstance(base, AnyT):
            node.__dict__["resolved"] = "field"
            return ANY

        if isinstance(base, TupleT):
            # Tuple öğeleri sırayla okunur: `t.0`, `t.1`.
            if not node.name.isdigit():
                self.error(
                    f"tuple'ın '{node.name}' diye bir alanı yok",
                    node.span,
                    hint=f"öğeler sırayla okunur: .0 – .{len(base.elems) - 1}",
                )
                return ANY
            sira = int(node.name)
            if sira >= len(base.elems):
                self.error(
                    f"tuple'ın {len(base.elems)} öğesi var; .{sira} yok",
                    node.span,
                    hint=f"geçerli olanlar: .0 – .{len(base.elems) - 1}",
                )
                return ANY
            node.__dict__["resolved"] = "tuple"
            return base.elems[sira]

        # `fn f<T: Yazdirilabilir>(x: T)` içinde x.yaz() çağrılabilir.
        if isinstance(base, TypeVar):
            for arayuz_adi in self.tip_sinirlari.get(base.name, []):
                arayuz = self.interfaces.get(arayuz_adi)
                if arayuz is not None and node.name in arayuz.methods:
                    node.__dict__["resolved"] = "method"
                    return arayuz.methods[node.name]
            sinirlar = self.tip_sinirlari.get(base.name, [])
            self.error(
                f"'{base.name}' tip parametresinde '{node.name}' yok",
                node.span,
                hint=(f"'{base.name}' yalnızca şu arayüzlerin metotlarını "
                      f"sunuyor: {', '.join(sinirlar)}") if sinirlar else
                     (f"tip parametresine sınır koy: <{base.name}: Arayuz>"),
            )
            return ANY

        if isinstance(base, StructT):
            if node.name in base.fields:
                node.__dict__["resolved"] = "field"
                return base.fields[node.name]
            if node.name in base.methods:
                node.__dict__["resolved"] = "method"
                return base.methods[node.name]
            self.error(
                f"'{base.name}' tipinde '{node.name}' yok",
                node.span,
                hint=f"alanlar: {', '.join(base.fields) or 'yok'}; "
                     f"metotlar: {', '.join(base.methods) or 'yok'}",
            )
            return ANY

        if isinstance(base, InterfaceT):
            if node.name in base.methods:
                node.__dict__["resolved"] = "method"
                return base.methods[node.name]
            self.error(
                f"'{base.name}' arayüzünde '{node.name}' yok",
                node.span,
                hint=f"arayüzün metotları: {', '.join(base.methods) or 'yok'}",
            )
            return ANY

        if isinstance(base, EnumT):
            if node.name in base.methods:
                node.__dict__["resolved"] = "method"
                return base.methods[node.name]
            self.error(
                f"'{base.name}' tipinde '{node.name}' metodu yok",
                node.span,
                hint=f"metotlar: {', '.join(base.methods) or 'yok'}",
            )
            return ANY

        sig = builtin_method(base, node.name)
        if sig is not None:
            node.__dict__["resolved"] = "builtin_method"
            return sig

        self.error(
            f"'{base}' tipinde '{node.name}' yok",
            node.span,
            hint=_member_hint(base),
        )
        return ANY

    # ------------------------------------------------------------- çağrılar
    def check_call(self, node: A.Call, env: Env, expected: Type | None) -> Type:
        callee = node.callee

        # 1) yerleşik serbest fonksiyonlar
        if isinstance(callee, A.Ident) and env.lookup(callee.name) is None \
                and callee.name in BUILTIN_NAMES:
            node.__dict__["resolved"] = "builtin"
            return self.check_builtin(node, callee.name, env)

        # 2) struct/enum tip adının doğrudan çağrılması — sık yapılan hata
        if isinstance(callee, A.Ident) and env.lookup(callee.name) is None:
            if callee.name in self.structs:
                self.error(
                    f"'{callee.name}' bir struct; çağrılamaz",
                    node.span,
                    hint=f"örnek: {callee.name} {{ alan: deger }}",
                )
                for a in node.args:
                    self.check_expr(a, env)
                return self.structs[callee.name]

        if isinstance(callee, A.FieldAccess):
            fn_ty = self.check_field(callee, env, expected)
            callee.ty = fn_ty
        elif isinstance(callee, A.Ident) and env.lookup(callee.name) is None                 and callee.name not in self.functions:
            # Enum adı yazılmadan çağrılan varyant: `Metin("a")`
            sahip = self.varyant_sahibi_bul(callee.name, expected, callee.span)
            if sahip is None:
                fn_ty = self.check_expr(callee, env)
            else:
                fn_ty = self.varyant_tipi(callee, sahip, callee.name, expected)
                callee.ty = fn_ty
        else:
            fn_ty = self.check_expr(callee, env)

        if isinstance(fn_ty, AnyT):
            for a in node.args:
                self.check_expr(a, env)
            return ANY

        if not isinstance(fn_ty, FnT):
            self.error(f"'{fn_ty}' çağrılabilir değil", node.span)
            for a in node.args:
                self.check_expr(a, env)
            return ANY

        # `map`/`filter`/`reduce` dönüş tipi lambdadan çıkarılır — tablo yetmez.
        if isinstance(callee, A.FieldAccess) \
                and callee.__dict__.get("resolved") == "builtin_method" \
                and callee.name in ("map", "filter", "reduce"):
            node.__dict__["resolved"] = "builtin_method"
            result = self.check_collection_method(node, callee, env)
            if result is not None:
                return OptT(result) if callee.safe and not isinstance(result, OptT) else result

        if isinstance(callee, A.FieldAccess):
            node.__dict__["resolved"] = callee.__dict__.get("resolved", "call")
            if callee.__dict__.get("resolved") == "enum_variant":
                node.__dict__["enum_name"] = callee.__dict__.get("enum_name")
                node.__dict__["variant"] = callee.name
        elif isinstance(callee, A.Ident):
            if callee.__dict__.get("resolved") == "enum_variant":
                node.__dict__["resolved"] = "enum_variant"
                node.__dict__["enum_name"] = callee.__dict__["enum_name"]
                node.__dict__["variant"] = callee.name
            else:
                node.__dict__["resolved"] = "func"

        # İmzada tip değişkeni varsa (generic fonksiyon ya da generic enum
        # yapıcısı) tip argümanları çıkarılır.
        if any(tipdegiskeni_var_mi(p) for p in fn_ty.params) or \
                tipdegiskeni_var_mi(fn_ty.ret):
            ret = self.generic_cagri_coz(node, fn_ty, env, expected)
            if isinstance(callee, A.FieldAccess) and callee.safe:
                return ret if isinstance(ret, OptT) else OptT(ret)
            return ret

        self.check_args(node, fn_ty, env)

        # `?.metot()` zinciri sonucu opsiyoneldir
        if isinstance(callee, A.FieldAccess) and callee.safe:
            ret = fn_ty.ret
            return ret if isinstance(ret, OptT) else OptT(ret)
        return fn_ty.ret

    def check_block_expr(self, node: A.BlockExpr, env: Env,
                         expected: Type | None) -> Type:
        """Değer üreten blok: son deyim bir ifade olmalı, değeri odur."""
        # Blok ifadesi hemen çağrılan bir işleve derlenir; oradan dönmek
        # dış fonksiyondan dönmek olmaz.
        yasak = self.yasakta("blok ifadesinin içinde")
        yasak.__enter__()
        try:
            return self._check_block_expr(node, env, expected)
        finally:
            yasak.__exit__(None, None, None)

    def _check_block_expr(self, node: A.BlockExpr, env: Env,
                          expected: Type | None) -> Type:
        inner = env.child()
        block = node.block
        if not block.stmts:
            self.error("bu blok bir değer üretmeli", node.span,
                       hint="son satıra bir değer yaz")
            return ANY

        for stmt in block.stmts[:-1]:
            self.check_stmt(stmt, inner)

        son = block.stmts[-1]
        if not isinstance(son, A.ExprStmt):
            self.check_stmt(son, inner)
            # `return`/`panic` gibi geri dönmeyen bir son da kabul edilir.
            if self.terminates(son):
                return NEVER
            self.error(
                "bu bloğun son satırı bir değer olmalı",
                son.span,
                hint="atama ya da döngü değil, bir değer yaz",
            )
            return ANY
        return self.check_expr(son.expr, inner, expected)

    def check_if_expr(self, node: A.IfExpr, env: Env, expected: Type | None) -> Type:
        cond = self.check_expr(node.cond, env, BOOL)
        self.expect_bool(cond, node.cond.span, "if koşulu")

        with self.yasakta("değer üreten 'if'in dallarında"):
            then_env = env.child()
            self.apply_narrowing(node.cond, then_env, True)
            then_ty = self.check_expr(node.then, then_env, expected)

            else_env = env.child()
            self.apply_narrowing(node.cond, else_env, False)
            else_ty = self.check_expr(
                node.otherwise, else_env, expected or then_ty)

        merged = common_type(then_ty, else_ty)
        if merged is None:
            self.error(
                f"if dallarının tipleri uyuşmuyor: '{then_ty}' ve '{else_ty}'",
                node.span,
                hint="her iki dal da aynı tipte değer üretmeli",
            )
            return then_ty
        return merged

    def check_match_expr(self, node: A.MatchExpr, env: Env, expected: Type | None) -> Type:
        subject = self.check_expr(node.subject, env)
        base = unwrap_optional(subject)
        covered: set[str] = set()
        has_catch_all = False
        result: Type | None = None

        for arm in node.arms:
            arm_env = env.child()
            kapsiyor = self.check_pattern(arm.pattern, subject, arm_env, covered)
            if self.kol_kosulu(arm, arm_env, kapsiyor):
                has_catch_all = True
            with self.yasakta("değer üreten 'match'in kollarında"):
                arm_ty = self.check_expr(arm.body, arm_env, expected or result)
            if result is None:
                result = arm_ty
            else:
                merged = common_type(result, arm_ty)
                if merged is None:
                    self.error(
                        f"match dallarının tipleri uyuşmuyor: '{result}' ve '{arm_ty}'",
                        arm.span,
                        hint="her dal aynı tipte değer üretmeli",
                    )
                else:
                    result = merged

        if isinstance(base, EnumT) and not has_catch_all:
            missing = [v for v in base.variants if v not in covered]
            if missing:
                self.error(
                    f"match tam değil; kapsanmayan varyantlar: {', '.join(missing)}",
                    node.span,
                    hint="eksik dalları ekle ya da '_ -> ...' dalı koy",
                )
        elif not isinstance(base, EnumT) and not has_catch_all:
            self.error(
                "değer üreten match her durumu kapsamalı",
                node.span,
                hint="sona '_ -> ...' dalı ekle",
            )

        return result if result is not None else ANY

    def check_collection_method(self, node: A.Call, callee: A.FieldAccess, env: Env) -> Type | None:
        """`map`, `filter`, `reduce` için tipi lambdanın kendisinden hesaplar."""
        base = unwrap_optional(callee.obj.ty) if callee.obj.ty is not None else None
        if not isinstance(base, ListT):
            return None
        elem = base.elem
        name = callee.name

        if name == "filter":
            if len(node.args) != 1:
                self.error(f"'filter' 1 argüman bekler, {len(node.args)} verildi", node.span)
                return ListT(elem)
            self.check_expr(node.args[0], env, FnT((elem,), BOOL))
            return ListT(elem)

        if name == "map":
            if len(node.args) != 1:
                self.error(f"'map' 1 argüman bekler, {len(node.args)} verildi", node.span)
                return ListT(ANY)
            fn = self.check_expr(node.args[0], env, FnT((elem,), ANY))
            if not isinstance(fn, FnT):
                self.error(f"'map' bir fonksiyon bekler, '{fn}' bulundu", node.args[0].span)
                return ListT(ANY)
            if len(fn.params) != 1 or not assignable(fn.params[0], elem):
                self.error(
                    f"'map' fonksiyonu ({elem}) almalı, '{fn}' verildi",
                    node.args[0].span,
                )
            if is_void(fn.ret):
                self.error("'map' fonksiyonu bir değer döndürmeli", node.args[0].span)
                return ListT(ANY)
            return ListT(fn.ret)

        # reduce(f, baslangic)
        if len(node.args) != 2:
            self.error(f"'reduce' 2 argüman bekler, {len(node.args)} verildi", node.span,
                       hint="örnek: liste.reduce(|toplam, e| toplam + e, 0)")
            return ANY
        init = self.check_expr(node.args[1], env)
        fn = self.check_expr(node.args[0], env, FnT((init, elem), init))
        if not isinstance(fn, FnT):
            self.error(f"'reduce' bir fonksiyon bekler, '{fn}' bulundu", node.args[0].span)
            return init
        if len(fn.params) != 2:
            self.error(f"'reduce' fonksiyonu iki parametre almalı, '{fn}' verildi",
                       node.args[0].span)
        elif not assignable(init, fn.ret):
            self.error(
                f"'reduce' fonksiyonu '{init}' döndürmeli, '{fn.ret}' döndürüyor",
                node.args[0].span,
            )
        return init

    def generic_cagri_coz(self, node: A.Call, fn_ty: FnT, env: Env,
                          expected: Type | None) -> Type:
        """Tip değişkeni içeren bir çağrıyı çözer.

        Hem generic fonksiyonlar (`ilk([1,2])`) hem generic enum yapıcıları
        (`Sonuc.Tamam(5)`) için kullanılır. Tip argümanları önce beklenen
        tipten, sonra verilen argümanlardan çıkarılır.
        """
        esleme: dict[str, Type] = {}

        # Beklenen tip biliniyorsa ondan başla: dönüş tipini oraya oturt.
        if expected is not None and tipdegiskeni_var_mi(fn_ty.ret):
            birlestir(fn_ty.ret, unwrap_optional(expected), esleme)

        if len(node.args) != len(fn_ty.params):
            self.error(
                f"{len(fn_ty.params)} argüman bekleniyordu, {len(node.args)} verildi",
                node.span,
                hint=f"imza: {fn_ty}",
            )

        for arg, param in zip(node.args, fn_ty.params):
            cozulmus = subst(param, esleme)
            if not tipdegiskeni_var_mi(cozulmus):
                ipucu = cozulmus
            elif isinstance(cozulmus, FnT):
                # Lambda beklenen yerde kısmi ipucu da işe yarar: `(T) -> U`
                # içinde T biliniyorsa parametrenin tipi oradan gelir, dönüş
                # tipi ise gövdeden çıkarılır.
                ipucu = tipdegiskenlerini_serbest_birak(
                    cozulmus, set(self.tip_degiskenleri))
            else:
                # Başka yerlerde yer tutucu koymak gerçek tipi siler; ipucusuz
                # bırakıp değerin kendi tipini çıkarmasına izin veririz.
                ipucu = None
            got = self.check_expr(arg, env, ipucu)
            if not birlestir(param, got, esleme):
                self.error(
                    f"argüman tipi uyuşmuyor: '{subst(param, esleme)}' "
                    f"bekleniyordu, '{got}' bulundu",
                    arg.span,
                )
        for extra in node.args[len(fn_ty.params):]:
            self.check_expr(extra, env)

        # Çözülemeyen tip değişkeni kaldıysa bildir. Fonksiyonun kendi tip
        # parametreleri (kapsamdakiler) çözülmüş sayılır: `fn f<U>() -> Kutu<U>`
        # içinde U geçerli bir tiptir.
        cozulmus_params = tuple(subst(p, esleme) for p in fn_ty.params)
        ret = subst(fn_ty.ret, esleme)
        acikta = tipdegiskenleri(ret) - set(self.tip_degiskenleri)
        if acikta:
            self.error(
                f"tip argümanı çıkarılamadı: {', '.join(sorted(acikta))}",
                node.span,
                hint="sonucun tipini yazarak belirt, örnek: let x: Sonuc<Int, String> = ...",
            )
            return ANY

        # Argümanları çözülmüş imzaya göre bir kez daha doğrula.
        for arg, param in zip(node.args, cozulmus_params):
            if arg.ty is not None and not assignable(param, arg.ty):
                self.error(
                    f"argüman tipi uyuşmuyor: '{param}' bekleniyordu, "
                    f"'{arg.ty}' bulundu",
                    arg.span,
                )
        return ret

    def cagri_duzeni(self, node: A.Call, fn_ty: FnT) -> list[int | None]:
        """Her parametre için hangi argümanın verildiği; verilmeyen None.

        Adlandırılmış argümanlar burada sıraya girer, üretilen kodda ad
        kalmaz. Geriye kalan boşlukları varsayılanlar doldurur.
        """
        adlar = getattr(node, "arg_names", None) or [None] * len(node.args)
        duzen: list[int | None] = [None] * len(fn_ty.params)
        sirali = 0
        for i, ad in enumerate(adlar):
            if ad is None:
                # Adsız argüman sıradaki boş yere gider.
                while sirali < len(duzen) and duzen[sirali] is not None:
                    sirali += 1
                if sirali < len(duzen):
                    duzen[sirali] = i
                    sirali += 1
                continue
            if ad not in fn_ty.adlar:
                self.error(
                    f"'{ad}' adında bir parametre yok",
                    node.args[i].span,
                    hint=("parametreler: " + ", ".join(fn_ty.adlar)
                          if fn_ty.adlar else None),
                )
                continue
            yer = fn_ty.adlar.index(ad)
            if duzen[yer] is not None:
                self.error(f"'{ad}' argümanı iki kez verildi", node.args[i].span)
                continue
            duzen[yer] = i
        return duzen

    def check_args(self, node: A.Call, fn_ty: FnT, env: Env) -> None:
        adli_var = any(getattr(node, "arg_names", None) or [])
        # Esnek yol yalnız gerçekten gerekliyse: varsayılanı olan bir
        # parametre ya da adlandırılmış argüman varsa. Yoksa eski, daha
        # net hata mesajlarını veren yol çalışır.
        esnek = fn_ty.en_az() < len(fn_ty.params) or adli_var

        if not esnek:
            if len(node.args) != len(fn_ty.params):
                self.error(
                    f"{len(fn_ty.params)} argüman bekleniyordu, "
                    f"{len(node.args)} verildi",
                    node.span,
                    hint=f"imza: {fn_ty}",
                )
            for arg, param_ty in zip(node.args, fn_ty.params):
                got = self.check_expr(arg, env, param_ty)
                if not assignable(param_ty, got):
                    self.error(
                        f"argüman tipi uyuşmuyor: '{param_ty}' bekleniyordu, "
                        f"'{got}' bulundu",
                        arg.span,
                    )
            for extra in node.args[len(fn_ty.params):]:
                self.check_expr(extra, env)
            return

        if len(node.args) > len(fn_ty.params):
            self.error(
                f"en çok {len(fn_ty.params)} argüman alır, "
                f"{len(node.args)} verildi",
                node.span,
                hint=f"imza: {fn_ty}",
            )

        duzen = self.cagri_duzeni(node, fn_ty)
        parametreler = getattr(fn_ty.decl, "params", None) or []

        # Yerleşmeyen argümanlar da denetlensin; hataları kaybolmasın.
        yerlesen = {i for i in duzen if i is not None}
        for i, arg in enumerate(node.args):
            if i not in yerlesen:
                self.check_expr(arg, env)

        # Çağrı burada normalleşir: argümanlar parametre sırasına dizilir,
        # yazılmayanların yerine varsayılan ifadenin bir kopyası konur.
        # Böylece arka uçlar (JavaScript, bytecode) adlandırılmış argümanı
        # da varsayılanı da hiç bilmeden doğru kodu üretir.
        yeni_args = []
        for yer, param_ty in enumerate(fn_ty.params):
            i = duzen[yer]
            if i is not None:
                arg = node.args[i]
                got = self.check_expr(arg, env, param_ty)
                if not assignable(param_ty, got):
                    self.error(
                        f"argüman tipi uyuşmuyor: '{param_ty}' bekleniyordu, "
                        f"'{got}' bulundu",
                        arg.span,
                    )
                yeni_args.append(arg)
                continue

            varsayilan = (parametreler[yer].default
                          if yer < len(parametreler) else None)
            if varsayilan is None:
                ad = fn_ty.adlar[yer] if yer < len(fn_ty.adlar) else str(yer + 1)
                self.error(
                    f"'{ad}' argümanı verilmedi",
                    node.span,
                    hint=f"imza: {fn_ty}",
                )
                continue
            kopya = copy.deepcopy(varsayilan)
            self.check_expr(kopya, env, param_ty)
            yeni_args.append(kopya)

        if len(yeni_args) == len(fn_ty.params):
            node.args = yeni_args
            node.arg_names = [None] * len(yeni_args)

    def check_lambda(self, node: A.Lambda, env: Env, expected: Type | None) -> Type:
        base = unwrap_optional(expected) if expected else None
        hints = base.params if isinstance(base, FnT) else ()

        inner = env.child()
        param_types: list[Type] = []
        for i, p in enumerate(node.params):
            if p.type_expr is not None:
                p.ty = self.resolve_type(p.type_expr)
            elif i < len(hints):
                p.ty = hints[i]
            else:
                self.error(
                    f"lambda parametresi '{p.name}' için tip çıkarılamıyor",
                    p.span,
                    hint=f"tipi yaz: |{p.name}: <Tip>| ...",
                )
                p.ty = ANY
            param_types.append(p.ty)
            inner.define(p.name, p.ty, False)

        declared_ret = self.resolve_type(node.ret_type) if node.ret_type else None
        expected_ret = declared_ret or (base.ret if isinstance(base, FnT) else None)

        prev_ret = self.current_ret
        self.current_ret = expected_ret if expected_ret is not None else VOID
        # Gövdeli lambda kendi deyim listesine yazılır: `?` orada lambdadan
        # çıkar ve doğru üretilir. Tek ifadelik lambda ok işaretinden sonra
        # doğrudan ifadeye derlenir, erken çıkışın konacağı yer yoktur.
        prev_yasak = self.soru_yasak
        self.soru_yasak = (None if isinstance(node.body, A.Block)
                           else "tek ifadelik lambda gövdesinde")

        if isinstance(node.body, A.Block):
            # Gövdeli lambda: dönüş tipi yazılmamışsa `return` ifadelerinden çıkar.
            if expected_ret is None:
                inferred = self.infer_block_return(node.body, inner)
                self.current_ret = inferred
                expected_ret = inferred
            self.check_block(node.body, inner)
            ret = self.current_ret
            if not is_void(ret) and not self.terminates(node.body):
                self.error("lambda her yolda değer döndürmüyor", node.span)
        else:
            ret = self.check_expr(node.body, inner, expected_ret)
            if expected_ret is not None and not assignable(expected_ret, ret):
                self.error(
                    f"lambda '{expected_ret}' döndürmeli, '{ret}' bulundu",
                    node.body.span,
                )
                ret = expected_ret

        self.current_ret = prev_ret
        self.soru_yasak = prev_yasak
        return FnT(tuple(param_types), ret)

    def infer_block_return(self, block: A.Block, env: Env) -> Type:
        """Gövdeli lambdanın dönüş tipini ilk `return` ifadesinden tahmin eder."""
        found = _first_return(block)
        if found is None or found.value is None:
            return VOID
        probe = Checker.__new__(Checker)
        probe.__dict__.update(self.__dict__)
        probe.errors = []  # tahmin sırasındaki hatalar bastırılır
        try:
            return probe.check_expr(found.value, env)
        except Exception:  # pragma: no cover - tahmin başarısızsa Void
            return VOID

    # ------------------------------------------------------------ yerleşikler
    def check_builtin(self, node: A.Call, name: str, env: Env) -> Type:
        args = node.args

        def arity(n: int) -> bool:
            if len(args) != n:
                self.error(
                    f"'{name}' {n} argüman bekler, {len(args)} verildi", node.span)
                for a in args:
                    self.check_expr(a, env)
                return False
            return True

        sayfa = _sayfa_imzalari()
        if name in sayfa:
            imza = sayfa[name]
            self.check_args(node, imza, env)
            return imza.ret

        sistem = _sistem_imzalari()
        if name in sistem:
            imza = sistem[name]
            self.check_args(node, imza, env)
            return imza.ret

        if name == "print":
            # Birden çok değer aralarında boşlukla yazdırılır: print("ad:", ad)
            if not args:
                self.error("'print' en az bir değer bekler", node.span)
                return VOID
            for a in args:
                self.check_expr(a, env)
            return VOID

        if name == "str":
            if not arity(1):
                return STRING
            self.check_expr(args[0], env)
            return STRING

        if name == "len":
            if not arity(1):
                return INT
            ty = self.check_expr(args[0], env)
            if not isinstance(ty, (ListT, MapT, AnyT)) and ty != STRING:
                self.error(f"'len' metin, liste ya da eşleme bekler, '{ty}' bulundu", args[0].span)
            return INT

        if name in ("int", "float"):
            if not arity(1):
                return INT if name == "int" else FLOAT
            ty = self.check_expr(args[0], env)
            target = INT if name == "int" else FLOAT
            other = FLOAT if name == "int" else INT
            if ty == STRING:
                node.__dict__["conv"] = "parse"
                return OptT(target)
            if ty == other or ty == target:
                node.__dict__["conv"] = "cast"
                return target
            if isinstance(ty, AnyT):
                node.__dict__["conv"] = "cast"
                return target
            self.error(
                f"'{name}' metin ya da sayı bekler, '{ty}' bulundu", args[0].span)
            return target

        if name == "abs":
            if not arity(1):
                return INT
            ty = self.check_expr(args[0], env)
            if ty not in (INT, FLOAT) and not isinstance(ty, AnyT):
                self.error(f"'abs' sayı bekler, '{ty}' bulundu", args[0].span)
                return INT
            return ty

        if name in ("min", "max"):
            if not arity(2):
                return INT
            a = self.check_expr(args[0], env)
            b = self.check_expr(args[1], env, a)
            if isinstance(a, AnyT) or isinstance(b, AnyT):
                return a if not isinstance(a, AnyT) else b
            if a in NUMERIC and b in NUMERIC:
                return FLOAT if FLOAT in (a, b) else INT
            if a == b and a == STRING:
                return STRING
            self.error(
                f"'{name}' iki sayı ya da iki metin bekler ('{a}', '{b}')",
                node.span,
            )
            return a if a in (INT, FLOAT, STRING) else INT

        if name in ("sqrt", "pow"):
            n = 1 if name == "sqrt" else 2
            if not arity(n):
                return FLOAT
            for a in args:
                ty = self.check_expr(a, env, FLOAT)
                if ty not in NUMERIC and not isinstance(ty, AnyT):
                    self.error(f"'{name}' sayı bekler, '{ty}' bulundu", a.span)
            return FLOAT

        if name in ("floor", "ceil", "round"):
            if not arity(1):
                return INT
            ty = self.check_expr(args[0], env, FLOAT)
            if ty not in NUMERIC and not isinstance(ty, AnyT):
                self.error(f"'{name}' sayı bekler, '{ty}' bulundu", args[0].span)
            return INT

        if name == "random":
            arity(0)
            return FLOAT

        if name == "panic":
            if not arity(1):
                return NEVER
            ty = self.check_expr(args[0], env, STRING)
            if ty != STRING and not isinstance(ty, AnyT):
                self.error(f"'panic' metin bekler, '{ty}' bulundu", args[0].span)
            return NEVER

        if name == "assert":
            if len(args) not in (1, 2):
                self.error(f"'assert' 1 ya da 2 argüman bekler, {len(args)} verildi", node.span)
                for a in args:
                    self.check_expr(a, env)
                return VOID
            cond = self.check_expr(args[0], env, BOOL)
            self.expect_bool(cond, args[0].span, "assert koşulu")
            if len(args) == 2:
                msg = self.check_expr(args[1], env, STRING)
                if msg != STRING and not isinstance(msg, AnyT):
                    self.error(f"'assert' mesajı metin olmalı, '{msg}' bulundu", args[1].span)
            return VOID

        self.error(f"bilinmeyen yerleşik: '{name}'", node.span)  # pragma: no cover
        return ANY


def _first_return(node: object) -> A.Return | None:
    if isinstance(node, A.Return):
        return node
    if isinstance(node, A.Block):
        for s in node.stmts:
            found = _first_return(s)
            if found is not None:
                return found
    if isinstance(node, A.If):
        return _first_return(node.then) or (
            _first_return(node.otherwise) if node.otherwise is not None else None)
    if isinstance(node, (A.While, A.For)):
        return _first_return(node.body)
    if isinstance(node, A.Match):
        for arm in node.arms:
            found = _first_return(arm.body)
            if found is not None:
                return found
    return None


def _member_hint(base: Type) -> str | None:
    names = _BUILTIN_MEMBER_NAMES.get(type(base).__name__)
    if base == STRING:
        names = _BUILTIN_MEMBER_NAMES["String"]
    elif base == ELEMENT:
        names = _BUILTIN_MEMBER_NAMES["Element"]
    elif base == OLAY:
        names = _BUILTIN_MEMBER_NAMES["Olay"]
    if not names:
        return None
    return f"kullanılabilir: {', '.join(sorted(names))}"


# ------------------------------------------------------ yerleşik metot tablosu
def builtin_method(base: Type, name: str) -> FnT | None:
    """Metin, liste ve eşleme üzerindeki yerleşik metotların imzası."""
    if base == STRING:
        table = {
            "len": FnT((), INT),
            "upper": FnT((), STRING),
            "lower": FnT((), STRING),
            "upperTr": FnT((), STRING),
            "lowerTr": FnT((), STRING),
            "trim": FnT((), STRING),
            "split": FnT((STRING,), ListT(STRING)),
            "contains": FnT((STRING,), BOOL),
            "replace": FnT((STRING, STRING), STRING),
            "startsWith": FnT((STRING,), BOOL),
            "endsWith": FnT((STRING,), BOOL),
            "slice": FnT((INT, INT), STRING),
            "charAt": FnT((INT,), STRING),
            "kodu": FnT((), INT),
            "indexOf": FnT((STRING,), INT),
            "repeat": FnT((INT,), STRING),
            "ters": FnT((), STRING),
            # Sabit genişliğe getirmek için: "7".solaDoldur(3, "0") -> "007"
            "solaDoldur": FnT((INT, STRING), STRING),
            "sagaDoldur": FnT((INT, STRING), STRING),
        }
        return table.get(name)

    if isinstance(base, ListT):
        t = base.elem
        opsiyonel_t = OptT(t) if not isinstance(t, OptT) else t
        table = {
            "len": FnT((), INT),
            # Lambda yazmadan kullanılabilen, adı kendini anlatan işlemler.
            "benzersiz": FnT((), ListT(t)),
            "say": FnT((t,), INT),
            "push": FnT((t,), VOID),
            "pop": FnT((), OptT(t) if not isinstance(t, OptT) else t),
            "contains": FnT((t,), BOOL),
            "indexOf": FnT((t,), INT),
            "slice": FnT((INT, INT), ListT(t)),
            "reverse": FnT((), ListT(t)),
            "sort": FnT((), ListT(t)),
            # Kendi ölçütünle sıralama: karşılaştırıcı a<b ise negatif,
            # a>b ise pozitif döndürür.
            "sirala": FnT((FnT((t, t), INT),), ListT(t)),
            # [[1, 2], [3]] -> [1, 2, 3] (bir kat)
            "duzlestir": FnT((), ListT(ANY)),
            # İki listeyi çiftler: [1,2] + ["a","b"] -> [(1,"a"), (2,"b")]
            # Argüman `Any`: liste tipleri değişmez olduğu için `[Any]`
            # yazmak `[String]` geçmeyi engellerdi. Çiftin ilk öğesi
            # tipini korur, ikincisi `Any` kalır.
            "eslestir": FnT((ANY,), ListT(TupleT((t, ANY)))),
            "ters": FnT((), ListT(t)),
            "first": FnT((), OptT(t) if not isinstance(t, OptT) else t),
            "last": FnT((), OptT(t) if not isinstance(t, OptT) else t),
            "map": FnT((FnT((t,), ANY),), ListT(ANY)),
            "filter": FnT((FnT((t,), BOOL),), ListT(t)),
            "reduce": FnT((FnT((ANY, t), ANY), ANY), ANY),
            "join": FnT((STRING,), STRING),
        }

        # Sayı listelerine özel kolay işlemler — lambda gerektirmez.
        if t in NUMERIC:
            table.update({
                "toplam": FnT((), t),
                "carpim": FnT((), t),
                "ortalama": FnT((), FLOAT),
                "enBuyuk": FnT((), opsiyonel_t),
                "enKucuk": FnT((), opsiyonel_t),
                "kat": FnT((t,), ListT(t)),
                "artir": FnT((t,), ListT(t)),
                "buyukler": FnT((t,), ListT(t)),
                "kucukler": FnT((t,), ListT(t)),
            })
            if t == INT:
                table["ciftler"] = FnT((), ListT(t))
                table["tekler"] = FnT((), ListT(t))

        # Metin listelerine özel kolay işlemler.
        if t == STRING:
            table.update({
                "buyukHarf": FnT((), ListT(STRING)),
                "kucukHarf": FnT((), ListT(STRING)),
                "icerenler": FnT((STRING,), ListT(STRING)),
            })

        return table.get(name)

    if base == ISTEK:
        return {
            "yontem": FnT((), STRING),
            "yol": FnT((), STRING),
            "sorgu": FnT((STRING,), OptT(STRING)),
            "baslik": FnT((STRING,), OptT(STRING)),
            "govde": FnT((), STRING),
            "ip": FnT((), STRING),
        }.get(name)

    if base == KOMUT:
        return {
            "cikis": FnT((), INT),      # 0 ise program başarıyla bitti
            "cikti": FnT((), STRING),   # standart çıktı
            "hata": FnT((), STRING),    # standart hata akışı
        }.get(name)

    if base == YANIT:
        return {
            "baslikYaz": FnT((STRING, STRING), YANIT),
            "durumYaz": FnT((INT,), YANIT),
        }.get(name)

    if base == OLAY:
        return {
            "tus": FnT((), STRING),        # basılan tuşun adı: "a", "Enter"…
            "ctrl": FnT((), BOOL),
            "shift": FnT((), BOOL),
            "alt": FnT((), BOOL),
            "engelle": FnT((), VOID),      # tarayıcının varsayılan işini iptal et
            "durdur": FnT((), VOID),       # olayın yukarı yayılmasını durdur
            "kaynak": FnT((), OptT(ELEMENT)),  # olayın geldiği öğe
            "x": FnT((), INT),             # fare: öğenin içindeki yatay konum (px)
            "y": FnT((), INT),             # fare: öğenin içindeki dikey konum (px)
        }.get(name)

    if base == ELEMENT:
        return {
            "metin": FnT((), STRING),
            "metinYaz": FnT((STRING,), VOID),
            "html": FnT((), STRING),
            "htmlYaz": FnT((STRING,), VOID),
            "deger": FnT((), STRING),
            "degerYaz": FnT((STRING,), VOID),
            "sinifEkle": FnT((STRING,), VOID),
            "sinifSil": FnT((STRING,), VOID),
            "sinifVarMi": FnT((STRING,), BOOL),
            "ozellik": FnT((STRING,), OptT(STRING)),
            "ozellikYaz": FnT((STRING, STRING), VOID),
            "stil": FnT((STRING, STRING), VOID),
            # Dinleyici olayı almak zorunda değil: `|| { ... }` da geçerlidir
            # (tip sistemi daha az parametreli fonksiyonu kabul eder).
            "dinle": FnT((STRING, FnT((OLAY,), VOID)), VOID),
            "ekle": FnT((ELEMENT,), VOID),
            # Metin kutusu (input / textarea) için imleç ve kaydırma erişimi
            "secimBasi": FnT((), INT),
            "secimSonu": FnT((), INT),
            "secimYap": FnT((INT, INT), VOID),
            "yaziEkle": FnT((STRING,), VOID),   # imleç konumuna metin yazar
            "kaydirmaUst": FnT((), INT),
            "kaydirmaUstYaz": FnT((INT,), VOID),
            "kaydirmaSol": FnT((), INT),
            "cikar": FnT((), VOID),
            "temizle": FnT((), VOID),
            "odaklan": FnT((), VOID),
            "isaretli": FnT((), BOOL),
            "isaretliYaz": FnT((BOOL,), VOID),
            "bul": FnT((STRING,), OptT(ELEMENT)),
            "bulHepsi": FnT((STRING,), ListT(ELEMENT)),
        }.get(name)

    if isinstance(base, MapT):
        k, v = base.key, base.value
        table = {
            "len": FnT((), INT),
            "get": FnT((k,), OptT(v) if not isinstance(v, OptT) else v),
            "set": FnT((k, v), VOID),
            "has": FnT((k,), BOOL),
            "remove": FnT((k,), VOID),
            "keys": FnT((), ListT(k)),
            "values": FnT((), ListT(v)),
        }
        return table.get(name)

    return None


_BUILTIN_MEMBER_NAMES = {
    "String": ["len", "upper", "lower", "upperTr", "lowerTr", "trim", "split", "contains", "replace",
               "startsWith", "endsWith", "slice", "charAt", "indexOf", "repeat", "kodu"],
    "ListT": ["len", "push", "pop", "contains", "indexOf", "slice", "reverse",
              "sort", "first", "last", "map", "filter", "reduce", "join",
              "benzersiz", "say", "toplam", "carpim", "ortalama", "enBuyuk",
              "enKucuk", "kat", "artir", "buyukler", "kucukler", "ciftler",
              "tekler", "buyukHarf", "kucukHarf", "icerenler"],
    "MapT": ["len", "get", "set", "has", "remove", "keys", "values"],
    "Element": ["metin", "metinYaz", "html", "htmlYaz", "deger", "degerYaz",
                "sinifEkle", "sinifSil", "sinifVarMi", "ozellik", "ozellikYaz",
                "stil", "dinle", "ekle", "cikar", "temizle", "odaklan",
                "bul", "bulHepsi", "secimBasi", "secimSonu", "secimYap",
                "yaziEkle", "kaydirmaUst", "kaydirmaUstYaz", "kaydirmaSol",
                "isaretli", "isaretliYaz"],
    "Olay": ["tus", "ctrl", "shift", "alt", "engelle", "durdur", "kaynak", "x", "y"],
    "Istek": ["yontem", "yol", "sorgu", "baslik", "govde", "ip"],
    "Komut": ["cikis", "cikti", "hata"],
    "Yanit": ["baslikYaz", "durumYaz"],
}


def check_module(module: A.Module, source: str = "") -> Checker:
    checker = Checker(module, source)
    checker.check()
    return checker
