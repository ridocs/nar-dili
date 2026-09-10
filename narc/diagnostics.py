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

    def __init__(self, message: str, span: Span | None = None, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span
        self.hint = hint

    def render(self, source: str | None = None) -> str:
        """Hatayı, varsa kaynak satırını ve işaretçiyi de içerecek şekilde biçimler."""
        head = f"hata: {self.message}"
        if self.span is None:
            return head

        out = [f"{self.span} — {self.message}"]
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
