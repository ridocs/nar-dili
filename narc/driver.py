"""Derleme sürücüsü: kaynak dosyayı okur, içe aktarmaları birleştirir,
denetler ve hedef kodu üretir."""

from __future__ import annotations

from pathlib import Path

from . import nar_ast as A
from .backends import js as js_backend
from .checker import Checker
from .diagnostics import NarError, Span
from .parser import parse


class Compilation:
    """Bir derleme birimi: birleştirilmiş modül, denetleyici ve kaynak metinler."""

    def __init__(self, module: A.Module, checker: Checker, sources: dict[str, str],
                 kutuphane: bool = False) -> None:
        self.module = module
        self.checker = checker
        self.sources = sources
        self.kutuphane = kutuphane

    def to_js(self) -> str:
        return js_backend.generate(self.module, self.checker, self.kutuphane)


def iceri_ipucu(hedef: Path) -> str | None:
    """Bulunamayan içe aktarma için aynı adlı gerçek bir dosya önerir.

    En sık hata klasör adını Türkçe yazmak: `araçlar/` ile `araclar/`
    aynı görünüyor. Aynı ada sahip bir dosya yakınlarda duruyorsa onu
    göstermek, hatayı çıkmaz sokak olmaktan çıkarır.

    Yalnız iki kademe bakılır — aynı klasör ve kardeş klasörler; bütün
    ağacı taramak hata yolunda gereksiz iş olurdu.
    """
    ad = hedef.name
    taban = hedef.parent
    while not taban.is_dir() and taban != taban.parent:
        taban = taban.parent
    if not taban.is_dir():
        return None

    adaylar: list[str] = []
    for kalip in (ad, f"*/{ad}"):
        for aday in sorted(taban.glob(kalip)):
            if aday.is_file():
                adaylar.append(aday.relative_to(taban).as_posix())
    if not adaylar:
        return None
    return 'belki: "' + min(adaylar, key=len) + '"'


def load_module(path: Path, sources: dict[str, str], seen: list[Path],
                stack: set[Path] | None = None,
                kaynak: str | None = None) -> list[A.Node]:
    """Dosyayı ve içe aktardıklarını çözümleyip üst düzey öğeleri düz listeye açar.

    `kaynak` verilirse dosya okunmaz, verilen metin kullanılır: düzenleyicide
    açık olan ve henüz kaydedilmemiş tampon böyle derlenir. İçe aktardıkları
    yine diskten okunur, `path`in klasörüne göre çözülür.
    """
    stack = stack if stack is not None else set()
    resolved = path.resolve()

    if resolved in stack:
        chain = " -> ".join(p.name for p in stack) + f" -> {resolved.name}"
        raise NarError(f"döngüsel içe aktarma: {chain}", Span(str(path), 1, 1))
    if resolved in seen:
        return []  # zaten yüklendi

    if kaynak is None and not resolved.exists():
        raise NarError(f"dosya bulunamadı: {path}", Span(str(path), 1, 1),
                       hint=iceri_ipucu(resolved))

    # `utf-8-sig`: Windows araçları (Not Defteri, PowerShell'in `-Encoding utf8`)
    # dosyanın başına BOM koyar. BOM varsa atılır, yoksa davranış değişmez.
    source = kaynak if kaynak is not None else resolved.read_text(encoding="utf-8-sig")
    name = resolved.name
    sources[name] = source
    seen.append(resolved)

    module = parse(source, name)
    stack.add(resolved)

    items: list[A.Node] = []
    for item in module.items:
        if isinstance(item, A.Import):
            target = (resolved.parent / item.path).resolve()
            items.extend(load_module(target, sources, seen, stack))
        else:
            items.append(item)

    stack.discard(resolved)
    return items


def compile_file(path: Path, sources: dict[str, str] | None = None,
                 kutuphane: bool = False) -> Compilation:
    """Dosyayı derler.

    `sources` verilirse okunan kaynak metinler oraya yazılır. Hata fırlatılsa
    bile dolu kalır; çağıran böylece hatanın geçtiği satırı gösterebilir.
    """
    return compile_source(None, path, sources, kutuphane)


def compile_source(kaynak: str | None, path: Path,
                   sources: dict[str, str] | None = None,
                   kutuphane: bool = False) -> Compilation:
    """Verilen metni `path` konumundaki dosyaymış gibi derler.

    `kaynak` None ise dosya diskten okunur (`compile_file` böyle çalışır).
    Metin verilirse disk yerine o kullanılır; içe aktardıkları `path`in
    klasörüne göre çözülür. Düzenleyici kaydedilmemiş tamponu böyle
    denetletir — içe aktarmalar komut satırındakiyle aynı yoldan geçsin,
    iki yerde iki ayrı davranış olmasın.
    """
    sources = sources if sources is not None else {}
    seen: list[Path] = []
    items = load_module(path, sources, seen, kaynak=kaynak)

    root = A.Module(Span(path.name, 1, 1), path.name, items)
    checker = Checker(root, sources.get(path.name, ""), kutuphane=kutuphane)
    checker.check()
    return Compilation(root, checker, sources, kutuphane)


HTML_TEMPLATE = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; padding: 24px; font: 14px/1.6 ui-monospace, SFMono-Regular,
         Menlo, Consolas, monospace; }}
  h1 {{ font: 600 18px/1.4 system-ui, sans-serif; margin: 0 0 16px; }}
  #cikti {{ white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<h1>{title}</h1>
<!-- Nar programı `bul("#uygulama")` ile buraya çizebilir. -->
<div id="uygulama"></div>
<div id="cikti"></div>
<script>
// Nar programının `print` çıktısı sayfaya yazılır.
(function () {{
  const hedef = document.getElementById("cikti");
  const asil = console.log.bind(console);
  console.log = function (...args) {{
    asil(...args);
    hedef.textContent += args.join(" ") + "\\n";
  }};
}})();
</script>
<script>
{code}
</script>
</body>
</html>
"""


def to_html(compilation: Compilation, title: str) -> str:
    return HTML_TEMPLATE.format(title=title, code=compilation.to_js())
