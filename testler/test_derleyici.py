"""Ön uç testleri: lexer, parser ve tip denetleyici.

Çalıştırma:  python -m unittest discover -s testler
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from narc.checker import Checker  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.lexer import tokenize  # noqa: E402
from narc.parser import parse  # noqa: E402


def check(src: str) -> Checker:
    module = parse(src, "test.nar")
    checker = Checker(module, src)
    checker.check()
    return checker


def wrap(body: str) -> str:
    return "fn main() {\n" + body + "\n}\n"


class LexerTesti(unittest.TestCase):
    def kinds(self, src: str) -> list[str]:
        return [t.kind for t in tokenize(src, "t.nar")]

    def test_sayilar(self):
        toks = tokenize("42 3.14 0xFF 0b1010 1_000 1.5e-3", "t.nar")
        values = [t.value for t in toks if t.kind in ("int", "float")]
        self.assertEqual(values, [42, 3.14, 255, 10, 1000, 0.0015])

    def test_satir_sonu_yalnizca_gerektiginde(self):
        # `+` sonrası satır sonu yutulur, ifade bölünebilir
        kinds = self.kinds("let x = 1 +\n2\n")
        self.assertNotIn("newline", kinds[:kinds.index("2") if "2" in kinds else 5])
        self.assertEqual(kinds.count("newline"), 1)

    def test_metin_gommesi(self):
        tok = tokenize('"a=${1 + 2} son"', "t.nar")[0]
        self.assertEqual(tok.kind, "string")
        self.assertEqual(tok.value[0], "a=")
        self.assertEqual(tok.value[1][0], "expr")
        self.assertEqual(tok.value[2], " son")

    def test_ic_ice_blok_yorumu(self):
        toks = self.kinds("/* dış /* iç */ hâlâ yorum */ 1")
        self.assertEqual(toks, ["int", "newline", "eof"])

    def test_kacis_dizileri(self):
        tok = tokenize(r'"satır\nsekme\tters\\tırnak\""', "t.nar")[0]
        self.assertEqual(tok.value[0], 'satır\nsekme\tters\\tırnak"')

    def test_sifirla_biten_kaynak(self):
        # Regresyon: `0` ile biten kaynak, taban öneki sanılıp taşmamalı
        toks = tokenize("let x = 0", "t.nar")
        self.assertEqual(toks[-3].value, 0)
        self.assertEqual(tokenize("0", "t.nar")[0].value, 0)

    def test_kapatilmamis_metin(self):
        with self.assertRaises(NarError):
            tokenize('"açık', "t.nar")

    def test_turkce_tanimlayici(self):
        toks = tokenize("let ağırlık = 1", "t.nar")
        self.assertEqual(toks[1].value, "ağırlık")


class ParserTesti(unittest.TestCase):
    def test_oncelik(self):
        module = parse(wrap("let x = 1 + 2 * 3"), "t.nar")
        expr = module.items[0].body.stmts[0].value
        self.assertEqual(expr.op, "+")
        self.assertEqual(expr.right.op, "*")

    def test_kosulda_struct_literali_yok(self):
        # `if x { }` içinde `{` blok olarak okunmalı
        module = parse("struct S { a: Int }\n" + wrap("let x = 1\nif x > 0 { print(\"e\") }"), "t.nar")
        self.assertEqual(len(module.items), 2)

    def test_struct_literali_taninir(self):
        module = parse("struct S { a: Int }\n" + wrap("let s = S { a: 1 }"), "t.nar")
        value = module.items[1].body.stmts[0].value
        self.assertEqual(type(value).__name__, "StructLit")

    def test_ustduzeyde_deyim_hatasi(self):
        with self.assertRaises(NarError):
            parse("print(\"merhaba\")\n", "t.nar")

    def test_ayni_satirda_iki_deyim_hatasi(self):
        with self.assertRaises(NarError):
            parse(wrap("let a = 1 let b = 2"), "t.nar")

    def test_lambda_kisa_ve_bloklu(self):
        module = parse(wrap("let f = |x| x + 1\nlet g = |x| { return x + 1 }"), "t.nar")
        stmts = module.items[0].body.stmts
        self.assertEqual(type(stmts[0].value).__name__, "Lambda")
        self.assertEqual(type(stmts[1].value).__name__, "Lambda")


class DenetleyiciTesti(unittest.TestCase):
    def gecerli(self, src: str):
        try:
            check(src)
        except NarError as err:
            self.fail(f"beklenmeyen hata: {err.render(src)}")

    def hatali(self, src: str, parca: str):
        with self.assertRaises(NarError) as ctx:
            check(src)
        self.assertIn(parca, ctx.exception.message,
                      f"beklenen ipucu bulunamadı.\nAlınan: {ctx.exception.message}")

    # --- geçerli programlar ---
    def test_temel_program(self):
        self.gecerli(wrap('let x = 1\nprint(str(x))'))

    def test_akis_daraltma(self):
        self.gecerli(wrap('let a: Int? = 3\nif a != none { print(str(a + 1)) }'))

    def test_daraltma_ve_operatoru(self):
        self.gecerli(wrap('let a: Int? = 3\nif a != none && a > 1 { print("e") }'))

    def test_map_tipi_lambdadan_cikarilir(self):
        self.gecerli(wrap('let m = [1, 2].map(|x| str(x))\nprint(m.join(","))'))

    def test_reduce(self):
        self.gecerli(wrap('print(str([1,2,3].reduce(|a, b| a + b, 0)))'))

    def test_bos_liste_tip_yaziliysa(self):
        self.gecerli(wrap('let l: [Int] = []\nprint(str(l.len()))'))

    def test_int_literali_float_baglaminda(self):
        self.gecerli(wrap('let x: Float = 3\nprint(str(x))'))

    def test_karsilikli_baswuru(self):
        self.gecerli("""
