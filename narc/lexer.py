"""Nar sözcüksel çözümleyici (lexer).

Kaynak metni token akışına çevirir. Her token kaynaktaki satır/sütun bilgisini
taşır; hata mesajları bu konumu kullanır.
"""

from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import NarError, Span

KEYWORDS = {
    "let", "var", "fn", "return", "if", "else", "while", "for", "in",
    "match", "struct", "enum", "import", "true", "false", "none",
    "self", "break", "continue", "type", "interface",
}

# Bu tokenlardan sonra gelen satır sonu bir deyimi bitirebilir (Go kuralı).
# Diğer durumlarda satır sonu yutulur, böylece ifadeler satıra bölünebilir.
NEWLINE_TERMINATORS = {
    "ident", "int", "float", "string", "true", "false", "none", "self",
    "break", "continue", "return", ")", "]", "}", "?", "!",
}

# Uzundan kısaya sıralı: eşleştirme sırası önemlidir.
OPERATORS = [
    "..=", "?.", "??", "->", "=>", "==", "!=", "<=", ">=", "&&", "||", "..",
    "+=", "-=", "*=", "/=", "%=",
    "(", ")", "{", "}", "[", "]", ",", ".", ":", ";", "=", "<", ">",
    "+", "-", "*", "/", "%", "!", "?", "|", "&", "_",
]


