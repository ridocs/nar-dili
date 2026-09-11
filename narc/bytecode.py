"""Nar bytecode'u — dilin kendi çalıştırma biçimi.

Nar şimdiye kadar yalnızca JavaScript üretiyordu; çalışmak için Node ya da
bir tarayıcı gerekiyordu. Bu modül dilin kendi komut kümesini tanımlar:
Nar programı önce bytecode'a çevrilir, sonra `narc/vm.py` içindeki sanal
makine onu doğrudan çalıştırır. Arada JavaScript yok.

TASARIM

Yığın makinesi. Kayıt makinesine göre üretimi çok daha basittir ve
Nar'ın ifade ağacı zaten yığın düzenine uyar: `a + b` → a yükle, b yükle,
TOPLA.

Her işlev kendi kod dizisini, sabit havuzunu ve yerel değişken sayısını
taşır. Çağrıda VM bir çerçeve (frame) açar.

SAYI TEMSİLİ

`Int` ve `Float` ayrı tiplerdir ve ayrı komutları vardır (`BOL` tam
bölme, `FBOL` ondalıklı). Tip denetleyici hangisinin kullanılacağını
zaten biliyor; VM'in çalışma anında tip bakması gerekmez.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum

# Bytecode dosya biçiminin sürümü. VM okurken buna bakar.
BICIM_SURUMU = 1
SIHIR = b"NARB"


class K(IntEnum):
    """Komutlar.

    Adlar kısa tutuldu: bytecode dökümü okunurken hizalı kalsın.
    Argümanı olan komutlar tek bir tamsayı argüman alır.
    """

    # --- yığın ---
    SABIT = 1          # sabit havuzundan yükle
    YOK = 2            # none
    DOGRU = 3
    YANLIS = 4
    AT = 5             # yığının tepesini at
    KOPYALA = 6

    # --- değişkenler ---
    YEREL_OKU = 10
    YEREL_YAZ = 11
    GLOBAL_OKU = 12
    GLOBAL_YAZ = 13
    KAPALI_OKU = 14    # closure'ın yakaladığı değer

    # --- aritmetik ---
    TOPLA = 20         # Int
    CIKAR = 21
    CARP = 22
    BOL = 23           # tam bölme
    MOD = 24
    FTOPLA = 25        # Float
    FCIKAR = 26
    FCARP = 27
    FBOL = 28
    FMOD = 29
    NEGATIF = 30
    FNEGATIF = 31
    METIN_EKLE = 32    # metin birleştirme

    # --- karşılaştırma ---
    ESIT = 40
    ESIT_DEGIL = 41
    KUCUK = 42
    KUCUK_ESIT = 43
    BUYUK = 44
    BUYUK_ESIT = 45
    DEGIL = 46

    # --- akış ---
    ATLA = 50
    ATLA_YANLIS = 51   # tepe yanlışsa atla (tepeyi atar)
    ATLA_DOGRU = 52
    ATLA_YANLIS_TUT = 53   # `&&` için: yanlışsa atla, tepeyi tutar
    ATLA_DOGRU_TUT = 54    # `||` için
    ATLA_VAR_TUT = 55      # `??` için: none değilse atla, tepeyi tutar

    # --- işlevler ---
    KAPAT = 60         # işlev şablonundan closure üret
    CAGIR = 61         # argüman sayısı
    DON = 62
    YERLESIK = 63      # yerleşik çağrısı (argüman sayısı ayrı bayt)

    # --- veri yapıları ---
    LISTE = 70         # n öğeyi listeye topla
    ESLEME = 71        # 2n öğeyi eşlemeye topla
    DIZIN_OKU = 72
    DIZIN_YAZ = 73
    STRUCT = 74        # sabit havuzundaki tarife göre struct kur
    ALAN_OKU = 75
    ALAN_YAZ = 76
    VARYANT = 77       # enum varyantı kur
    ETIKET = 78        # varyant adını yığına koy
    YUK_OKU = 79       # varyantın i. yükü
    METOT_CAGIR = 80   # struct/enum metodu

    # --- döngü yardımcıları ---
    ARALIK = 90        # (bas, son, dahil) → yineleyici listesi

    DUR = 99


# Argüman alan komutlar. Diğerleri tek baytlıktır.
ARGUMANLI = {
    K.SABIT, K.YEREL_OKU, K.YEREL_YAZ, K.GLOBAL_OKU, K.GLOBAL_YAZ,
    K.KAPALI_OKU, K.ATLA, K.ATLA_YANLIS, K.ATLA_DOGRU, K.ATLA_YANLIS_TUT,
    K.ATLA_DOGRU_TUT, K.ATLA_VAR_TUT, K.KAPAT, K.CAGIR, K.LISTE, K.ESLEME,
    K.STRUCT, K.ALAN_OKU, K.ALAN_YAZ, K.VARYANT, K.YUK_OKU, K.METOT_CAGIR,
    K.YERLESIK, K.KOPYALA,
}


@dataclass
class Islev:
    """Derlenmiş bir işlev.

    `kod` komut listesidir: her öğe ya `(komut, arg)` ya da `(komut,)`.
    Yazma/okuma sırasında düz bayt dizisine çevrilir.
    """

    ad: str
    parametre_sayisi: int = 0
    yerel_sayisi: int = 0
    kod: list = field(default_factory=list)
    sabitler: list = field(default_factory=list)
    # Bu işlevin dıştaki hangi yerelleri yakaladığı: (dis_yerel_mi, indis)
    yakalananlar: list = field(default_factory=list)
    # Hata iletisi için: her komutun kaynak satırı
    satirlar: list = field(default_factory=list)

    def sabit_ekle(self, deger) -> int:
        """Sabiti havuza koyar, indisini döndürür. Aynısı varsa yeniden kullanır."""
        # Bool ve int Python'da eşit sayılabilir (True == 1); tip de eşleşmeli.
        for i, mevcut in enumerate(self.sabitler):
            if type(mevcut) is type(deger) and mevcut == deger:
                return i
        self.sabitler.append(deger)
        return len(self.sabitler) - 1

    def yaz(self, komut: K, arg: int | None = None, satir: int = 0) -> int:
        """Komutu ekler ve yerini döndürür (atlama yamalamak için)."""
        self.kod.append((komut, arg) if arg is not None else (komut,))
        self.satirlar.append(satir)
        return len(self.kod) - 1

    def yamala(self, yer: int, hedef: int) -> None:
        """Daha önce yazılmış bir atlamanın hedefini düzeltir."""
        komut = self.kod[yer][0]
        self.kod[yer] = (komut, hedef)

    def __repr__(self) -> str:
        return f"Islev({self.ad!r}, {len(self.kod)} komut)"


@dataclass
class Program:
    """Bir bütün olarak derlenmiş program."""

    ana: Islev                       # `main`
    islevler: list = field(default_factory=list)
    global_adlar: list = field(default_factory=list)
    # Struct tarifleri: ad → alan adları (sıralı)
    struct_tarifleri: dict = field(default_factory=dict)
    # Enum tarifleri: ad → {varyant: yük sayısı}
    enum_tarifleri: dict = field(default_factory=dict)


def dokum(islev: Islev, girinti: str = "") -> str:
    """İşlevin bytecode'unu okunabilir biçimde yazar.

    Hata ayıklarken ve `nar bytecode` komutunda kullanılır.
    """
    satirlar = [f"{girinti}işlev {islev.ad}  "
                f"({islev.parametre_sayisi} parametre, "
                f"{islev.yerel_sayisi} yerel)"]
    for i, komut in enumerate(islev.kod):
        ad = K(komut[0]).name
        if len(komut) > 1:
            ek = ""
            if komut[0] == K.SABIT and komut[1] < len(islev.sabitler):
                ek = f"   ; {islev.sabitler[komut[1]]!r}"
            satirlar.append(f"{girinti}  {i:4}  {ad:<16} {komut[1]}{ek}")
        else:
            satirlar.append(f"{girinti}  {i:4}  {ad}")
    return "\n".join(satirlar)


# --- dosya biçimi ---------------------------------------------------------
# `.narb` dosyası: sihirli sayı, sürüm, ardından JSON gövde. JSON seçildi
# çünkü okunabilir ve Python'un kendi araçlarıyla incelenebilir; hız
# gerektiğinde ikili bir biçime geçmek kolay.


def yaz_dosya(program: Program) -> bytes:
    """Programı `.narb` baytlarına çevirir."""
    import json

    def islev_sozlugu(f: Islev) -> dict:
        return {
            "ad": f.ad,
            "parametre_sayisi": f.parametre_sayisi,
            "yerel_sayisi": f.yerel_sayisi,
            "kod": [list(k) for k in f.kod],
            "sabitler": [_sabit_yaz(s) for s in f.sabitler],
            "yakalananlar": f.yakalananlar,
            "satirlar": f.satirlar,
        }

    govde = {
        "ana": islev_sozlugu(program.ana),
        "islevler": [islev_sozlugu(f) for f in program.islevler],
        "global_adlar": program.global_adlar,
        "struct_tarifleri": program.struct_tarifleri,
        "enum_tarifleri": program.enum_tarifleri,
    }
    veri = json.dumps(govde, ensure_ascii=False).encode("utf-8")
    return SIHIR + struct.pack("<I", BICIM_SURUMU) + veri


def oku_dosya(baytlar: bytes) -> Program:
    """`.narb` baytlarını programa çevirir."""
    import json

    if not baytlar.startswith(SIHIR):
        raise ValueError("bu bir Nar bytecode dosyası değil")
    surum = struct.unpack("<I", baytlar[4:8])[0]
    if surum > BICIM_SURUMU:
        raise ValueError(
            f"bytecode biçimi {surum}, bu sürüm en çok {BICIM_SURUMU} okuyor")

    govde = json.loads(baytlar[8:].decode("utf-8"))

    def islev_oku(d: dict) -> Islev:
        return Islev(
            ad=d["ad"],
            parametre_sayisi=d["parametre_sayisi"],
            yerel_sayisi=d["yerel_sayisi"],
            kod=[tuple(k) for k in d["kod"]],
            sabitler=[_sabit_oku(s) for s in d["sabitler"]],
            yakalananlar=[tuple(y) for y in d["yakalananlar"]],
            satirlar=d.get("satirlar", []),
        )

    return Program(
        ana=islev_oku(govde["ana"]),
        islevler=[islev_oku(f) for f in govde["islevler"]],
        global_adlar=govde["global_adlar"],
        struct_tarifleri=govde["struct_tarifleri"],
        enum_tarifleri=govde["enum_tarifleri"],
    )


def _sabit_yaz(deger):
    """Sabiti JSON'a yazılabilir biçime çevirir.

    Int ve Float JSON'da ayrışmaz (`1` ile `1.0`); tip etiketi gerekiyor.
    """
    if isinstance(deger, bool):
        return {"t": "b", "v": deger}
    if isinstance(deger, int):
        return {"t": "i", "v": deger}
    if isinstance(deger, float):
        return {"t": "f", "v": deger}
    if isinstance(deger, str):
        return {"t": "s", "v": deger}
    if deger is None:
        return {"t": "n"}
    raise TypeError(f"bytecode'a yazılamayan sabit: {deger!r}")


def _sabit_oku(d):
    tur = d["t"]
    if tur == "b":
        return bool(d["v"])
    if tur == "i":
        return int(d["v"])
    if tur == "f":
        return float(d["v"])
    if tur == "s":
        return d["v"]
    return None
