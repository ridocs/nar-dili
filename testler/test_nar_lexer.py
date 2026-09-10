"""Nar ile yazılmış lexer, Python lexer'ıyla aynı sonucu vermeli.

`derleyici/lexer.nar`, derleyiciyi kendi diline taşıma yolundaki ilk
adımdır. Doğruluğunun ölçüsü şu: aynı kaynak için Python'daki
`narc/lexer.py` ile **birebir aynı** token dizisini üretmek.

Karşılaştırma gerçek kod üzerinde yapılır: projedeki bütün `.nar`
dosyaları iki lexer'dan da geçirilir.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.driver import compile_file  # noqa: E402
from narc.lexer import tokenize as python_tokenize  # noqa: E402

NODE = shutil.which("node")
NAR_LEXER = KOK / "derleyici" / "lexer.nar"


def nar_lexer_js(tmp: Path) -> Path:
    """Nar lexer'ını kütüphane olarak derler."""
    kod = compile_file(NAR_LEXER, kutuphane=True).to_js()
    betik = tmp / "nar-lexer.js"
    betik.write_text(kod, encoding="utf-8")
    return betik


def nar_ile_tokenlestir(betik: Path, kaynaklar: list[str]) -> list:
    """Verilen kaynakları Nar lexer'ıyla tokenleştirir (tek Node çağrısı)."""
    surucu = (
        f"require({str(betik).replace(chr(92), '/')!r});\n"
        "let veri = '';\n"
        "process.stdin.setEncoding('utf8');\n"
        "process.stdin.on('data', (p) => { veri += p; });\n"
        "process.stdin.on('end', () => {\n"
        "  const girdi = JSON.parse(veri);\n"
        "  const cikti = girdi.map((k) => {\n"
        "    const s = Nar.tokenlestir(k);\n"
        "    if (s.$tag === 'Hata') {\n"
        "      const h = s.$values[0];\n"
        "      return {hata: h.mesaj, satir: h.satir, sutun: h.sutun};\n"
        "    }\n"
        "    return {tokenlar: s.$values[0].map(\n"
        "      (t) => [t.tur, t.satir, t.sutun])};\n"
        "  });\n"
        "  process.stdout.write(JSON.stringify(cikti));\n"
        "});\n"
    )
    sonuc = subprocess.run(
        [NODE, "-e", surucu], input=json.dumps(kaynaklar),
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    if sonuc.returncode != 0:
        raise AssertionError("Nar lexer çalışmadı:\n" + sonuc.stderr.strip())
    return json.loads(sonuc.stdout)


def python_ile_tokenlestir(kaynak: str) -> list:
    return [[t.kind, t.span.line, t.span.col] for t in python_tokenize(kaynak, "t.nar")]


def proje_dosyalari() -> list[Path]:
    dosyalar: list[Path] = []
    for klasor in ("araclar", "ornekler", "derleyici", "testler/nar"):
        dosyalar.extend(sorted((KOK / klasor).glob("*.nar")))
    dosyalar.append(KOK / "deneme.nar")
    return [d for d in dosyalar if d.exists()]


@unittest.skipIf(NODE is None, "node bulunamadı")
class NarLexerTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.betik = nar_lexer_js(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def karsilastir(self, kaynaklar: list[str], adlar: list[str]):
        nar_sonuclari = nar_ile_tokenlestir(self.betik, kaynaklar)
        for ad, kaynak, nar in zip(adlar, kaynaklar, nar_sonuclari):
            with self.subTest(kaynak=ad):
                self.assertNotIn("hata", nar, f"{ad}: Nar lexer hata verdi: {nar}")
                beklenen = python_ile_tokenlestir(kaynak)
                alinan = [list(t) for t in nar["tokenlar"]]
                self.assertEqual(
                    alinan, beklenen,
                    f"{ad}: token dizileri ayrışıyor\n"
                    f"ilk fark: {self._ilk_fark(alinan, beklenen)}",
                )

    @staticmethod
    def _ilk_fark(a: list, b: list) -> str:
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return f"{i}. token: Nar={x} Python={y}"
        return f"uzunluk farkı: Nar={len(a)} Python={len(b)}"

    def test_kucuk_ornekler(self):
        ornekler = [
            'fn main() { print("merhaba") }',
            "let x = 42\nlet y = 3.14\nlet z = 0xFF\nlet w = 1_000\nlet e = 1.5e-3",
            "// yorum\n/* blok /* iç içe */ yorum */\nlet a = 1",
            'let s = "kaçış \\n \\t \\" son"',
            'let g = "gömme ${a + b} son"',
            "a ?? b\nc?.d\ne!\nf..g\nh..=i",
            "x += 1\ny -= 2\nz *= 3\nw /= 4\nv %= 5",
            "let ağırlık = 70\nlet İsim = \"x\"",
            "match x { _ -> 1 }\nlet _sayi = 2",
            "if a && b || !c { }",
            "struct S<T> { a: T }\ninterface I { fn m() -> Int }",
            "let bos = []\nlet m = {}\n",
            "0",
            "",
            "\n\n\n",
        ]
        self.karsilastir(ornekler, [f"örnek {i}" for i in range(len(ornekler))])

    def test_proje_dosyalari(self):
        dosyalar = proje_dosyalari()
        self.assertGreater(len(dosyalar), 5, "yeterince dosya bulunamadı")
        kaynaklar = [d.read_text(encoding="utf-8-sig") for d in dosyalar]
        self.karsilastir(kaynaklar, [d.name for d in dosyalar])

    def test_hatalari_da_yakaliyor(self):
        hatalilar = [
            '"kapatılmamış',
            "/* kapatılmamış yorum",
            "let x = 0x",
        ]
        sonuclar = nar_ile_tokenlestir(self.betik, hatalilar)
        for kaynak, sonuc in zip(hatalilar, sonuclar):
            with self.subTest(kaynak=kaynak):
                self.assertIn("hata", sonuc, f"{kaynak!r} için hata bekleniyordu")


if __name__ == "__main__":
    unittest.main(verbosity=2)