struct A { b: B }
struct B { n: Int }
fn main() { let a = A { b: B { n: 1 } }
 print(str(a.b.n)) }
""")

    def test_enum_metodu(self):
        self.gecerli("""
enum E { A(Int)  B
  fn deger() -> Int {
    match self {
      E.A(n) -> return n
      E.B -> return 0
    }
  }
}
fn main() { print(str(E.A(5).deger())) }
""")

    # --- hatalı programlar ---
    def test_tanimsiz_isim(self):
        self.hatali(wrap("print(str(yok))"), "tanımsız isim")

    def test_tip_uyusmazligi(self):
        self.hatali(wrap('let x: Int = "a"'), "bekleniyordu")

    def test_degismeze_atama(self):
        self.hatali(wrap("let x = 1\nx = 2"), "değişmez")

    def test_int_float_toplama(self):
        self.hatali(wrap("let x = 1 + 2.0"), "tanımlı değil")

    def test_opsiyonel_dogrudan_erisim(self):
        self.hatali(wrap('let s: String? = none\nprint(s.upper())'), "opsiyonel")

    def test_eksik_return(self):
        self.hatali("fn f() -> Int { }\nfn main() { print(str(f())) }", "değer döndürmüyor")

    def test_match_tam_degil(self):
        self.hatali(
            "enum E { A  B }\nfn main() { match E.A { E.A -> print(\"a\") } }",
            "tam değil",
        )

    def test_bilinmeyen_alan(self):
        self.hatali(
            "struct S { a: Int }\nfn main() { let s = S { a: 1 }\n print(str(s.b)) }",
            "yok",
        )

    def test_eksik_alan(self):
        self.hatali(
            "struct S { a: Int  b: Int }\nfn main() { let s = S { a: 1 }\n print(str(s.a)) }",
            "eksik alanlar",
        )

    def test_yanlis_argüman_sayisi(self):
        self.hatali(
            "fn f(a: Int) -> Int { return a }\nfn main() { print(str(f(1, 2))) }",
            "argüman bekleniyordu",
        )

    def test_main_yok(self):
        self.hatali("fn f() { }", "'main' fonksiyonu yok")

    def test_bos_liste_tipsiz(self):
        self.hatali(wrap("let l = []"), "çıkarılamıyor")

    def test_dongusuz_break(self):
        self.hatali(wrap("break"), "döngü içinde")

    def test_bilinmeyen_tip(self):
        self.hatali("fn main() { let x: Yok = 1\n print(str(x)) }", "bilinmeyen tip")

    def test_yerlesik_yeniden_tanim(self):
        self.hatali("fn print(x: Int) { }\nfn main() { }", "yerleşik")

    def test_map_tek_degiskenle(self):
        self.hatali(
            wrap('let m = {"a": 1}\nfor k in m { print(k) }'),
            "iki değişken",
        )

    def test_sirali_olmayan_karsilastirma(self):
        self.hatali(
            "struct S { a: Int }\nfn main() { let x = S{a:1} < S{a:2}\n print(str(x)) }",
            "sıralanabilir değil",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
