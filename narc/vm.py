"""Nar sanal makinesi — bytecode'u doğrudan çalıştırır.

JavaScript yok, Node yok. Program `narc/bytecode.py` komutlarına çevrilir
ve burada yürütülür.

DEĞER TEMSİLİ

    Int      → int
    Float    → float
    Bool     → bool
    String   → str
    none     → None
    [T]      → list
    {K: V}   → dict
    struct   → NarStruct
    enum     → NarVaryant
    işlev    → Kapanis

ÇAĞRI MODELİ

Her çağrı bir `Cerceve` açar: işlev, yerel değişkenler, dönüş adresi ve
yığın tabanı. Python'un kendi yığını kullanılmaz — böylece özyineleme
derinliği Python'unkine değil, kendi sınırımıza bağlı.
"""

from __future__ import annotations

import math
import random
import sys
import threading
import time
from dataclasses import dataclass, field

from .bytecode import K, Islev, Program

# Özyineleme sınırı. Kendi sayacımız, Python'un yığınına bağlı değil.
COKDERIN = 10_000


class NarCalismaHatasi(Exception):
    """Çalışma anında oluşan hata: sıfıra bölme, dizin taşması, panik…"""

    def __init__(self, mesaj: str, yigin: list | None = None):
        super().__init__(mesaj)
        self.mesaj = mesaj
        self.yigin = yigin or []

    def __str__(self) -> str:
        if not self.yigin:
            return self.mesaj
        iz = "\n".join(f"  {ad} içinde" for ad in reversed(self.yigin))
        return f"{self.mesaj}\n{iz}"


@dataclass
class NarStruct:
    tip: str
    alanlar: dict

    def __eq__(self, o):
        return (isinstance(o, NarStruct) and o.tip == self.tip
                and o.alanlar == self.alanlar)


@dataclass
class NarVaryant:
    tip: str
    varyant: str
    yuk: list = field(default_factory=list)

    def __eq__(self, o):
        return (isinstance(o, NarVaryant) and o.tip == self.tip
                and o.varyant == self.varyant and o.yuk == self.yuk)


@dataclass
class Kapanis:
    """Bir işlev ve yakaladığı değerler."""

    islev: Islev
    yakalanan: list = field(default_factory=list)
    # Metot çağrılarında bağlı nesne
    kendisi: object = None


@dataclass
class Cerceve:
    kapanis: Kapanis
    yereller: list
    donus_adresi: int
    yigin_tabani: int


def metin(deger) -> str:
    """Nar değerini kullanıcıya gösterilecek metne çevirir.

    Kurallar JavaScript arka ucundaki `$str` ile aynı: aynı program iki
    hedefte de aynı çıktıyı vermeli.
    """
    if deger is None:
        return "none"
    if deger is True:
        return "true"
    if deger is False:
        return "false"
    if isinstance(deger, float):
        if deger == int(deger) and abs(deger) < 1e15:
            return f"{int(deger)}.0"
        return repr(deger)
    if isinstance(deger, str):
        return deger
    if isinstance(deger, list):
        return "[" + ", ".join(_ic_metin(o) for o in deger) + "]"
    if isinstance(deger, dict):
        icler = ", ".join(f"{_ic_metin(k)}: {_ic_metin(v)}"
                          for k, v in deger.items())
        return "{" + icler + "}"
    if isinstance(deger, NarStruct):
        icler = ", ".join(f"{ad}: {_ic_metin(v)}"
                          for ad, v in deger.alanlar.items())
        # Boşluklar JavaScript arka ucuyla aynı: `Nokta { x: 1, y: 2 }`
        return f"{deger.tip} {{ {icler} }}" if icler else f"{deger.tip} {{}}"
    if isinstance(deger, NarVaryant):
        if not deger.yuk:
            return f"{deger.tip}.{deger.varyant}"
        return (f"{deger.tip}.{deger.varyant}("
                + ", ".join(_ic_metin(y) for y in deger.yuk) + ")")
    if isinstance(deger, Kapanis):
        return f"<işlev {deger.islev.ad}>"
    return str(deger)


def _ic_metin(deger) -> str:
    """Liste/struct içindeki metinler tırnakla gösterilir."""
    if isinstance(deger, str):
        return '"' + deger.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return metin(deger)


