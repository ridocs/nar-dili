"""Nar komut satırı arayüzü.

  nar run    dosya.nar          derler ve Node ile çalıştırır
  nar build  dosya.nar          JavaScript üretir
  nar build  dosya.nar --target web    tek dosyalık HTML üretir
  nar check  dosya.nar          yalnızca denetler
  nar emit   dosya.nar          üretilen kodu ekrana yazar
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .diagnostics import NarError, NarErrors
from .driver import compile_file, to_html


def fail(err: NarError, sources: dict[str, str]) -> int:
    if isinstance(err, NarErrors):
        print(err.render_all(sources), file=sys.stderr)
        return 1
    source = None
    if err.span is not None:
        source = sources.get(err.span.filename)
    print(err.render(source), file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nar",
        description="Nar derleyicisi — çok platformlu uygulamalar için tek dil.",
    )
    parser.add_argument("--version", action="version", version=f"Nar {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("run", "derler ve çalıştırır"),
        ("build", "hedef kodu dosyaya yazar"),
        ("check", "yalnızca tip denetimi yapar"),
        ("emit", "üretilen kodu ekrana yazar"),
    ):
        sub = subs.add_parser(name, help=help_text)
        sub.add_argument("file", type=Path, help="kaynak .nar dosyası")
        if name in ("build", "emit"):
            sub.add_argument("--target", default="js", choices=["js", "web"],
                             help="çıktı hedefi (varsayılan: js)")
        if name == "build":
            sub.add_argument("-o", "--out", type=Path, default=None,
                             help="çıktı dosyası")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources: dict[str, str] = {}

    try:
        compilation = compile_file(args.file, sources)
    except NarError as err:
        return fail(err, sources)
    except FileNotFoundError:
        print(f"hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1

    if args.command == "check":
        print(f"tamam: {args.file} — hata yok")
        return 0

    target = getattr(args, "target", "js")
    title = args.file.stem
    output = to_html(compilation, title) if target == "web" else compilation.to_js()

    if args.command == "emit":
        sys.stdout.write(output)
        return 0

    if args.command == "build":
        suffix = ".html" if target == "web" else ".js"
        out_path = args.out or args.file.with_suffix(suffix)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"yazıldı: {out_path}")
        return 0

    # run
    node = shutil.which("node")
    if node is None:
        print("hata: 'node' bulunamadı. Node.js kurulu olmalı.", file=sys.stderr)
        return 1

    build_dir = args.file.parent / ".narbuild"
    build_dir.mkdir(exist_ok=True)
    script = build_dir / (args.file.stem + ".js")
    script.write_text(compilation.to_js(), encoding="utf-8")

    result = subprocess.run([node, str(script)])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