@dataclass
class Token:
    kind: str        # "ident" | "int" | "float" | "string" | anahtar kelime | operatör | "newline" | "eof"
    value: object    # metin ya da çözümlenmiş literal değeri
    span: Span

    def __repr__(self) -> str:  # hata ayıklama kolaylığı
        return f"Token({self.kind!r}, {self.value!r}, {self.span.line}:{self.span.col})"


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_part(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


class Lexer:
    def __init__(self, source: str, filename: str = "<kaynak>") -> None:
        # Kaynak metin doğrudan verildiyse BOM hâlâ başta olabilir; at.
        self.src = source.lstrip("﻿")
        self.filename = filename
        self.i = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    # --- yardımcılar -----------------------------------------------------
    def _span(self, line: int, col: int, length: int = 1) -> Span:
        return Span(self.filename, line, col, length)

    def _peek(self, offset: int = 0) -> str:
        j = self.i + offset
        return self.src[j] if j < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, kind: str, value: object, line: int, col: int) -> None:
        length = max(1, self.col - col) if self.line == line else 1
        self.tokens.append(Token(kind, value, self._span(line, col, length)))

    def _last_kind(self) -> str | None:
        return self.tokens[-1].kind if self.tokens else None

    def _error(self, message: str, line: int | None = None, col: int | None = None):
        return NarError(message, self._span(line or self.line, col or self.col))

    # --- ana döngü -------------------------------------------------------
    def tokenize(self) -> list[Token]:
        while self.i < len(self.src):
            ch = self._peek()

            if ch == "\n":
                line, col = self.line, self.col
                self._advance()
                if self._last_kind() in NEWLINE_TERMINATORS:
                    self._add("newline", "\n", line, col)
                continue

            if ch in " \t\r":
                self._advance()
                continue

            if ch == "/" and self._peek(1) == "/":
                while self.i < len(self.src) and self._peek() != "\n":
                    self._advance()
                continue

            if ch == "/" and self._peek(1) == "*":
                self._block_comment()
                continue

            if ch == '"':
                self._string()
                continue

            if ch.isdigit():
                self._number()
                continue

            if _is_ident_start(ch):
                self._ident()
                continue

            if self._operator():
                continue

            raise self._error(f"beklenmeyen karakter: {ch!r}")

        # Dosya sonunda kapatılmamış deyimi bitir.
        if self._last_kind() in NEWLINE_TERMINATORS:
            self._add("newline", "\n", self.line, self.col)
        self._add("eof", None, self.line, self.col)
        return self.tokens

    # --- alt çözümleyiciler ----------------------------------------------
    def _block_comment(self) -> None:
        line, col = self.line, self.col
        self._advance()  # /
        self._advance()  # *
        depth = 1
        while depth > 0:
            if self.i >= len(self.src):
                raise self._error("kapatılmamış blok yorumu", line, col)
            if self._peek() == "/" and self._peek(1) == "*":
                self._advance(); self._advance()
                depth += 1
            elif self._peek() == "*" and self._peek(1) == "/":
                self._advance(); self._advance()
                depth -= 1
            else:
                self._advance()

    def _number(self) -> None:
        line, col = self.line, self.col
        start = self.i

        # Dikkat: boş dizge her dizgenin alt dizesidir, bu yüzden `_peek(1)`
        # boş değilken kontrol edilmeli — yoksa `0` ile biten kaynakta taşar.
        if self._peek() == "0" and self._peek(1) != "" and self._peek(1) in "xXbBoO":
            self._advance()
            base_char = self._advance().lower()
            base = {"x": 16, "b": 2, "o": 8}[base_char]
            digits = ""
            while self.i < len(self.src) and (self._peek().isalnum() or self._peek() == "_"):
                c = self._advance()
                if c != "_":
                    digits += c
            if not digits:
                raise self._error("sayı tabanı belirtildi ama rakam yok", line, col)
            try:
                value = int(digits, base)
            except ValueError:
                raise self._error(f"geçersiz sayı: {self.src[start:self.i]!r}", line, col) from None
            self._add("int", value, line, col)
            return

        is_float = False
        while self.i < len(self.src):
            c = self._peek()
            if c.isdigit() or c == "_":
                self._advance()
            elif c == "." and self._peek(1).isdigit() and not is_float:
                is_float = True
                self._advance()
            elif c in "eE" and (self._peek(1).isdigit() or (self._peek(1) in "+-" and self._peek(2).isdigit())):
                is_float = True
                self._advance()
                if self._peek() in "+-":
                    self._advance()
            else:
                break

        text = self.src[start:self.i].replace("_", "")
        if is_float:
            self._add("float", float(text), line, col)
        else:
            self._add("int", int(text), line, col)

    def _string(self) -> None:
        """Metin literali.

        Değer, parça listesi olarak saklanır: düz metinler ``str``,
        ``${...}`` içe gömmeleri ``("expr", kaynak_metin, satır, sütun)``
        demeti olarak. Parser gömülü ifadeleri yeniden çözümler.
        """
        line, col = self.line, self.col

        # `"""` çok satırlı metni açar: satır sonları içeriğin parçasıdır.
        cok_satirli = self._peek(1) == '"' and self._peek(2) == '"'
        if cok_satirli:
            self._advance()
            self._advance()
            self._advance()
            # Açılıştan hemen sonraki satır sonu okunurluk içindir, metne
            # girmez: `"""\nilk satır` baştaki boş satırı taşımamalı.
            if self._peek() == "\r":
                self._advance()
            if self._peek() == "\n":
                self._advance()
        else:
            self._advance()  # açılış tırnağı

        parts: list[object] = []
        buf = ""

        while True:
            if self.i >= len(self.src):
                raise self._error("kapatılmamış metin literali", line, col)
            ch = self._peek()

            if ch == '"':
                if not cok_satirli:
                    self._advance()
                    break
                if self._peek(1) == '"' and self._peek(2) == '"':
                    self._advance()
                    self._advance()
                    self._advance()
                    break
                # Çok satırlı metinde tek tırnak sıradan bir karakterdir.
                buf += self._advance()
                continue

            if ch == "\n":
                if not cok_satirli:
                    raise self._error(
                        "metin literali satır sonunda kapatılmamış", line, col)
                buf += self._advance()
                continue

            if ch == "\\":
                self._advance()
                esc = self._advance()
                mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                           '"': '"', "0": "\0", "$": "$", "'": "'"}
                if esc in mapping:
                    buf += mapping[esc]
                elif esc == "u":
                    if self._peek() != "{":
                        raise self._error("\\u kaçışı '{' bekliyor")
                    self._advance()
                    hex_digits = ""
                    while self._peek() != "}":
                        if self.i >= len(self.src):
                            raise self._error("kapatılmamış \\u{...} kaçışı")
                        hex_digits += self._advance()
                    self._advance()  # }
                    buf += chr(int(hex_digits, 16))
                else:
                    raise self._error(f"bilinmeyen kaçış dizisi: \\{esc}")
                continue

            if ch == "$" and self._peek(1) == "{":
                if buf:
                    parts.append(buf)
                    buf = ""
                self._advance()  # $
                self._advance()  # {
                expr_line, expr_col = self.line, self.col
                depth = 1
                expr_src = ""
                while depth > 0:
                    if self.i >= len(self.src):
                        raise self._error("kapatılmamış ${...} gömmesi", line, col)
                    c = self._peek()
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            self._advance()
                            break
                    elif c == '"':
                        # gömme içindeki iç metni olduğu gibi kopyala
                        expr_src += self._advance()
                        while self.i < len(self.src) and self._peek() != '"':
                            if self._peek() == "\\":
                                expr_src += self._advance()
                            expr_src += self._advance()
                        if self.i >= len(self.src):
                            raise self._error("gömme içinde kapatılmamış metin", line, col)
                        expr_src += self._advance()
                        continue
                    expr_src += self._advance()
                if not expr_src.strip():
                    raise self._error("boş ${} gömmesi", expr_line, expr_col)
                parts.append(("expr", expr_src, expr_line, expr_col))
                continue

            buf += self._advance()

        if buf or not parts:
            parts.append(buf)
        self._add("string", parts, line, col)

    def _ident(self) -> None:
        line, col = self.line, self.col
        start = self.i
        while self.i < len(self.src) and _is_ident_part(self._peek()):
            self._advance()
        text = self.src[start:self.i]
        if text in KEYWORDS:
            self._add(text, text, line, col)
        else:
            self._add("ident", text, line, col)

    def _operator(self) -> bool:
        line, col = self.line, self.col
        for op in OPERATORS:
            if self.src.startswith(op, self.i):
                # `_` tek başına joker desendir; `_ad` tanımlayıcıdır.
                if op == "_" and _is_ident_part(self._peek(1)):
                    return False
                for _ in op:
                    self._advance()
                self._add(op, op, line, col)
                return True
        return False


def tokenize(source: str, filename: str = "<kaynak>") -> list[Token]:
    return Lexer(source, filename).tokenize()