class VM:
    def __init__(self, program: Program, argumanlar: list | None = None):
        self.program = program
        self.globaller: dict[int, object] = {}
        self.yigin: list = []
        self.cerceveler: list[Cerceve] = []
        self.argumanlar = argumanlar or []
        self.cikti: list[str] = []
        self.cikti_yaz = True

    # --- yardımcılar ------------------------------------------------------

    def hata(self, mesaj: str):
        iz = [c.kapanis.islev.ad for c in self.cerceveler]
        return NarCalismaHatasi(mesaj, iz)

    def _satir(self) -> int:
        if not self.cerceveler:
            return 0
        c = self.cerceveler[-1]
        satirlar = c.kapanis.islev.satirlar
        i = c.donus_adresi - 1
        return satirlar[i] if 0 <= i < len(satirlar) else 0

    # --- çalıştırma -------------------------------------------------------

    def calistir(self) -> object:
        ana = Kapanis(self.program.ana)
        return self.cagir(ana, [])

    def cagir(self, kapanis: Kapanis, argumanlar: list) -> object:
        """Bir işlevi çağırır ve dönüş değerini verir."""
        if len(self.cerceveler) >= COKDERIN:
            raise self.hata("çağrı yığını çok derin (sonsuz özyineleme olabilir)")

        islev = kapanis.islev
        yereller = [None] * max(islev.yerel_sayisi, len(argumanlar))
        for i, a in enumerate(argumanlar):
            yereller[i] = a

        cerceve = Cerceve(kapanis, yereller, 0, len(self.yigin))
        self.cerceveler.append(cerceve)
        try:
            return self._dongu(cerceve)
        finally:
            self.cerceveler.pop()
            del self.yigin[cerceve.yigin_tabani:]

    def _dongu(self, cerceve: Cerceve) -> object:
        islev = cerceve.kapanis.islev
        kod = islev.kod
        sabitler = islev.sabitler
        yigin = self.yigin
        ip = 0

        while ip < len(kod):
            komut = kod[ip]
            k = komut[0]
            cerceve.donus_adresi = ip + 1
            ip += 1

            # --- yığın ---
            if k == K.SABIT:
                yigin.append(sabitler[komut[1]])
            elif k == K.YOK:
                yigin.append(None)
            elif k == K.DOGRU:
                yigin.append(True)
            elif k == K.YANLIS:
                yigin.append(False)
            elif k == K.AT:
                yigin.pop()
            elif k == K.KOPYALA:
                yigin.append(yigin[-1 - komut[1]])

            # --- değişkenler ---
            elif k == K.YEREL_OKU:
                yigin.append(cerceve.yereller[komut[1]])
            elif k == K.YEREL_YAZ:
                cerceve.yereller[komut[1]] = yigin.pop()
            elif k == K.GLOBAL_OKU:
                yigin.append(self.globaller.get(komut[1]))
            elif k == K.GLOBAL_YAZ:
                self.globaller[komut[1]] = yigin.pop()
            elif k == K.KAPALI_OKU:
                yigin.append(cerceve.kapanis.yakalanan[komut[1]])

            # --- aritmetik ---
            elif k == K.TOPLA:
                b = yigin.pop(); yigin[-1] = yigin[-1] + b
            elif k == K.CIKAR:
                b = yigin.pop(); yigin[-1] = yigin[-1] - b
            elif k == K.CARP:
                b = yigin.pop(); yigin[-1] = yigin[-1] * b
            elif k == K.BOL:
                b = yigin.pop()
                if b == 0:
                    raise self.hata("sıfıra bölme")
                a = yigin[-1]
                # Nar'da tam bölme sıfıra doğru kırpar (JavaScript gibi),
                # Python'un aşağı yuvarlamasından farklı.
                yigin[-1] = int(a / b)
            elif k == K.MOD:
                b = yigin.pop()
                if b == 0:
                    raise self.hata("sıfıra bölme (mod)")
                a = yigin[-1]
                yigin[-1] = a - int(a / b) * b
            elif k == K.FTOPLA:
                b = yigin.pop(); yigin[-1] = float(yigin[-1]) + float(b)
            elif k == K.FCIKAR:
                b = yigin.pop(); yigin[-1] = float(yigin[-1]) - float(b)
            elif k == K.FCARP:
                b = yigin.pop(); yigin[-1] = float(yigin[-1]) * float(b)
            elif k == K.FBOL:
                b = yigin.pop()
                if b == 0:
                    raise self.hata("sıfıra bölme")
                yigin[-1] = float(yigin[-1]) / float(b)
            elif k == K.FMOD:
                b = yigin.pop()
                if b == 0:
                    raise self.hata("sıfıra bölme (mod)")
                a = float(yigin[-1])
                yigin[-1] = math.fmod(a, float(b))
            elif k == K.NEGATIF:
                yigin[-1] = -yigin[-1]
            elif k == K.FNEGATIF:
                yigin[-1] = -float(yigin[-1])
            elif k == K.METIN_EKLE:
                b = yigin.pop()
                yigin[-1] = metin(yigin[-1]) + metin(b)

            # --- karşılaştırma ---
            elif k == K.ESIT:
                b = yigin.pop(); yigin[-1] = yigin[-1] == b
            elif k == K.ESIT_DEGIL:
                b = yigin.pop(); yigin[-1] = yigin[-1] != b
            elif k == K.KUCUK:
                b = yigin.pop(); yigin[-1] = yigin[-1] < b
            elif k == K.KUCUK_ESIT:
                b = yigin.pop(); yigin[-1] = yigin[-1] <= b
            elif k == K.BUYUK:
                b = yigin.pop(); yigin[-1] = yigin[-1] > b
            elif k == K.BUYUK_ESIT:
                b = yigin.pop(); yigin[-1] = yigin[-1] >= b
            elif k == K.DEGIL:
                yigin[-1] = not yigin[-1]

            # --- akış ---
            elif k == K.ATLA:
                ip = komut[1]
            elif k == K.ATLA_YANLIS:
                if not yigin.pop():
                    ip = komut[1]
            elif k == K.ATLA_DOGRU:
                if yigin.pop():
                    ip = komut[1]
            elif k == K.ATLA_YANLIS_TUT:
                if not yigin[-1]:
                    ip = komut[1]
                else:
                    yigin.pop()
            elif k == K.ATLA_DOGRU_TUT:
                if yigin[-1]:
                    ip = komut[1]
                else:
                    yigin.pop()
            elif k == K.ATLA_VAR_TUT:
                if yigin[-1] is not None:
                    ip = komut[1]
                else:
                    yigin.pop()

            # --- işlevler ---
            elif k == K.KAPAT:
                sablon = self.program.islevler[komut[1]]
                yakalanan = []
                for dis_yerel_mi, indis in sablon.yakalananlar:
                    if dis_yerel_mi:
                        yakalanan.append(cerceve.yereller[indis])
                    else:
                        yakalanan.append(cerceve.kapanis.yakalanan[indis])
                yigin.append(Kapanis(sablon, yakalanan))
            elif k == K.CAGIR:
                n = komut[1]
                args = yigin[len(yigin) - n:]
                del yigin[len(yigin) - n:]
                hedef = yigin.pop()
                yigin.append(self._cagriyi_yap(hedef, args))
            elif k == K.DON:
                return yigin.pop() if yigin else None
            elif k == K.YERLESIK:
                indis, n = komut[1] >> 8, komut[1] & 0xFF
                args = yigin[len(yigin) - n:]
                del yigin[len(yigin) - n:]
                yigin.append(self._yerlesik(indis, args))

            # --- veri yapıları ---
            elif k == K.LISTE:
                n = komut[1]
                ogeler = yigin[len(yigin) - n:]
                del yigin[len(yigin) - n:]
                yigin.append(ogeler)
            elif k == K.ESLEME:
                n = komut[1]
                duz = yigin[len(yigin) - 2 * n:]
                del yigin[len(yigin) - 2 * n:]
                yigin.append({duz[i]: duz[i + 1] for i in range(0, len(duz), 2)})
            elif k == K.DIZIN_OKU:
                dizin = yigin.pop()
                nesne = yigin.pop()
                yigin.append(self._dizin_oku(nesne, dizin))
            elif k == K.DIZIN_YAZ:
                deger = yigin.pop()
                dizin = yigin.pop()
                nesne = yigin.pop()
                self._dizin_yaz(nesne, dizin, deger)
            elif k == K.STRUCT:
                tip = sabitler[komut[1]]
                alan_adlari = self.program.struct_tarifleri[tip]
                n = len(alan_adlari)
                degerler = yigin[len(yigin) - n:]
                del yigin[len(yigin) - n:]
                yigin.append(NarStruct(tip, dict(zip(alan_adlari, degerler))))
            elif k == K.ALAN_OKU:
                ad = sabitler[komut[1]]
                nesne = yigin.pop()
                yigin.append(self._alan_oku(nesne, ad))
            elif k == K.ALAN_YAZ:
                ad = sabitler[komut[1]]
                deger = yigin.pop()
                nesne = yigin.pop()
                if not isinstance(nesne, NarStruct):
                    raise self.hata(f"'{ad}' alanı yazılamıyor: nesne değil")
                nesne.alanlar[ad] = deger
            elif k == K.VARYANT:
                tarif = sabitler[komut[1]]      # "Tip.Varyant:n"
                tip_varyant, _, sayi = tarif.rpartition(":")
                tip, _, varyant = tip_varyant.partition(".")
                n = int(sayi)
                yuk = yigin[len(yigin) - n:] if n else []
                if n:
                    del yigin[len(yigin) - n:]
                yigin.append(NarVaryant(tip, varyant, yuk))
            elif k == K.ETIKET:
                nesne = yigin.pop()
                yigin.append(nesne.varyant if isinstance(nesne, NarVaryant) else "")
            elif k == K.YUK_OKU:
                nesne = yigin[-1]
                yigin.append(nesne.yuk[komut[1]])
            elif k == K.ARALIK:
                dahil = yigin.pop()
                son = yigin.pop()
                bas = yigin.pop()
                yigin.append(list(range(bas, son + 1 if dahil else son)))

            elif k == K.DUR:
                return None
            else:
                raise self.hata(f"bilinmeyen komut: {k}")

        return None

    def _cagriyi_yap(self, hedef, args):
        if isinstance(hedef, Kapanis):
            if hedef.kendisi is not None:
                args = [hedef.kendisi] + args
            return self.cagir(hedef, args)
        raise self.hata(f"çağrılabilir değil: {metin(hedef)}")

    # --- veri erişimi -----------------------------------------------------

    def _dizin_oku(self, nesne, dizin):
        if isinstance(nesne, str):
            if not isinstance(dizin, int):
                raise self.hata("metin dizini tam sayı olmalı")
            if dizin < 0 or dizin >= len(nesne):
                raise self.hata(
                    f"metin dizini sınır dışı: {dizin} (uzunluk {len(nesne)})")
            return nesne[dizin]
        if isinstance(nesne, list):
            if dizin < 0 or dizin >= len(nesne):
                raise self.hata(
                    f"liste dizini sınır dışı: {dizin} (uzunluk {len(nesne)})")
            return nesne[dizin]
        if isinstance(nesne, dict):
            return nesne.get(dizin)
        if nesne is None:
            raise self.hata("none üzerinde dizin okunamaz")
        raise self.hata(f"dizinlenemez: {metin(nesne)}")

    def _dizin_yaz(self, nesne, dizin, deger):
        if isinstance(nesne, list):
            if dizin < 0 or dizin >= len(nesne):
                raise self.hata(
                    f"liste dizini sınır dışı: {dizin} (uzunluk {len(nesne)})")
            nesne[dizin] = deger
        elif isinstance(nesne, dict):
            nesne[dizin] = deger
        else:
            raise self.hata(f"dizine yazılamaz: {metin(nesne)}")

    def _alan_oku(self, nesne, ad):
        if isinstance(nesne, NarStruct):
            if ad in nesne.alanlar:
                return nesne.alanlar[ad]
            raise self.hata(f"'{nesne.tip}' tipinde '{ad}' alanı yok")
        if nesne is None:
            raise self.hata(f"none üzerinde '{ad}' okunamaz")
        raise self.hata(f"'{ad}' alanı okunamıyor: {metin(nesne)}")

    # --- yerleşikler ------------------------------------------------------

    def _yerlesik(self, indis: int, args: list):
        ad = YERLESIK_ADLAR[indis]
        islev = YERLESIKLER.get(ad)
        if islev is None:
            raise self.hata(f"yerleşik bulunamadı: {ad}")
        return islev(self, args)


