"""Sanal makinenin metot yerleşikleri.

Nar'da `"abc".upper()` ya da `[1,2].toplam()` gibi çağrılar metot
görünümündedir ama tip başına tablolarla çözülür. VM'de bunlar alıcıyı
ilk argüman alan işlevlerdir; bytecode üreticisi `m_upper`, `m_toplam`
adlarıyla çağırır.

Davranışlar JavaScript arka ucundaki karşılıklarıyla **aynı** olmak
zorunda: aynı program iki hedefte de aynı sonucu vermeli. Ayrıştıkları
yerler (Türkçe büyük/küçük harf, tam bölme, yuvarlama) burada açıkça
uygulanır.
"""

from __future__ import annotations

import math

from .vm import NarStruct, NarVaryant, Kapanis, metin

# Türkçe büyük/küçük harf: `i` → `İ`, `I` → `ı`. Bu eşleme olmadan
# "istanbul".upperTr() yanlış sonuç verir.
_TR_BUYUK = {"i": "İ", "ı": "I"}
_TR_KUCUK = {"I": "ı", "İ": "i"}


def _upper_tr(s: str) -> str:
    return "".join(_TR_BUYUK.get(c, c) for c in s).upper()


def _lower_tr(s: str) -> str:
    return "".join(_TR_KUCUK.get(c, c) for c in s).lower()


def _dilim(uzunluk: int, bas: int, son: int) -> tuple[int, int]:
    """Dilim sınırlarını kırpar; taşma hata değil, boş dilim verir."""
    bas = max(0, min(bas, uzunluk))
    son = max(bas, min(son, uzunluk))
    return bas, son


def _sayisal_liste(vm, l: list, ad: str) -> list:
    if any(not isinstance(o, (int, float)) or isinstance(o, bool) for o in l):
        raise vm.hata(f"{ad}(): liste sayı içermeli")
    return l


# --- metin ----------------------------------------------------------------

METIN_METOTLARI = {
    "m_len": lambda vm, a: len(a[0]),
    "m_upper": lambda vm, a: a[0].upper(),
    "m_lower": lambda vm, a: a[0].lower(),
    "m_upperTr": lambda vm, a: _upper_tr(a[0]),
    "m_lowerTr": lambda vm, a: _lower_tr(a[0]),
    "m_trim": lambda vm, a: a[0].strip(),
    "m_contains": lambda vm, a: a[1] in a[0],
    "m_startsWith": lambda vm, a: a[0].startswith(a[1]),
    "m_endsWith": lambda vm, a: a[0].endswith(a[1]),
    "m_indexOf": lambda vm, a: a[0].find(a[1]),
    "m_repeat": lambda vm, a: a[0] * max(0, a[1]),
    "m_kodu": lambda vm, a: ord(a[0][0]) if a[0] else 0,
}


def _m_split(vm, a):
    metin_, ayirac = a[0], a[1]
    if ayirac == "":
        return list(metin_)
    return metin_.split(ayirac)


def _m_replace(vm, a):
    return a[0].replace(a[1], a[2])


def _m_slice(vm, a):
    bas, son = _dilim(len(a[0]), a[1], a[2])
    return a[0][bas:son]


def _m_charAt(vm, a):
    i = a[1]
    return a[0][i] if 0 <= i < len(a[0]) else ""


# --- liste ----------------------------------------------------------------

def _m_push(vm, a):
    a[0].append(a[1])
    return None


def _m_pop(vm, a):
    return a[0].pop() if a[0] else None


def _m_liste_slice(vm, a):
    bas, son = _dilim(len(a[0]), a[1], a[2])
    return a[0][bas:son]


def _m_sort(vm, a):
    """Yeni bir sıralı liste döndürür; özgün liste değişmez."""
    l = list(a[0])
    try:
        return sorted(l)
    except TypeError:
        raise vm.hata("sort(): liste karşılaştırılabilir öğeler içermeli")


def _m_map(vm, a):
    liste, islev = a[0], a[1]
    return [vm._cagriyi_yap(islev, [o]) for o in liste]


def _m_filter(vm, a):
    liste, islev = a[0], a[1]
    return [o for o in liste if vm._cagriyi_yap(islev, [o])]


def _m_reduce(vm, a):
    liste, islev, baslangic = a[0], a[1], a[2]
    toplam = baslangic
    for o in liste:
        toplam = vm._cagriyi_yap(islev, [toplam, o])
    return toplam


def _m_ortalama(vm, a):
    l = _sayisal_liste(vm, a[0], "ortalama")
    if not l:
        return 0.0
    return float(sum(l)) / len(l)


