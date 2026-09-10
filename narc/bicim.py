"""`nar fmt` — kod biçimlendirme.

Biçimlendiricinin kendisi **Nar diliyle** yazılmıştır
(`araclar/bicimlendirici.nar`). Bu modül onu kütüphane olarak derler ve
Node üzerinden çalıştırır; sonucu Python tarafına geri getirir.

Derlenmiş JavaScript önbelleğe alınır, kaynak değişince yenilenir.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .backends import js as js_backend
from .checker import Checker
from .diagnostics import NarError
from .parser import parse

KOK = Path(__file__).resolve().parent.parent
BICIMLENDIRICI_NAR = KOK / "araclar" / "bicimlendirici.nar"
ONBELLEK = KOK / ".narbuild" / "bicimlendirici.js"

_bellek: dict[str, object] = {"mtime": None, "js": ""}


class BicimHatasi(Exception):
    """Biçimlendirici çalıştırılamadı."""


def _kaynak_zamani() -> float:
    """Biçimlendirici ve bağımlılıklarının en yeni değişiklik zamanı."""
    en_yeni = 0.0
    for yol in (BICIMLENDIRICI_NAR, KOK / "araclar" / "tarayici.nar"):
        try:
            en_yeni = max(en_yeni, yol.stat().st_mtime)
        except OSError:
            pass
    return en_yeni


def bicimlendirici_js() -> str:
    """`bicimlendirici.nar`'ı kütüphane olarak derler (önbellekli)."""
    mtime = _kaynak_zamani()
    if _bellek["mtime"] == mtime and _bellek["js"]:
        return _bellek["js"]  # type: ignore[return-value]

    if not BICIMLENDIRICI_NAR.exists():
        raise BicimHatasi(f"biçimlendirici bulunamadı: {BICIMLENDIRICI_NAR}")

    kaynak = BICIMLENDIRICI_NAR.read_text(encoding="utf-8-sig")
    # `import` çözümlemesi için tam derleme sürücüsünü kullanırız.
    from .driver import compile_file

    derleme = compile_file(BICIMLENDIRICI_NAR, kutuphane=True)
    kod = derleme.to_js()

    ONBELLEK.parent.mkdir(parents=True, exist_ok=True)
    ONBELLEK.write_text(kod, encoding="utf-8")
    _bellek["mtime"] = mtime
    _bellek["js"] = kod
    return kod


def bicimlendir(kaynak: str) -> str:
    """Nar kaynağını biçimlendirilmiş hâliyle döndürür."""
    node = shutil.which("node")
    if node is None:
        raise BicimHatasi("'node' bulunamadı; biçimlendirme için Node.js gerekir")

    try:
        bicimlendirici_js()
    except NarError as err:
        raise BicimHatasi(
            "biçimlendiricinin kendisi derlenemedi:\n" + err.render()
        ) from None

    surucu = (
        f"require({str(ONBELLEK).replace(chr(92), '/')!r});\n"
        "let veri = '';\n"
        "process.stdin.setEncoding('utf8');\n"
        "process.stdin.on('data', (p) => { veri += p; });\n"
        "process.stdin.on('end', () => {\n"
        "  process.stdout.write(Nar.bicimlendir(veri));\n"
        "});\n"
    )

    sonuc = subprocess.run(
        [node, "-e", surucu],
        input=kaynak, capture_output=True, text=True, encoding="utf-8",
        timeout=30,
    )
    if sonuc.returncode != 0:
        raise BicimHatasi("biçimlendirme başarısız:\n" + sonuc.stderr.strip())
    return sonuc.stdout