# --- yerleşik işlevler ----------------------------------------------------
# Sıra önemli: bytecode indisle başvurur.

def _print(vm: VM, args):
    satir = " ".join(metin(a) for a in args)
    vm.cikti.append(satir)
    if vm.cikti_yaz:
        print(satir)
    return None


def _len(vm: VM, args):
    d = args[0]
    if isinstance(d, (str, list, dict)):
        return len(d)
    raise vm.hata(f"len() bu değere uygulanamaz: {metin(d)}")


def _int(vm: VM, args):
    d = args[0]
    if isinstance(d, bool):
        return 1 if d else 0
    if isinstance(d, (int, float)):
        return int(d)
    if isinstance(d, str):
        try:
            return int(d.strip())
        except ValueError:
            try:
                return int(float(d.strip()))
            except ValueError:
                return None
    return None


def _float(vm: VM, args):
    d = args[0]
    if isinstance(d, bool):
        return 1.0 if d else 0.0
    if isinstance(d, (int, float)):
        return float(d)
    if isinstance(d, str):
        try:
            return float(d.strip())
        except ValueError:
            return None
    return None


def _panic(vm: VM, args):
    raise vm.hata("panik: " + metin(args[0]))


def _assert(vm: VM, args):
    if not args[0]:
        mesaj = metin(args[1]) if len(args) > 1 else "doğrulama başarısız"
        raise vm.hata("doğrulama: " + mesaj)
    return None


