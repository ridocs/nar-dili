"""Nar AST'sinden bytecode üretir.

JavaScript arka ucunun kardeşi: aynı ağacı alır, ama `narc/vm.py` sanal
makinesinin komutlarına çevirir. Böylece bir Nar programı Node olmadan
çalışabilir.

KAPSAM

Terminal programlarının ihtiyaç duyduğu her şey: sayılar, metinler,
listeler, eşlemeler, struct, enum, match, closure, generic işlevler.
Sayfa (DOM) ve sunucu işlemleri burada yok — onlar tarayıcı ve Node
hedeflerine ait.

DEĞİŞKEN ÇÖZÜMÜ

Üretici kendi kapsam zincirini tutar. Her ad üç yerden birinde bulunur:
yerel (bu işlevin çerçevesi), yakalanan (dıştaki işlevden) ya da global.
`Kapsam` sınıfı bunu izler ve closure'ın neyi yakalayacağını çıkarır.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import nar_ast as A
from ..bytecode import K, Islev, Program
from ..checker import Checker
from ..types import (
    FLOAT, INT, STRING, EnumT, ListT, MapT, OptT, StructT, unwrap_optional,
)
from ..vm import YERLESIK_INDISI


class UretimHatasi(Exception):
    """Bytecode'a çevrilemeyen bir yapı."""


@dataclass
class Kapsam:
    """Bir işlevin değişken kapsamı."""

    islev: Islev
    ust: "Kapsam | None" = None
    # ad → yerel indis (en içteki blok en sonda)
    bloklar: list = field(default_factory=lambda: [{}])
    # Yakalanan dış değişkenler: ad → (kapanış indisi)
    yakalanan_adlar: dict = field(default_factory=dict)

    def blok_ac(self):
        self.bloklar.append({})

    def blok_kapat(self):
        self.bloklar.pop()

    def tanimla(self, ad: str) -> int:
        indis = self.islev.yerel_sayisi
        self.islev.yerel_sayisi += 1
        self.bloklar[-1][ad] = indis
        return indis

    def yerel_bul(self, ad: str) -> int | None:
        for blok in reversed(self.bloklar):
            if ad in blok:
                return blok[ad]
        return None

    def yakala(self, ad: str) -> int | None:
        """Adı dış kapsamlarda arar; bulursa yakalama listesine ekler."""
        if ad in self.yakalanan_adlar:
            return self.yakalanan_adlar[ad]
        if self.ust is None:
            return None

        dis_yerel = self.ust.yerel_bul(ad)
        if dis_yerel is not None:
            indis = len(self.islev.yakalananlar)
            self.islev.yakalananlar.append((True, dis_yerel))
            self.yakalanan_adlar[ad] = indis
            return indis

        dis_yakalanan = self.ust.yakala(ad)
        if dis_yakalanan is not None:
            indis = len(self.islev.yakalananlar)
            self.islev.yakalananlar.append((False, dis_yakalanan))
            self.yakalanan_adlar[ad] = indis
            return indis
        return None


