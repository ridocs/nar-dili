"""Tip sistemini sınamak için sabit bir tip listesi.

`testler/nar/tip_ornekleri.nar` **birebir aynı** listeyi kurar. Böylece iki
tip sistemi, tarif alışverişine gerek kalmadan aynı tipler üzerinde
karşılaştırılabilir: i. tip iki tarafta da aynı tiptir.

Liste sıralaması testin sözleşmesidir; ortaya eleman eklenmez, sona eklenir.
"""

from __future__ import annotations

from .types import (
    ANY, BOOL, ELEMENT, FLOAT, INT, NEVER, NONE, OLAY, STRING, VOID,
    EnumT, FnT, InterfaceT, ListT, MapT, OptT, RangeT, StructT, TypeVar,
    uygula_enum, uygula_struct,
)


def ornek_struct() -> StructT:
    return StructT(
        "Nokta",
        fields={"x": INT, "y": INT},
        mutable_fields={"x"},
        methods={"yaz": FnT((), STRING)},
        interfaces=("Yazdirilabilir",),
    )


def kutu_sablonu() -> StructT:
    """`struct Kutu<T> { deger: T }`"""
    return StructT(
        "Kutu",
        fields={"deger": TypeVar("T")},
        methods={"al": FnT((), TypeVar("T"))},
        type_params=("T",),
    )


def ornek_enum() -> EnumT:
    return EnumT(
        "Hava",
        variants={"Gunesli": (), "Yagmurlu": (INT,)},
    )


def sonuc_sablonu() -> EnumT:
    """`enum Sonuc<T, H> { Tamam(T)  Hata(H) }`"""
    return EnumT(
        "Sonuc",
        variants={"Tamam": (TypeVar("T"),), "Hata": (TypeVar("H"),)},
        type_params=("T", "H"),
    )


def ornek_arayuz() -> InterfaceT:
    return InterfaceT("Yazdirilabilir", methods={"yaz": FnT((), STRING)})


def ornek_tipler() -> list:
    nokta = ornek_struct()
    kutu = kutu_sablonu()
    hava = ornek_enum()
    sonuc = sonuc_sablonu()

    return [
        INT,                                        # 0
        FLOAT,                                      # 1
        BOOL,                                       # 2
        STRING,                                     # 3
        VOID,                                       # 4
        ELEMENT,                                    # 5
        OLAY,                                       # 6
        NONE,                                       # 7
        NEVER,                                      # 8
        ANY,                                        # 9
        ListT(INT),                                 # 10
        ListT(STRING),                              # 11
        ListT(ListT(INT)),                          # 12
        MapT(STRING, INT),                          # 13
        MapT(INT, ListT(STRING)),                   # 14
        OptT(INT),                                  # 15
        OptT(STRING),                               # 16
        OptT(ListT(INT)),                           # 17
        FnT((), VOID),                              # 18
        FnT((INT,), BOOL),                          # 19
        FnT((INT, STRING), VOID),                   # 20
        FnT((OLAY,), VOID),                         # 21
        FnT((), INT),                               # 22
        RangeT(INT),                                # 23
        TypeVar("T"),                               # 24
        TypeVar("U"),                               # 25
        nokta,                                      # 26
        kutu,                                       # 27  (uygulanmamış şablon)
        uygula_struct(kutu, (INT,)),                # 28
        uygula_struct(kutu, (STRING,)),             # 29
        uygula_struct(kutu, (TypeVar("T"),)),       # 30
        hava,                                       # 31
        sonuc,                                      # 32
        uygula_enum(sonuc, (INT, STRING)),          # 33
        uygula_enum(sonuc, (STRING, INT)),          # 34
        ornek_arayuz(),                             # 35
        OptT(nokta),                                # 36
        ListT(uygula_struct(kutu, (INT,))),         # 37
        FnT((TypeVar("T"),), TypeVar("T")),         # 38
        MapT(STRING, OptT(INT)),                    # 39
    ]
