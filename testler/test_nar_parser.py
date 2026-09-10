"""Nar ile yazılan çözümleyici, Python çözümleyiciyle aynı ağacı kurmalı.

`derleyici/parser.nar`, derleyiciyi kendi diline taşıma yolundaki ikinci
adımdır (ilki lexer'dı). Doğruluğunun ölçüsü şu: aynı kaynak için birebir
aynı **S-ifadesini** üretmek.

S-ifadesi ağacın parantezli metin hâlidir; iki tarafın ortak dili odur
(`derleyici/ast.nar` ve `narc/sifade.py`). Konum bilgisi yazılmaz — iki
çözümleyicinin satır/sütun hesabı birebir aynı olmak zorunda değil, ağacın
yapısı aynı olmak zorunda.

Karşılaştırma gerçek kod üzerinde yapılır: projedeki bütün `.nar` dosyaları
iki çözümleyiciden de geçirilir.
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

from narc import sifade  # noqa: E402
from narc.driver import compile_file  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")
NAR_PARSER = KOK / "derleyici" / "parser.nar"


def nar_parser_js(tmp: Path) -> Path:
    kod = compile_file(NAR_PARSER, kutuphane=True).to_js()
    betik = tmp / "nar-parser.js"
    betik.write_text(kod, encoding="utf-8")
    return betik


def nar_ile_cozumle(betik: Path, kaynaklar: list[str]) -> list[str]:
    """Kaynakları Nar çözümleyicisinden geçirir (tek Node çağrısı)."""
    surucu = (
        f"require({str(betik).replace(chr(92), '/')!r});\n"
        "let veri = '';\n"
        "process.stdin.setEncoding('utf8');\n"
        "process.stdin.on('data', (p) => { veri += p; });\n"
        "process.stdin.on('end', () => {\n"
        "  const girdi = JSON.parse(veri);\n"
        "  process.stdout.write(JSON.stringify(girdi.map(\n"
        "    (k) => Nar.sifadeUret(k))));\n"
        "});\n"
    )
    sonuc = subprocess.run(
        [NODE, "-e", surucu], input=json.dumps(kaynaklar),
        capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    if sonuc.returncode != 0:
        raise AssertionError("Nar çözümleyici çalışmadı:\n" + sonuc.stderr.strip())
    return json.loads(sonuc.stdout)


def proje_dosyalari() -> list[Path]:
    dosyalar: list[Path] = []
    for klasor in ("araclar", "ornekler", "derleyici", "testler/nar"):
        dosyalar.extend(sorted((KOK / klasor).glob("*.nar")))
    dosyalar.append(KOK / "deneme.nar")
    return [d for d in dosyalar if d.exists()]


@unittest.skipIf(NODE is None, "node bulunamadı")
class NarParserTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.betik = nar_parser_js(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def karsilastir(self, kaynaklar: list[str], adlar: list[str]):
        nar_sonuclari = nar_ile_cozumle(self.betik, kaynaklar)
        for ad, kaynak, alinan in zip(adlar, kaynaklar, nar_sonuclari):
            with self.subTest(kaynak=ad):
                self.assertFalse(
                    alinan.startswith("HATA"),
                    f"{ad}: Nar çözümleyici hata verdi: {alinan[:200]}",
                )
                beklenen = sifade.yaz(parse(kaynak, "t.nar"))
                self.assertEqual(
                    alinan, beklenen,
                    f"{ad}: ağaçlar ayrışıyor\n{self._ilk_fark(alinan, beklenen)}",
                )

    @staticmethod
    def _ilk_fark(a: str, b: str) -> str:
        n = min(len(a), len(b))
        i = 0
        while i < n and a[i] == b[i]:
            i += 1
        bas = max(0, i - 60)
        return (f"  konum {i}\n"
                f"  Nar    : ...{a[bas:i + 80]}\n"
                f"  Python : ...{b[bas:i + 80]}")

    def test_kucuk_ornekler(self):
        ornekler = [
            'fn main() { print("merhaba") }',
            "let x = 42\nvar y = 3.14\nlet z = 0xFF\nlet b = 0b1010\nlet o = 0o17",
            "let m = 1_000_000\nlet e = 1.5e3\nlet n = -7",
            'let s = "a ${1 + 2} b"',
            'let ic = "dış ${"iç ${1}"} son"',
            'let k = "kaçış \\n \\t \\\\ \\" \\u{1F34E} son"',
            'let bos = ""',
            "fn f<T: Yaz>(x: T) -> T = x",
            "fn g<T, U>(a: T, b: U) -> Bool = true",
            "struct S<T> { var a: T\n  let b: Int\n  fn m() -> T = self.a }",
            "struct N: Yaz, Olc { a: Int }",
            "enum E { Bir  Iki(Int, String)  Uc }",
            "enum G<T>: Yaz { Dolu(T)  Bos\n  fn yaz() -> String = \"x\" }",
            "interface I { fn m() -> Int\n  fn n(a: String) }",
            "type Sayi = Int\ntype Liste = [String]\ntype Esleme = {String: Int}",
            "type Islev = (Int, String) -> Bool\ntype Ops = Int?",
            "fn h() { for (k, v) in m { print(k, v) } }",
            "fn i() { for x in 0..10 { }\n  for y in 0..=10 { } }",
            "fn j() { match x { E.Bir -> 1\n  E.Iki(a, _) -> a\n  _ -> 2 } }",
            "fn k() { match x { .Bir -> 1\n  Iki(a) -> a\n  3 -> 4\n  none -> 5 } }",
            "fn l() { let a = if b { 1 } else if c { 2 } else { 3 } }",
            "fn m2() { if a { } else if b { } else { } }",
            "fn n2() { let p = [1, 2, 3].map(|x| x * 2).filter(|y| y > 2) }",
            "fn o() { let q = |a: Int, b: Int| -> Int { return a + b } }",
            # `fn` ifadesi ad ister; ad kullanılmaz ama sözdizimi böyle.
            "fn p() { let r = fn ic(x: Int) -> Int { return x } }",
            "fn q2() { let t = Nokta { x: 1, y: 2 } }",
            "fn r() { let u = Kutu<Int> { deger: 5 } }",
            "fn s2() { let v = Bos { } }",
            "fn t2() { a?.b!.c[0](1).d }",
            "fn u2() { x += 1\n  y.z = 2\n  w[0] -= 3 }",
            "fn v2() { while a && b || !c { break }\n  while true { continue } }",
            "fn w2() { let e = {}\n  let f = {\"a\": 1, \"b\": 2} }",
            "fn x2() { return }",
            "fn y2() -> Int { return 1 }",
            "fn z2() { print(1,\n  2,\n  3) }",
            "fn aa() { let x = 1 +\n    2 }",
            "import \"a/b.nar\"\nlet g2 = 1",
            "fn bb() { let n = a < b\n  let m = c > d }",
        ]
        self.karsilastir(ornekler, [f"örnek {i}" for i in range(len(ornekler))])

    def test_proje_dosyalari(self):
        dosyalar = proje_dosyalari()
        self.assertGreater(len(dosyalar), 15, "yeterince dosya bulunamadı")
        kaynaklar = [d.read_text(encoding="utf-8-sig") for d in dosyalar]
        self.karsilastir(kaynaklar, [d.name for d in dosyalar])

    def test_hatalari_da_yakaliyor(self):
        """Python'un reddettiği kaynağı Nar da reddetmeli.

        Hata *mesajlarının* birebir aynı olması beklenmez; reddedilmesi
        beklenir. Sessizce kabul eden bir çözümleyici sessizce yanlış kod
        üretir.
        """
        from narc.diagnostics import NarError

        hatalilar = [
            "fn",
            "fn f(",
            "let",
            "let = 5",
            "let x",
            "struct { }",
            "enum E {",
            "fn f() { let a = if b { 1 } }",
            "fn f() { match x { } }",
            "interface I { }",
            "interface I { fn m() -> Int { return 1 } }",
            "fn f() { 1 = 2 }",
            "fn f() { let a = ( }",
            "fn f() { let a = [1, }",
            "type",
            "import 5",
            "5 + 5",
        ]
        nar_sonuclari = nar_ile_cozumle(self.betik, hatalilar)
        for kaynak, alinan in zip(hatalilar, nar_sonuclari):
            with self.subTest(kaynak=kaynak):
                with self.assertRaises(NarError, msg="Python bunu kabul etti"):
                    parse(kaynak, "t.nar")
                self.assertTrue(
                    alinan.startswith("HATA"),
                    f"Nar çözümleyici hatayı kaçırdı: {kaynak!r} → {alinan[:120]}",
                )


if __name__ == "__main__":
    unittest.main()