def _sqrt(vm: VM, args):
    d = float(args[0])
    if d < 0:
        raise vm.hata("sqrt(): negatif sayının karekökü yok")
    return math.sqrt(d)


def _round(vm: VM, args):
    # Nar `.5` değerlerini yukarı yuvarlar (JavaScript gibi);
    # Python'un bankacı yuvarlamasından farklı.
    d = float(args[0])
    return int(math.floor(d + 0.5))


YERLESIKLER = {
    "print": _print,
    "str": lambda vm, a: metin(a[0]),
    "len": _len,
    "int": _int,
    "float": _float,
    "abs": lambda vm, a: abs(a[0]),
    "min": lambda vm, a: min(a[0], a[1]),
    "max": lambda vm, a: max(a[0], a[1]),
    "sqrt": _sqrt,
    "pow": lambda vm, a: float(a[0]) ** float(a[1]),
    "floor": lambda vm, a: int(math.floor(float(a[0]))),
    "ceil": lambda vm, a: int(math.ceil(float(a[0]))),
    "round": _round,
    "random": lambda vm, a: random.random(),
    "panic": _panic,
    "assert": _assert,
    "simdi": lambda vm, a: int(time.time() * 1000),
    "zamanMetni": lambda vm, a: time.strftime("%Y-%m-%d %H:%M:%S"),
    "koddan": lambda vm, a: chr(a[0]),
    "argumanlar": lambda vm, a: list(vm.argumanlar),
    "cik": lambda vm, a: sys.exit(a[0]),
}

