"""Nar kaynağını renklendirilmiş HTML'e çevirir.

Belgeler sitesi bunu kullanır. Lexer'dan farklı olarak yorumları ve
boşlukları da korur; amacı çözümleme değil, göstermektir.
"""

from __future__ import annotations

import html
import re

from .checker import BUILTIN_NAMES
from .lexer import KEYWORDS
from .types import PRIMITIVES

TIPLER = set(PRIMITIVES) | {"Void"}

TOKEN_RE = re.compile(
    r"""
      (?P<comment>//[^\n]*|/\*.*?\*/)
    | (?P<string>"(?:[^"\\\n]|\\.)*")
    | (?P<number>\b0[xXbBoO][0-9a-fA-F_]+\b|\b\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?\b)
    | (?P<word>[^\W\d]\w*)
    # Operatör tek karakter olmalı: açgözlü eşleşme `("` gibi dizilerde
    # tırnağı yutup metin literalinin başlangıcını yok ediyordu.
    | (?P<op>[^\w\s])
    """,
    re.VERBOSE | re.DOTALL,
)


def _kelime_sinifi(kelime: str, sonrasi: str) -> str | None:
    if kelime in KEYWORDS:
        return "n-kw"
    if kelime in TIPLER:
        return "n-tip"
    if kelime in BUILTIN_NAMES:
        return "n-yerlesik"
    if sonrasi.lstrip().startswith("("):
        return "n-fn"
    if kelime[:1].isupper():
        return "n-tip"
    return None


def renklendir(kaynak: str) -> str:
    """Kaynağı `<span>`'lı HTML'e çevirir. Girdi metni kaçışlanır."""
    parcalar: list[str] = []
    son = 0

    for eslesme in TOKEN_RE.finditer(kaynak):
        if eslesme.start() > son:
            parcalar.append(html.escape(kaynak[son:eslesme.start()]))
        son = eslesme.end()
        metin = eslesme.group()
        tur = eslesme.lastgroup

        if tur == "comment":
            sinif = "n-yorum"
        elif tur == "string":
            sinif = "n-metin"
        elif tur == "number":
            sinif = "n-sayi"
        elif tur == "word":
            sinif = _kelime_sinifi(metin, kaynak[eslesme.end():eslesme.end() + 4])
        else:
            sinif = "n-op" if metin.strip() else None

        kacisli = html.escape(metin)
        parcalar.append(f'<span class="{sinif}">{kacisli}</span>' if sinif else kacisli)

    if son < len(kaynak):
        parcalar.append(html.escape(kaynak[son:]))
    return "".join(parcalar)
