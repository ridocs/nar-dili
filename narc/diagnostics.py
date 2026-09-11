"""Hata konumu ve kullanıcıya gösterilen tanı mesajları."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """Kaynak dosyada bir aralık. Satır ve sütun 1 tabanlıdır."""

    filename: str
    line: int
    col: int
    length: int = 1

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.col}"


class NarError(Exception):
    """Derleme hatası. Kaynak konumu ve isteğe bağlı ipucu taşır."""

    # "hata" derlemeyi durdurur; "uyari" durdurmaz, yalnızca söyler.
    seviye = "hata"

    def __init__(self, message: str, span: Span | None = None, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span
        self.hint = hint

    def render(self, source: str | None = None) -> str:
        """Hatayı, varsa kaynak satırını ve işaretçiyi de içerecek şekilde biçimler."""
        etiket = "uyarı" if self.seviye == "uyari" else "hata"
        head = f"{etiket}: {self.message}"
        if self.span is None:
            return head

        baslik = f"{self.span} — {self.message}"
        if self.seviye == "uyari":
            baslik = f"{self.span} — uyarı: {self.message}"
        out = [baslik]
        if source is not None:
            lines = source.splitlines()
            index = self.span.line - 1
            if 0 <= index < len(lines):
                line_text = lines[index].replace("\t", " ")
                gutter = str(self.span.line)
                pad = " " * len(gutter)
                out.append(f" {pad} |")
                out.append(f" {gutter} | {line_text}")
                caret = " " * (self.span.col - 1) + "^" * max(1, self.span.length)
                out.append(f" {pad} | {caret}")
        if self.hint:
            out.append(f"  ipucu: {self.hint}")
        return "\n".join(out)


class NarUyari(NarError):
    """Derlemeyi durdurmayan bildirim. Aynı biçimde yazılır, farklı etiketle."""

    seviye = "uyari"


class NarErrors(NarError):
    """Birden çok derleme hatası.

    `NarError`'dan türer: ilk hatanın mesajını ve konumunu taşır, böylece
    yalnızca tek hata bekleyen çağıranlar değişmeden çalışmaya devam eder.
    Hepsini görmek isteyen `errors` listesine ya da `render_all()`'a bakar.
    """

    def __init__(self, errors: list[NarError]) -> None:
        if not errors:  # pragma: no cover - çağıran boş liste vermez
            raise ValueError("NarErrors boş liste ile oluşturulamaz")
        ilk = errors[0]
        super().__init__(ilk.message, ilk.span, ilk.hint)
        self.errors = errors

    def render_all(self, sources: dict[str, str] | None = None) -> str:
        """Tüm hataları alt alta biçimler."""
        sources = sources or {}
        parcalar = []
        for hata in self.errors:
            kaynak = sources.get(hata.span.filename) if hata.span else None
            parcalar.append(hata.render(kaynak))
        adet = len(self.errors)
        if adet > 1:
            parcalar.append(f"\n{adet} hata bulundu.")
        return "\n\n".join(parcalar)


def duzenle(errors: list[NarError]) -> list[NarError]:
    """Hataları konuma göre sıralar ve birebir aynı olanları teke indirir."""
    gorulmus: set[tuple] = set()
    benzersiz: list[NarError] = []
    for hata in errors:
        anahtar = (
            hata.span.filename if hata.span else "",
            hata.span.line if hata.span else 0,
            hata.span.col if hata.span else 0,
            hata.message,
        )
        if anahtar in gorulmus:
            continue
        gorulmus.add(anahtar)
        benzersiz.append(hata)

    benzersiz.sort(key=lambda h: (
        h.span.filename if h.span else "",
        h.span.line if h.span else 0,
        h.span.col if h.span else 0,
    ))
    return benzersiz