# --- dosya, ortam ve kimlik ----------------------------------------------
# Bu işlevler `nar run` ile terminal programları yazarken gerekiyor.
# Tarayıcıya özgü olanlar (DOM) burada yok: VM'de sayfa yoktur.

def _dosya_oku(vm: VM, args):
    from pathlib import Path
    try:
        return Path(args[0]).read_text(encoding="utf-8-sig")
    except OSError:
        return None


def _dosya_yaz(vm: VM, args):
    from pathlib import Path
    try:
        Path(args[0]).write_text(args[1], encoding="utf-8")
        return True
    except OSError:
        return False


def _dosya_ekle(vm: VM, args):
    from pathlib import Path
    try:
        with open(Path(args[0]), "a", encoding="utf-8") as f:
            f.write(args[1])
        return True
    except OSError:
        return False


def _dosya_sil(vm: VM, args):
    from pathlib import Path
    try:
        Path(args[0]).unlink()
        return True
    except OSError:
        return False


def _klasor_listele(vm: VM, args):
    from pathlib import Path
    try:
        return sorted(p.name for p in Path(args[0]).iterdir())
    except OSError:
        return []


def _klasor_olustur(vm: VM, args):
    from pathlib import Path
    try:
        Path(args[0]).mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def _satir_oku(vm: VM, args):
    try:
        return input()
    except EOFError:
        return None