LISTE_METOTLARI = {
    "m_push": _m_push,
    "m_pop": _m_pop,
    "m_contains": lambda vm, a: a[1] in a[0],
    "m_indexOf": lambda vm, a: a[0].index(a[1]) if a[1] in a[0] else -1,
    "m_reverse": lambda vm, a: list(reversed(a[0])),
    "m_first": lambda vm, a: a[0][0] if a[0] else None,
    "m_last": lambda vm, a: a[0][-1] if a[0] else None,
    "m_join": lambda vm, a: a[1].join(metin(o) for o in a[0]),
    "m_sort": _m_sort,
    "m_map": _m_map,
    "m_filter": _m_filter,
    "m_reduce": _m_reduce,
    # Lambda gerektirmeyen kolay işlemler
    "m_benzersiz": lambda vm, a: list(dict.fromkeys(a[0])),
    "m_say": lambda vm, a: a[0].count(a[1]),
    "m_toplam": lambda vm, a: sum(_sayisal_liste(vm, a[0], "toplam")),
    "m_carpim": lambda vm, a: math.prod(_sayisal_liste(vm, a[0], "carpim")),
    "m_ortalama": _m_ortalama,
    "m_enBuyuk": lambda vm, a: max(a[0]) if a[0] else None,
    "m_enKucuk": lambda vm, a: min(a[0]) if a[0] else None,
    "m_kat": lambda vm, a: [o * a[1] for o in a[0]],
    "m_artir": lambda vm, a: [o + a[1] for o in a[0]],
    "m_buyukler": lambda vm, a: [o for o in a[0] if o > a[1]],
    "m_kucukler": lambda vm, a: [o for o in a[0] if o < a[1]],
    "m_ciftler": lambda vm, a: [o for o in a[0] if o % 2 == 0],
    "m_tekler": lambda vm, a: [o for o in a[0] if o % 2 != 0],
    "m_buyukHarf": lambda vm, a: [str(o).upper() for o in a[0]],
    "m_kucukHarf": lambda vm, a: [str(o).lower() for o in a[0]],
    "m_icerenler": lambda vm, a: [o for o in a[0] if a[1] in o],
}


# --- eşleme ---------------------------------------------------------------

def _m_set(vm, a):
    a[0][a[1]] = a[2]
    return None


def _m_remove(vm, a):
    a[0].pop(a[1], None)
    return None


ESLEME_METOTLARI = {
    "m_get": lambda vm, a: a[0].get(a[1]),
    "m_set": _m_set,
    "m_has": lambda vm, a: a[1] in a[0],
    "m_remove": _m_remove,
    "m_keys": lambda vm, a: list(a[0].keys()),
    "m_values": lambda vm, a: list(a[0].values()),
}


# --- ortak: alıcının tipine göre seçilenler ------------------------------
# `len`, `contains`, `indexOf`, `slice` hem metinde hem listede var.

def _ortak_len(vm, a):
    d = a[0]
    if isinstance(d, (str, list, dict)):
        return len(d)
    raise vm.hata(f"len(): uygulanamaz: {metin(d)}")


def _ortak_contains(vm, a):
    return a[1] in a[0]


def _ortak_indexOf(vm, a):
    d = a[0]
    if isinstance(d, str):
        return d.find(a[1])
    return d.index(a[1]) if a[1] in d else -1


def _ortak_slice(vm, a):
    bas, son = _dilim(len(a[0]), a[1], a[2])
    return a[0][bas:son]


def _ortak_len_liste(vm, a):
    return _ortak_len(vm, a)


# --- üreticinin çağırdığı yardımcılar -------------------------------------

def _harfler(vm, a):
    """Metni harf listesine çevirir — `for c in metin` için."""
    return list(a[0])


def _anahtarlar(vm, a):
    return list(a[0].keys())


def _liste_birlestir(vm, a):
    return list(a[0]) + list(a[1])


def _zorla_ac(vm, a):
    """`x!` — opsiyoneli zorla açar.

    `none` ise burada durmak, değeri sessizce geçirip hatanın çok sonra
    anlamsız bir yerde çıkmasından iyidir.
    """
    if a[0] is None:
        raise vm.hata("'!' ile açılan değer none")
    return a[0]


EK_YERLESIKLER = {
    **METIN_METOTLARI,
    **LISTE_METOTLARI,
    **ESLEME_METOTLARI,
    "m_split": _m_split,
    "m_replace": _m_replace,
    "m_slice": _ortak_slice,
    "m_charAt": _m_charAt,
    "m_len": _ortak_len,
    "m_contains": _ortak_contains,
    "m_indexOf": _ortak_indexOf,
    # üretici içi
    "harfler": _harfler,
    "anahtarlar": _anahtarlar,
    "listeBirlestir": _liste_birlestir,
    "zorlaAc": _zorla_ac,
}


def kur() -> None:
    """Metot yerleşiklerini VM ve üretici tablolarına ekler.

    Ayrı bir işlev olmasının nedeni döngüsel içe aktarmayı önlemek:
    `vm` modülü bu dosyayı bilmez, bu dosya `vm`'i bilir.
    """
    from . import vm as vm_modulu
    from .backends import bytecode_uretici

    for ad, islev in EK_YERLESIKLER.items():
        if ad not in vm_modulu.YERLESIKLER:
            vm_modulu.YERLESIKLER[ad] = islev
            vm_modulu.YERLESIK_ADLAR.append(ad)
            vm_modulu.YERLESIK_INDISI[ad] = len(vm_modulu.YERLESIK_ADLAR) - 1

    bytecode_uretici.EK_YERLESIK_INDISI.clear()
    bytecode_uretici.EK_YERLESIK_INDISI.update(vm_modulu.YERLESIK_INDISI)
