"""Sözdizimi renklendirme — Nar ile yazılmış renklendiriciyi çağırır.

Renklendiricinin kendisi `araclar/renklendirici.nar` dosyasındadır. Bu
modül onu kütüphane olarak derleyip Node üzerinden çalıştırır; böylece
IDE ile belgeler sitesi **aynı** renklendiriciyi kullanır ve ikisi
arasında sessizce fark oluşamaz.

Site üretimi yüzlerce kod bloğu renklendirdiği için her blok başına bir
Node süreci açmak yavaş olurdu; `renklendir_toplu` hepsini tek çağrıda
yollar.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .diagnostics import NarError

KOK = Path(__file__).resolve().parent.parent
RENKLENDIRICI_NAR = KOK / "araclar" / "renklendirici.nar"
ONBELLEK = KOK / ".narbuild" / "renklendirici.js"

_bellek: dict[str, object] = {"imza": None}


class RenkHatasi(Exception):
    """Renklendirici çalıştırılamadı."""


def _imza() -> tuple:
    zamanlar = []
    for yol in (RENKLENDIRICI_NAR, KOK / "araclar" / "tarayici.nar"):
        try:
            zamanlar.append(yol.stat().st_mtime)
        except OSError:
            zamanlar.append(0.0)
    return tuple(zamanlar)


def _hazirla() -> Path:
    """Renklendiriciyi derleyip önbelleğe yazar, betik yolunu döndürür."""
    imza = _imza()
    if _bellek["imza"] == imza and ONBELLEK.exists():
        return ONBELLEK

    if not RENKLENDIRICI_NAR.exists():
        raise RenkHatasi(f"renklendirici bulunamadı: {RENKLENDIRICI_NAR}")

    from .driver import compile_file

    try:
        kod = compile_file(RENKLENDIRICI_NAR, kutuphane=True).to_js()
    except NarError as err:
        raise RenkHatasi(
            "renklendiricinin kendisi derlenemedi:\n" + err.render()
        ) from None

    ONBELLEK.parent.mkdir(parents=True, exist_ok=True)
    ONBELLEK.write_text(kod, encoding="utf-8")
    _bellek["imza"] = imza
    return ONBELLEK


def renklendir_toplu(kaynaklar: list[str]) -> list[str]:
    """Birden çok kaynağı tek Node çağrısında renklendirir."""
    if not kaynaklar:
        return []

    node = shutil.which("node")
    if node is None:
        raise RenkHatasi("'node' bulunamadı; renklendirme için Node.js gerekir")

    betik_yolu = str(_hazirla()).replace("\\", "/")
    surucu = (
        f"require({betik_yolu!r});\n"
        "let veri = '';\n"
        "process.stdin.setEncoding('utf8');\n"
        "process.stdin.on('data', (p) => { veri += p; });\n"
        "process.stdin.on('end', () => {\n"
        "  const girdi = JSON.parse(veri);\n"
        "  const cikti = girdi.map((k) => Nar.renklendir(k));\n"
        "  process.stdout.write(JSON.stringify(cikti));\n"
        "});\n"
    )

    sonuc = subprocess.run(
        [node, "-e", surucu],
        input=json.dumps(kaynaklar), capture_output=True, text=True,
        encoding="utf-8", timeout=120,
    )
    if sonuc.returncode != 0:
        raise RenkHatasi("renklendirme başarısız:\n" + sonuc.stderr.strip())

    try:
        return json.loads(sonuc.stdout)
    except ValueError as err:  # pragma: no cover - Node bozuk çıktı verirse
        raise RenkHatasi(f"renklendirici çıktısı okunamadı: {err}") from None


def renklendir(kaynak: str) -> str:
    """Tek bir kaynağı renklendirir."""
    return renklendir_toplu([kaynak])[0]