def _rastgele_metin(vm: VM, args):
    import secrets
    harfler = ("abcdefghijklmnopqrstuvwxyz"
               "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return "".join(secrets.choice(harfler) for _ in range(max(0, args[0])))


def _sha256(vm: VM, args):
    import hashlib
    return hashlib.sha256(str(args[0]).encode("utf-8")).hexdigest()


def _icerik_tipi(vm: VM, args):
    yol = str(args[0])
    nokta = yol.rfind(".")
    if nokta < 0:
        return "application/octet-stream"
    tablo = {
        "html": "text/html; charset=utf-8", "css": "text/css; charset=utf-8",
        "js": "text/javascript; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "txt": "text/plain; charset=utf-8", "svg": "image/svg+xml",
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "gif": "image/gif", "webp": "image/webp", "ico": "image/x-icon",
        "pdf": "application/pdf", "zip": "application/zip",
    }
    return tablo.get(yol[nokta + 1:].lower(), "application/octet-stream")


YERLESIKLER.update({
    "dosyaOku": _dosya_oku,
    "dosyaYaz": _dosya_yaz,
    "dosyaEkle": _dosya_ekle,
    "dosyaVarMi": lambda vm, a: __import__("pathlib").Path(a[0]).exists(),
    "dosyaSil": _dosya_sil,
    "klasorListele": _klasor_listele,
    "klasorMu": lambda vm, a: __import__("pathlib").Path(a[0]).is_dir(),
    "klasorOlustur": _klasor_olustur,
    "satirOku": _satir_oku,
    "tumGirdi": lambda vm, a: sys.stdin.read(),
    "ortam": lambda vm, a: __import__("os").environ.get(a[0]),
    "rastgeleMetin": _rastgele_metin,
    "sha256": _sha256,
    "icerikTipi": _icerik_tipi,
})


YERLESIK_ADLAR = list(YERLESIKLER.keys())
YERLESIK_INDISI = {ad: i for i, ad in enumerate(YERLESIK_ADLAR)}


# Ayrı iş parçacığı için istenen yığın boyutu. Derin özyineleme yapan
# programlar (ağaç gezme, özyinelemeli ayrıştırma) bunu gerektirir.
YIGIN_BOYUTU = 64 * 1024 * 1024


def calistir(program: Program, argumanlar: list | None = None,
             cikti_yaz: bool = True) -> VM:
    """Programı çalıştırır ve VM'i döndürür (çıktı `vm.cikti` içinde).

    Program büyük yığınlı ayrı bir iş parçacığında yürütülür: VM'in çağrı
    derinliği Python'un varsayılan yığınına değil, kendi sınırına
    (`COKDERIN`) bağlı olmalı.
    """
    vm = VM(program, argumanlar)
    vm.cikti_yaz = cikti_yaz

    sonuc: dict = {}

    def calis():
        onceki_sinir = sys.getrecursionlimit()
        sys.setrecursionlimit(max(onceki_sinir, COKDERIN * 8))
        try:
            vm.calistir()
        except BaseException as e:      # SystemExit de taşınmalı
            sonuc["hata"] = e
        finally:
            sys.setrecursionlimit(onceki_sinir)

    onceki_yigin = threading.stack_size()
    try:
        threading.stack_size(YIGIN_BOYUTU)
    except (ValueError, RuntimeError):
        pass                            # sistem izin vermiyorsa varsayılanla

    is_parcacigi = threading.Thread(target=calis, daemon=True)
    is_parcacigi.start()
    is_parcacigi.join()

    try:
        threading.stack_size(onceki_yigin)
    except (ValueError, RuntimeError):
        pass

    if "hata" in sonuc:
        hata = sonuc["hata"]
        if isinstance(hata, RecursionError):
            raise NarCalismaHatasi(
                "çağrı yığını çok derin (sonsuz özyineleme olabilir)")
        raise hata
    return vm