class BytecodeUretici:
    def __init__(self, module: A.Module, checker: Checker):
        self.module = module
        self.checker = checker
        self.program = Program(ana=Islev("main"))
        self.kapsam: Kapsam | None = None
        # Üst düzey adlar: fonksiyonlar ve değişkenler
        self.global_indis: dict[str, int] = {}
        # Döngü yamaları: (break yerleri, continue yerleri)
        self.dongu_yiginlari: list = []

    # --- yardımcılar ------------------------------------------------------

    @property
    def islev(self) -> Islev:
        return self.kapsam.islev

    def yaz(self, komut: K, arg: int | None = None, dugum=None) -> int:
        satir = getattr(getattr(dugum, "span", None), "line", 0) if dugum else 0
        return self.islev.yaz(komut, arg, satir)

    def sabit(self, deger) -> int:
        return self.islev.sabit_ekle(deger)

    def global_ad(self, ad: str) -> int:
        if ad not in self.global_indis:
            self.global_indis[ad] = len(self.program.global_adlar)
            self.program.global_adlar.append(ad)
        return self.global_indis[ad]

    def su_an(self) -> int:
        return len(self.islev.kod)

    # --- giriş ------------------------------------------------------------

    def uret(self) -> Program:
        self._tarifleri_topla()

        # Üst düzey işlevler önce kaydedilir: birbirlerini çağırabilmeliler.
        islev_dugumleri = [i for i in self.module.items if isinstance(i, A.FnDecl)]
        for d in islev_dugumleri:
            self.global_ad(d.name)

        # Metotlar da işlev olarak derlenir; adları "Tip.metot".
        for item in self.module.items:
            if isinstance(item, (A.StructDecl, A.EnumDecl)):
                for m in item.methods:
                    self.global_ad(f"{item.name}.{m.name}")

        ana = Islev("main")
        self.program.ana = ana
        self.kapsam = Kapsam(ana)

        # Üst düzey let/var'lar ve işlev tanımları `main` başında kurulur.
        for item in self.module.items:
            if isinstance(item, A.FnDecl):
                self._islev_tanimla(item, None)
            elif isinstance(item, (A.StructDecl, A.EnumDecl)):
                for m in item.methods:
                    self._islev_tanimla(m, item.name)

        for item in self.module.items:
            if isinstance(item, A.LetStmt):
                self._ust_duzey_let(item)

        # `main` gövdesi
        ana_dugum = next((d for d in islev_dugumleri if d.name == "main"), None)
        if ana_dugum is None:
            raise UretimHatasi("programda 'main' fonksiyonu yok")

        self.yaz(K.GLOBAL_OKU, self.global_ad("main"))
        self.yaz(K.CAGIR, 0)
        self.yaz(K.AT)
        self.yaz(K.DUR)
        return self.program

    def _tarifleri_topla(self):
        for item in self.module.items:
            if isinstance(item, A.StructDecl):
                self.program.struct_tarifleri[item.name] = [
                    f.name for f in item.fields]
            elif isinstance(item, A.EnumDecl):
                self.program.enum_tarifleri[item.name] = {
                    v.name: len(v.payload) for v in item.variants}

    def _ust_duzey_let(self, stmt: A.LetStmt):
        if stmt.value is not None:
            self.ifade(stmt.value)
        else:
            self.yaz(K.YOK)
        self.yaz(K.GLOBAL_YAZ, self.global_ad(stmt.name), stmt)

    def _islev_tanimla(self, decl: A.FnDecl, sahip: str | None):
        """İşlevi derler ve global olarak kaydeder."""
        ad = f"{sahip}.{decl.name}" if sahip else decl.name
        sablon = self.islev_derle(decl, ad, sahip)
        indis = len(self.program.islevler)
        self.program.islevler.append(sablon)
        self.yaz(K.KAPAT, indis, decl)
        self.yaz(K.GLOBAL_YAZ, self.global_ad(ad), decl)

    def islev_derle(self, decl: A.FnDecl, ad: str, sahip: str | None) -> Islev:
        islev = Islev(ad, parametre_sayisi=len(decl.params) + (1 if sahip else 0))
        onceki = self.kapsam
        self.kapsam = Kapsam(islev, ust=onceki)

        if sahip:
            self.kapsam.tanimla("self")
        for p in decl.params:
            self.kapsam.tanimla(p.name)

        if decl.body is not None:
            self.blok(decl.body)
        self.yaz(K.YOK)
        self.yaz(K.DON)

        self.kapsam = onceki
        return islev

    # --- deyimler ---------------------------------------------------------

    def blok(self, b: A.Block):
        self.kapsam.blok_ac()
        for s in b.stmts:
            self.deyim(s)
        self.kapsam.blok_kapat()

    def deyim(self, s: A.Stmt):
        if isinstance(s, A.LetStmt):
            if s.value is not None:
                self.ifade(s.value)
            else:
                self.yaz(K.YOK)
            indis = self.kapsam.tanimla(s.name)
            self.yaz(K.YEREL_YAZ, indis, s)

        elif isinstance(s, A.Assign):
            self._atama(s)

        elif isinstance(s, A.ExprStmt):
            self.ifade(s.expr)
            self.yaz(K.AT)

        elif isinstance(s, A.Return):
            if s.value is not None:
                self.ifade(s.value)
            else:
                self.yaz(K.YOK)
            self.yaz(K.DON, dugum=s)

        elif isinstance(s, A.If):
            self._eger(s)

        elif isinstance(s, A.While):
            self._while(s)

        elif isinstance(s, A.For):
            self._for(s)

        elif isinstance(s, A.Match):
            self._match_deyimi(s)

        elif isinstance(s, A.Break):
            yer = self.yaz(K.ATLA, 0, s)
            if not self.dongu_yiginlari:
                raise UretimHatasi("döngü dışında 'break'")
            self.dongu_yiginlari[-1][0].append(yer)

        elif isinstance(s, A.Continue):
            yer = self.yaz(K.ATLA, 0, s)
            if not self.dongu_yiginlari:
                raise UretimHatasi("döngü dışında 'continue'")
            self.dongu_yiginlari[-1][1].append(yer)

        else:
            raise UretimHatasi(f"bytecode'a çevrilemeyen deyim: {type(s).__name__}")

    def _atama(self, s: A.Assign):
        hedef = s.target

        # `x += 1` → önce mevcut değer okunur
        if s.op != "=":
            islec = s.op[0]
            if isinstance(hedef, A.Ident):
                self._ad_oku(hedef)
                self.ifade(s.value)
                self._ikili_islec(islec, s.ty if hasattr(s, "ty") else None,
                                  hedef.ty)
                self._ada_yaz(hedef)
                return
            # Alan ve dizin için: nesneyi iki kez değerlendirmemek adına
            # önce adresi hesaplayıp kopyalıyoruz.
            if isinstance(hedef, A.FieldAccess):
                self.ifade(hedef.obj)
                self.yaz(K.KOPYALA, 0)
                self.yaz(K.ALAN_OKU, self.sabit(hedef.name))
                self.ifade(s.value)
                self._ikili_islec(islec, None, hedef.ty)
                self.yaz(K.ALAN_YAZ, self.sabit(hedef.name), s)
                return
            if isinstance(hedef, A.Index):
                self.ifade(hedef.obj)
                self.ifade(hedef.index)
                self.yaz(K.KOPYALA, 1)
                self.yaz(K.KOPYALA, 1)
                self.yaz(K.DIZIN_OKU)
                self.ifade(s.value)
                self._ikili_islec(islec, None, hedef.ty)
                self.yaz(K.DIZIN_YAZ, dugum=s)
                return
            raise UretimHatasi("bu ifadeye bileşik atama yapılamaz")

        if isinstance(hedef, A.Ident):
            self.ifade(s.value)
            self._ada_yaz(hedef)
        elif isinstance(hedef, A.FieldAccess):
            self.ifade(hedef.obj)
            self.ifade(s.value)
            self.yaz(K.ALAN_YAZ, self.sabit(hedef.name), s)
        elif isinstance(hedef, A.Index):
            self.ifade(hedef.obj)
            self.ifade(hedef.index)
            self.ifade(s.value)
            self.yaz(K.DIZIN_YAZ, dugum=s)
        else:
            raise UretimHatasi("bu ifadeye atama yapılamaz")

    def _ada_yaz(self, ad_dugumu: A.Ident):
        yerel = self.kapsam.yerel_bul(ad_dugumu.name)
        if yerel is not None:
            self.yaz(K.YEREL_YAZ, yerel, ad_dugumu)
            return
        self.yaz(K.GLOBAL_YAZ, self.global_ad(ad_dugumu.name), ad_dugumu)

    def _eger(self, s: A.If):
        if s.bag_ad:
            self._eger_bagli(s)
            return
        self.ifade(s.cond)
        yanlis_atla = self.yaz(K.ATLA_YANLIS, 0, s)
        self.blok(s.then)

        if s.otherwise is not None:
            son_atla = self.yaz(K.ATLA, 0)
            self.islev.yamala(yanlis_atla, self.su_an())
            if isinstance(s.otherwise, A.Block):
                self.blok(s.otherwise)
            else:
                self.deyim(s.otherwise)
            self.islev.yamala(son_atla, self.su_an())
        else:
            self.islev.yamala(yanlis_atla, self.su_an())

    def _eger_bagli(self, s: A.If):
        """`if let ad = ifade` — değer bir kez hesaplanır, ada bağlanır.

        Ad yalnız `then` dalında görünür; blok onu `if`in dışına sızdırmaz.
        """
        self.kapsam.blok_ac()
        self.ifade(s.bag_ifade)
        ad_indis = self.kapsam.tanimla(s.bag_ad)
        self.yaz(K.KOPYALA, 0)
        self.yaz(K.YEREL_YAZ, ad_indis)

        # Yığında değerin bir kopyası duruyor: none değilse dala girilir.
        self.yaz(K.SABIT, self.sabit(None))
        self.yaz(K.ESIT_DEGIL)
        yanlis_atla = self.yaz(K.ATLA_YANLIS, 0, s)
        self.blok(s.then)

        if s.otherwise is not None:
            son_atla = self.yaz(K.ATLA, 0)
            self.islev.yamala(yanlis_atla, self.su_an())
            if isinstance(s.otherwise, A.Block):
                self.blok(s.otherwise)
            else:
                self.deyim(s.otherwise)
            self.islev.yamala(son_atla, self.su_an())
        else:
            self.islev.yamala(yanlis_atla, self.su_an())
        self.kapsam.blok_kapat()

    def _while(self, s: A.While):
        basi = self.su_an()
        self.ifade(s.cond)
        cikis = self.yaz(K.ATLA_YANLIS, 0, s)

        self.dongu_yiginlari.append(([], []))
        self.blok(s.body)
        kirilmalar, devamlar = self.dongu_yiginlari.pop()

        for yer in devamlar:
            self.islev.yamala(yer, basi)
        self.yaz(K.ATLA, basi)
        self.islev.yamala(cikis, self.su_an())
        for yer in kirilmalar:
            self.islev.yamala(yer, self.su_an())

    def _for(self, s: A.For):
        """`for` her zaman bir liste üzerinde döner.

        Aralık, metin ve eşleme de önce listeye çevrilir: VM'de tek bir
        yineleme biçimi olması hem üreticiyi hem makineyi sadeleştiriyor.
        """
        kaynak_tipi = unwrap_optional(s.iterable.ty) if s.iterable.ty else None

        self.kapsam.blok_ac()

        if isinstance(s.iterable, A.RangeExpr):
            self.ifade(s.iterable.start)
            self.ifade(s.iterable.end)
            self.yaz(K.DOGRU if s.iterable.inclusive else K.YANLIS)
            self.yaz(K.ARALIK)
        elif isinstance(kaynak_tipi, MapT):
            # Eşlemede anahtar listesi üzerinde dönülür.
            self.ifade(s.iterable)
            kaynak_indis = self.kapsam.tanimla(" esleme")
            self.yaz(K.KOPYALA, 0)
            self.yaz(K.YEREL_YAZ, kaynak_indis)
            self._yerlesik_cagir("anahtarlar", 1)
        elif kaynak_tipi == STRING:
            self.ifade(s.iterable)
            self._yerlesik_cagir("harfler", 1)
        else:
            self.ifade(s.iterable)

        liste_indis = self.kapsam.tanimla(" liste")
        self.yaz(K.YEREL_YAZ, liste_indis)

        sayac_indis = self.kapsam.tanimla(" sayac")
        self.yaz(K.SABIT, self.sabit(0))
        self.yaz(K.YEREL_YAZ, sayac_indis)

        ad_indisleri = [self.kapsam.tanimla(ad) for ad in s.names]

        basi = self.su_an()
        self.yaz(K.YEREL_OKU, sayac_indis)
        self.yaz(K.YEREL_OKU, liste_indis)
        self._yerlesik_cagir("len", 1)
        self.yaz(K.KUCUK)
        cikis = self.yaz(K.ATLA_YANLIS, 0, s)

        # Döngü değişkenlerini doldur
        self.yaz(K.YEREL_OKU, liste_indis)
        self.yaz(K.YEREL_OKU, sayac_indis)
        self.yaz(K.DIZIN_OKU)
        if isinstance(kaynak_tipi, MapT) and len(s.names) == 2:
            # (anahtar, değer): anahtarı yaz, değeri eşlemeden oku
            self.yaz(K.KOPYALA, 0)
            self.yaz(K.YEREL_YAZ, ad_indisleri[0])
            esleme_indis = self.kapsam.yerel_bul(" esleme")
            self.yaz(K.YEREL_OKU, esleme_indis)
            self.yaz(K.KOPYALA, 1)
            self.yaz(K.DIZIN_OKU)
            self.yaz(K.YEREL_YAZ, ad_indisleri[1])
            self.yaz(K.AT)
        elif len(s.names) == 2:
            # (indeks, öğe): öğeyi yaz, sonra sayacı indekse koy. Döngü
            # zaten bir sayaç tutuyordu; indeks onun okunmasından ibaret.
            self.yaz(K.YEREL_YAZ, ad_indisleri[1])
            self.yaz(K.YEREL_OKU, sayac_indis)
            self.yaz(K.YEREL_YAZ, ad_indisleri[0])
        else:
            self.yaz(K.YEREL_YAZ, ad_indisleri[0])

        self.dongu_yiginlari.append(([], []))
        self.blok(s.body)
        kirilmalar, devamlar = self.dongu_yiginlari.pop()

        artir = self.su_an()
        for yer in devamlar:
            self.islev.yamala(yer, artir)
        self.yaz(K.YEREL_OKU, sayac_indis)
        self.yaz(K.SABIT, self.sabit(1))
        self.yaz(K.TOPLA)
        self.yaz(K.YEREL_YAZ, sayac_indis)
        self.yaz(K.ATLA, basi)

        self.islev.yamala(cikis, self.su_an())
        for yer in kirilmalar:
            self.islev.yamala(yer, self.su_an())
        self.kapsam.blok_kapat()

    def _match_deyimi(self, s: A.Match):
        self.ifade(s.subject)
        konu_indis = self.kapsam.tanimla(" konu")
        self.yaz(K.YEREL_YAZ, konu_indis)

        son_atlamalar = []
        for kol in s.arms:
            self.kapsam.blok_ac()
            atla_yeri = self._desen_kosulu(kol.pattern, konu_indis)
            if isinstance(kol.body, A.Block):
                self.blok(kol.body)
            elif isinstance(kol.body, A.Stmt):
                self.deyim(kol.body)
            else:
                self.ifade(kol.body)
                self.yaz(K.AT)
            son_atlamalar.append(self.yaz(K.ATLA, 0))
            if atla_yeri is not None:
                self.islev.yamala(atla_yeri, self.su_an())
            self.kapsam.blok_kapat()

        for yer in son_atlamalar:
            self.islev.yamala(yer, self.su_an())

    def _desen_kosulu(self, desen: A.Pattern, konu_indis: int) -> int | None:
        """Deseni sınar; uymuyorsa atlanacak yeri döndürür.

        `None` dönerse desen her zaman uyar (joker ya da bağlama).
        """
        if isinstance(desen, A.WildcardPat):
            return None

        if isinstance(desen, A.BindPat):
            enum_adi = desen.__dict__.get("as_enum")
            if enum_adi is not None:      # yüksüz varyant adı
                self.yaz(K.YEREL_OKU, konu_indis)
                self.yaz(K.ETIKET)
                self.yaz(K.SABIT, self.sabit(desen.name))
                self.yaz(K.ESIT)
                return self.yaz(K.ATLA_YANLIS, 0)
            indis = self.kapsam.tanimla(desen.name)
            self.yaz(K.YEREL_OKU, konu_indis)
            self.yaz(K.YEREL_YAZ, indis)
            return None

        if isinstance(desen, A.LiteralPat):
            self.yaz(K.YEREL_OKU, konu_indis)
            self.ifade(desen.value)
            self.yaz(K.ESIT)
            return self.yaz(K.ATLA_YANLIS, 0)

        if isinstance(desen, A.EnumPat):
            self.yaz(K.YEREL_OKU, konu_indis)
            self.yaz(K.ETIKET)
            self.yaz(K.SABIT, self.sabit(desen.variant))
            self.yaz(K.ESIT)
            atla = self.yaz(K.ATLA_YANLIS, 0)

            for i, alt in enumerate(desen.subpatterns):
                if isinstance(alt, A.WildcardPat):
                    continue
                if isinstance(alt, A.BindPat) and alt.__dict__.get("as_enum") is None:
                    indis = self.kapsam.tanimla(alt.name)
                    self.yaz(K.YEREL_OKU, konu_indis)
                    self.yaz(K.YUK_OKU, i)
                    self.yaz(K.YEREL_YAZ, indis)
                    self.yaz(K.AT)
                    continue
                raise UretimHatasi(
                    "iç içe desenler henüz bytecode'a çevrilmiyor")
            return atla

        raise UretimHatasi(f"çevrilemeyen desen: {type(desen).__name__}")

    # --- ifadeler ---------------------------------------------------------

    def ifade(self, e: A.Expr):
        if isinstance(e, A.IntLit):
            self.yaz(K.SABIT, self.sabit(int(e.value)), e)
        elif isinstance(e, A.FloatLit):
            self.yaz(K.SABIT, self.sabit(float(e.value)), e)
        elif isinstance(e, A.BoolLit):
            self.yaz(K.DOGRU if e.value else K.YANLIS, dugum=e)
        elif isinstance(e, A.NoneLit):
            self.yaz(K.YOK, dugum=e)
        elif isinstance(e, A.StringLit):
            self._metin(e)
        elif isinstance(e, A.Ident):
            self._ad_oku(e)
        elif isinstance(e, A.SelfExpr):
            indis = self.kapsam.yerel_bul("self")
            if indis is None:
                raise UretimHatasi("'self' bu kapsamda yok")
            self.yaz(K.YEREL_OKU, indis, e)
        elif isinstance(e, A.ListLit):
            for o in e.items:
                self.ifade(o)
            self.yaz(K.LISTE, len(e.items), e)
        elif isinstance(e, A.MapLit):
            for anahtar, deger in e.entries:
                self.ifade(anahtar)
                self.ifade(deger)
            self.yaz(K.ESLEME, len(e.entries), e)
        elif isinstance(e, A.StructLit):
            self._struct_lit(e)
        elif isinstance(e, A.Unary):
            self._tekli(e)
        elif isinstance(e, A.Binary):
            self._ikili(e)
        elif isinstance(e, A.RangeExpr):
            self.ifade(e.start)
            self.ifade(e.end)
            self.yaz(K.DOGRU if e.inclusive else K.YANLIS)
            self.yaz(K.ARALIK, dugum=e)
        elif isinstance(e, A.Index):
            self.ifade(e.obj)
            self.ifade(e.index)
            self.yaz(K.DIZIN_OKU, dugum=e)
        elif isinstance(e, A.FieldAccess):
            self._alan_erisimi(e)
        elif isinstance(e, A.Propagate):
            # `ifade?` — none ise işlevden hemen none döner.
            # ATLA_VAR_TUT tam bunun için var: none değilse atlar ve
            # değeri yığında bırakır, none ise onu atar.
            self.ifade(e.operand)
            devam = self.yaz(K.ATLA_VAR_TUT, 0, e)
            self.yaz(K.YOK)
            self.yaz(K.DON, dugum=e)
            self.islev.yamala(devam, self.su_an())

        elif isinstance(e, A.Unwrap):
            # `x!` — none ise sessizce geçmek yerine durmalı; yoksa hata
            # çok sonra, anlamsız bir yerde ortaya çıkar.
            self.ifade(e.operand)
            self._yerlesik_cagir("zorlaAc", 1, e)
        elif isinstance(e, A.Call):
            self._cagri(e)
        elif isinstance(e, A.Lambda):
            self._lambda(e)
        elif isinstance(e, A.IfExpr):
            self._eger_ifadesi(e)
        elif isinstance(e, A.BlockExpr):
            self._blok_ifadesi(e)
        elif isinstance(e, A.MatchExpr):
            self._match_ifadesi(e)
        else:
            raise UretimHatasi(
                f"bytecode'a çevrilemeyen ifade: {type(e).__name__}")

    def _ad_oku(self, e: A.Ident):
        # Enum varyantı: `Renk.Kirmizi` ya da çıplak `Kirmizi`
        if e.__dict__.get("resolved") == "enum_variant":
            enum_adi = e.__dict__["enum_name"]
            self.yaz(K.VARYANT, self.sabit(f"{enum_adi}.{e.name}:0"), e)
            return

        yerel = self.kapsam.yerel_bul(e.name)
        if yerel is not None:
            self.yaz(K.YEREL_OKU, yerel, e)
            return
        yakalanan = self.kapsam.yakala(e.name)
        if yakalanan is not None:
            self.yaz(K.KAPALI_OKU, yakalanan, e)
            return
        self.yaz(K.GLOBAL_OKU, self.global_ad(e.name), e)

    def _metin(self, e: A.StringLit):
        if not e.parts:
            self.yaz(K.SABIT, self.sabit(""), e)
            return
        ilk = True
        for parca in e.parts:
            if isinstance(parca, str):
                self.yaz(K.SABIT, self.sabit(parca))
            else:
                self.ifade(parca)
            if not ilk:
                self.yaz(K.METIN_EKLE)
            ilk = False
        # Tek parça metin değilse metne çevrilmeli
        if len(e.parts) == 1 and not isinstance(e.parts[0], str):
            self._yerlesik_cagir("str", 1)

    def _struct_lit(self, e: A.StructLit):
        tarif = self.program.struct_tarifleri.get(e.type_name)
        if tarif is None:
            raise UretimHatasi(f"bilinmeyen struct: {e.type_name}")
        verilen = dict(e.fields)
        for alan in tarif:
            if alan in verilen:
                self.ifade(verilen[alan])
            else:
                self.yaz(K.YOK)
        self.yaz(K.STRUCT, self.sabit(e.type_name), e)

    def _tekli(self, e: A.Unary):
        self.ifade(e.operand)
        if e.op == "!":
            self.yaz(K.DEGIL, dugum=e)
        elif e.op == "-":
            tip = unwrap_optional(e.ty) if e.ty else None
            self.yaz(K.FNEGATIF if tip == FLOAT else K.NEGATIF, dugum=e)
        else:
            raise UretimHatasi(f"bilinmeyen tekli işleç: {e.op}")

    def _ikili(self, e: A.Binary):
        # Kısa devre yapan işleçler ayrı: sağ taraf her zaman
        # değerlendirilmemeli.
        if e.op == "&&":
            self.ifade(e.left)
            atla = self.yaz(K.ATLA_YANLIS_TUT, 0, e)
            self.ifade(e.right)
            self.islev.yamala(atla, self.su_an())
            return
        if e.op == "||":
            self.ifade(e.left)
            atla = self.yaz(K.ATLA_DOGRU_TUT, 0, e)
            self.ifade(e.right)
            self.islev.yamala(atla, self.su_an())
            return
        if e.op == "??":
            self.ifade(e.left)
            atla = self.yaz(K.ATLA_VAR_TUT, 0, e)
            self.ifade(e.right)
            self.islev.yamala(atla, self.su_an())
            return

        self.ifade(e.left)
        self.ifade(e.right)
        self._ikili_islec(e.op, e.ty, e.left.ty)

    def _ikili_islec(self, op: str, sonuc_tipi, sol_tipi):
        sonuc = unwrap_optional(sonuc_tipi) if sonuc_tipi else None
        sol = unwrap_optional(sol_tipi) if sol_tipi else None

        if op == "+":
            if sonuc == STRING:
                self.yaz(K.METIN_EKLE)
                return
            if sonuc == FLOAT:
                self.yaz(K.FTOPLA)
                return
            if isinstance(sonuc, ListT):
                self._yerlesik_cagir("listeBirlestir", 2)
                return
            self.yaz(K.TOPLA)
            return

        ondalik = sonuc == FLOAT
        eslesme = {
            "-": K.FCIKAR if ondalik else K.CIKAR,
            "*": K.FCARP if ondalik else K.CARP,
            "/": K.FBOL if ondalik else K.BOL,
            "%": K.FMOD if ondalik else K.MOD,
            "==": K.ESIT,
            "!=": K.ESIT_DEGIL,
            "<": K.KUCUK,
            "<=": K.KUCUK_ESIT,
            ">": K.BUYUK,
            ">=": K.BUYUK_ESIT,
        }
        if op not in eslesme:
            raise UretimHatasi(f"bilinmeyen işleç: {op}")
        self.yaz(eslesme[op])

    def _alan_erisimi(self, e: A.FieldAccess):
        cozum = e.__dict__.get("resolved")
        if cozum == "enum_variant":
            enum_adi = e.__dict__["enum_name"]
            self.yaz(K.VARYANT, self.sabit(f"{enum_adi}.{e.name}:0"), e)
            return
        self.ifade(e.obj)
        if e.safe:
            # `a?.b` — nesne none ise sonuç none; alan hiç okunmaz.
            oku = self.yaz(K.ATLA_VAR_TUT, 0, e)
            self.yaz(K.YOK)
            son = self.yaz(K.ATLA, 0)
            self.islev.yamala(oku, self.su_an())
            self.yaz(K.ALAN_OKU, self.sabit(e.name), e)
            self.islev.yamala(son, self.su_an())
            return
        self.yaz(K.ALAN_OKU, self.sabit(e.name), e)

    def _cagri(self, e: A.Call):
        cozum = e.__dict__.get("resolved")

        if cozum == "enum_variant":
            enum_adi = e.__dict__["enum_name"]
            varyant = e.__dict__["variant"]
            for a in e.args:
                self.ifade(a)
            self.yaz(K.VARYANT,
                     self.sabit(f"{enum_adi}.{varyant}:{len(e.args)}"), e)
            return

        if cozum == "builtin":
            self._yerlesik_dugum(e)
            return

        if cozum in ("builtin_method", "method"):
            self._metot_cagrisi(e)
            return

        # Sıradan çağrı
        self.ifade(e.callee)
        for a in e.args:
            self.ifade(a)
        self.yaz(K.CAGIR, len(e.args), e)

    def _yerlesik_dugum(self, e: A.Call):
        ad = e.callee.name
        for a in e.args:
            self.ifade(a)
        self._yerlesik_cagir(ad, len(e.args), e)

    def _yerlesik_cagir(self, ad: str, n: int, dugum=None):
        indis = YERLESIK_INDISI.get(ad)
        if indis is None:
            indis = EK_YERLESIK_INDISI.get(ad)
            if indis is None:
                temiz = ad[2:] if ad.startswith("m_") else ad
                if temiz in SAYFA_VE_SUNUCU:
                    raise UretimHatasi(
                        f"'{temiz}' sanal makinede yok: sayfa ve sunucu "
                        "işlemleri tarayıcı ya da Node hedefinde çalışır "
                        "(nar build --target web / --target js)")
                raise UretimHatasi(f"bu ortamda yerleşik yok: {temiz}()")
        self.yaz(K.YERLESIK, (indis << 8) | n, dugum)

    def _metot_cagrisi(self, e: A.Call):
        callee = e.callee
        alici_tipi = unwrap_optional(callee.obj.ty) if callee.obj.ty else None

        if callee.safe:
            # `a?.metot()` — nesne none ise çağrı yapılmaz.
            self.ifade(callee.obj)
            cagir = self.yaz(K.ATLA_VAR_TUT, 0, e)
            self.yaz(K.YOK)
            son = self.yaz(K.ATLA, 0)
            self.islev.yamala(cagir, self.su_an())
            alici_indis = self.kapsam.tanimla(" alici")
            self.yaz(K.YEREL_YAZ, alici_indis)
            self._metot_govdesi(e, callee, alici_tipi, alici_indis)
            self.islev.yamala(son, self.su_an())
            return

        self._metot_govdesi(e, callee, alici_tipi, None)

    def _metot_govdesi(self, e: A.Call, callee, alici_tipi, alici_indis):
        """Metot çağrısının kendisi.

        `alici_indis` verilirse alıcı o yerelden okunur (güvenli çağrıda
        nesne zaten değerlendirilmiştir); yoksa yeniden üretilir.
        """
        def alici_yukle():
            if alici_indis is not None:
                self.yaz(K.YEREL_OKU, alici_indis)
            else:
                self.ifade(callee.obj)

        # Kullanıcı tanımlı metot: global "Tip.metot" olarak duruyor
        if isinstance(alici_tipi, (StructT, EnumT)):
            metot_adi = f"{alici_tipi.name}.{callee.name}"
            if metot_adi in self.global_indis:
                self.yaz(K.GLOBAL_OKU, self.global_ad(metot_adi))
                alici_yukle()
                for a in e.args:
                    self.ifade(a)
                self.yaz(K.CAGIR, len(e.args) + 1, e)
                return

        # Yerleşik metot: alıcı ilk argüman olur
        alici_yukle()
        for a in e.args:
            self.ifade(a)
        self._yerlesik_cagir("m_" + callee.name, len(e.args) + 1, e)

    def _lambda(self, e: A.Lambda):
        islev = Islev(f"<lambda>", parametre_sayisi=len(e.params))
        onceki = self.kapsam
        self.kapsam = Kapsam(islev, ust=onceki)
        for p in e.params:
            self.kapsam.tanimla(p.name)

        if isinstance(e.body, A.Block):
            self.blok(e.body)
            self.yaz(K.YOK)
            self.yaz(K.DON)
        else:
            self.ifade(e.body)
            self.yaz(K.DON)

        self.kapsam = onceki
        indis = len(self.program.islevler)
        self.program.islevler.append(islev)
        self.yaz(K.KAPAT, indis, e)

    def _eger_ifadesi(self, e: A.IfExpr):
        self.ifade(e.cond)
        yanlis = self.yaz(K.ATLA_YANLIS, 0, e)
        self.ifade(e.then)
        son = self.yaz(K.ATLA, 0)
        self.islev.yamala(yanlis, self.su_an())
        self.ifade(e.otherwise)
        self.islev.yamala(son, self.su_an())

    def _blok_ifadesi(self, e: A.BlockExpr):
        self.kapsam.blok_ac()
        deyimler = e.block.stmts
        for s in deyimler[:-1]:
            self.deyim(s)
        son = deyimler[-1]
        if isinstance(son, A.ExprStmt):
            self.ifade(son.expr)
        else:
            self.deyim(son)
            self.yaz(K.YOK)
        self.kapsam.blok_kapat()

    def _match_ifadesi(self, e: A.MatchExpr):
        self.ifade(e.subject)
        self.kapsam.blok_ac()
        konu_indis = self.kapsam.tanimla(" konu")
        self.yaz(K.YEREL_YAZ, konu_indis)

        son_atlamalar = []
        for kol in e.arms:
            self.kapsam.blok_ac()
            atla_yeri = self._desen_kosulu(kol.pattern, konu_indis)
            if isinstance(kol.body, A.Block):
                self._blok_ifadesi(A.BlockExpr(kol.body.span, kol.body))
            else:
                self.ifade(kol.body)
            son_atlamalar.append(self.yaz(K.ATLA, 0))
            if atla_yeri is not None:
                self.islev.yamala(atla_yeri, self.su_an())
            self.kapsam.blok_kapat()

        # Hiçbir dal uymazsa (tip denetleyici buna izin vermez) none.
        self.yaz(K.YOK)
        for yer in son_atlamalar:
            self.islev.yamala(yer, self.su_an())
        self.kapsam.blok_kapat()


# Yalnızca tarayıcı ya da Node hedefinde anlamlı olanlar. Sanal makinede
# sayfa da sunucu da yoktur; hata mesajı bunu açıkça söylemeli.
SAYFA_VE_SUNUCU = {
    "bul", "bulHepsi", "olustur", "govde", "zamanla", "istek",
    "sunucu", "yanit", "yanitMetin", "yanitHtml", "yanitJson", "yanitDosya",
    "yonlendir",
    # Element metotları
    "metin", "metinYaz", "html", "htmlYaz", "deger", "degerYaz",
    "sinifEkle", "sinifSil", "sinifVarMi", "ozellik", "ozellikYaz", "stil",
    "dinle", "ekle", "cikar", "temizle", "odaklan", "secimBasi", "secimSonu",
    "secimYap", "yaziEkle", "kaydirmaUst", "kaydirmaUstYaz", "kaydirmaSol",
}

# Üreticinin kullandığı, VM'de metot olarak duran ek yerleşikler.
# `narc/vm_metotlar.py` bunları doldurur.
EK_YERLESIK_INDISI: dict[str, int] = {}


def uret(module: A.Module, checker: Checker) -> Program:
    return BytecodeUretici(module, checker).uret()
