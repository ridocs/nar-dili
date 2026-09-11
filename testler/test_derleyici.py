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

    def test_bom_atlanir(self):
        # Regresyon: Not Defteri ve PowerShell `-Encoding utf8` dosya başına
        # BOM koyar; derleyici bunu görmezden gelmeli.
        toks = tokenize("﻿let x = 1", "t.nar")
        self.assertEqual(toks[0].kind, "let")

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

    def test_metin_ile_sayi_toplanamaz_degil_artik(self):
        # Sadeleştirme: bir taraf metinse sonuç metindir
        self.gecerli(wrap('let x = "yaş: " + 25\nprint(x)'))

    def test_liste_ile_sayi_toplanmaz(self):
        self.hatali(wrap("let x = [1] + 2"), "tanımlı değil")

    def test_bool_carpilmaz(self):
        self.hatali(wrap("let x = true * 2"), "tanımlı değil")

    def test_if_dallari_ayni_tipte_olmali(self):
        self.hatali(wrap('let x = if true { 1 } else { "a" }'), "uyuşmuyor")

    def test_if_ifadesinde_else_zorunlu(self):
        with self.assertRaises(NarError) as ctx:
            check(wrap("let x = if true { 1 }"))
        self.assertIn("else", ctx.exception.message)

    def test_deger_ureten_match_tam_olmali(self):
        self.hatali(
            "enum E { A  B }\nfn main() { let x = match E.A { E.A -> 1 }\n print(x) }",
            "tam değil",
        )

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

    def test_tum_hatalar_birden_bildirilir(self):
        src = wrap('let a: Int = "m"\nlet b = yok\nprint(d)')
        with self.assertRaises(NarError) as ctx:
            check(src)
        hepsi = getattr(ctx.exception, "errors", [])
        self.assertEqual(len(hepsi), 3, f"3 hata bekleniyordu: {[h.message for h in hepsi]}")
        # Konuma göre sıralı olmalı
        satirlar = [h.span.line for h in hepsi]
        self.assertEqual(satirlar, sorted(satirlar))

    def test_ayni_hata_tekrarlanmaz(self):
        src = wrap("let a = yok")
        with self.assertRaises(NarError) as ctx:
            check(src)
        self.assertEqual(len(getattr(ctx.exception, "errors", [])), 1)

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

    def uyarilar(self, src: str) -> list:
        from narc.parser import parse as _parse
        modul = _parse(src, "t.nar")
        denetci = Checker(modul, src)
        denetci.check()
        return [u.message for u in denetci.warnings]

    def test_kullanilmayan_degisken_uyarisi(self):
        """Tanımlanıp hiç okunmayan let/var uyarı verir; derleme durmaz."""
        self.assertEqual(
            self.uyarilar(wrap("let toplam = 5")),
            ["'toplam' tanımlanmış ama hiç kullanılmamış"])
        # Okunuyorsa uyarı yok.
        self.assertEqual(self.uyarilar(wrap("let a = 5\nprint(a)")), [])
        # Yalnız yazılan değişken de kullanılmamış sayılır.
        self.assertEqual(
            self.uyarilar(wrap("var s = 0\ns = 1")),
            ["'s' tanımlanmış ama hiç kullanılmamış"])
        # Alt çizgiyle başlayan ad bilerek kullanılmıyor.
        self.assertEqual(self.uyarilar(wrap("let _gecici = 5")), [])
        # Parametreler ve döngü değişkenleri uyarı vermez.
        self.assertEqual(self.uyarilar(
            "fn f(a: Int) {\n  for i in 1..=2 { print(1) }\n}\n"
            + wrap("f(1)")), [])
        # İç kapsamdaki tanım da yakalanır; dış kapsamdaki kullanım sayılır.
        self.assertEqual(
            self.uyarilar(wrap("let a = 1\nif true { let b = a }")),
            ["'b' tanımlanmış ama hiç kullanılmamış"])

    def test_soru_operatoru(self):
        """`?` none ise fonksiyondan none döner."""
        ust = "fn ilk(l: [Int]) -> Int? = l.first()\n"

        def sar_opsiyonel(govde: str) -> str:
            return (ust + "fn dene(l: [Int]) -> Int? {\n" + govde
                    + "\n}\nfn main() { print(dene([1]) ?? 0) }\n")

        self.gecerli(sar_opsiyonel("  let a = ilk(l)?\n  return a"))
        self.gecerli(sar_opsiyonel("  return ilk(l)? + ilk(l)?"))
        # `if` *deyiminin* koşulu bir kez ve koşulsuz değerlendirilir.
        self.gecerli(sar_opsiyonel(
            "  if ilk(l)? > 0 { return 1 }\n  return 0"))
        # Gövdeli lambda kendi deyim listesine yazılır: orada serbest.
        self.gecerli(sar_opsiyonel(
            "  let f = |x: [Int]| -> Int? { let a = ilk(x)?\n    return a }\n"
            "  return f(l)"))

    def test_soru_tip_kurallari(self):
        ust = "fn ilk(l: [Int]) -> Int? = l.first()\n"
        # Opsiyonel olmayan değer açılamaz.
        self.hatali(
            ust + "fn dene() -> Int? {\n  let a = 5?\n  return a\n}\n"
            + "fn main() { print(dene() ?? 0) }\n",
            "opsiyonel bir değer bekler")
        # Fonksiyonun dönüş tipi opsiyonel olmalı.
        self.hatali(
            ust + "fn dene(l: [Int]) -> Int {\n  let a = ilk(l)?\n"
            "  return a\n}\nfn main() { print(dene([1])) }\n",
            "opsiyonel döndüren bir fonksiyonda")
        # Üst düzeyde dönülecek bir fonksiyon yok.
        self.hatali(
            ust + "let G = ilk([1])?\nfn main() { print(G ?? 0) }\n",
            "opsiyonel döndüren bir fonksiyonda")

    def test_soru_kosullu_yerlerde_yasak(self):
        """`?` fonksiyondan erken çıkar; koşullu değerlendirilen yerlerde
        erken çıkışın doğru yere konacağı bir yer yoktur.

        Sessizce yanlış kod üretmektense açık hata verilir.
        """
        ust = "fn ilk(l: [Int]) -> Int? = l.first()\n"

        def dene(govde: str) -> str:
            return (ust + "fn dene(l: [Int]) -> Int? {\n" + govde
                    + "\n  return 1\n}\nfn main() { print(dene([1]) ?? 0) }\n")

        self.hatali(dene("  let x = ilk(l) ?? ilk(l)?"),
                    "'??' işlecinin sağında")
        self.hatali(dene("  let x = true && ilk(l)? > 0"),
                    "'&&' işlecinin sağında")
        self.hatali(dene("  let x = false || ilk(l)? > 0"),
                    "'||' işlecinin sağında")
        self.hatali(dene("  let x = if true { ilk(l)? } else { 0 }"),
                    "değer üreten 'if'in dallarında")
        self.hatali(dene("  let x = match 1 { _ -> ilk(l)? }"),
                    "değer üreten 'match'in kollarında")
        self.hatali(dene("  while ilk(l)? > 0 { break }"),
                    "while koşulunda")
        self.hatali(dene("  let f = |x: [Int]| ilk(x)?"),
                    "tek ifadelik lambda gövdesinde")

    def test_if_let(self):
        """`if let` opsiyoneli açar; ad yalnız then dalında görünür."""
        ust = "fn belki(a: Int) -> Int? = if a > 0 { a } else { none }\n"
        self.gecerli(ust + wrap(
            "if let v = belki(5) { print(v + 1) }"))
        self.gecerli(ust + wrap(
            "if let v = belki(5) { print(v) } else if let w = belki(2) { print(w) } else { print(0) }"))
        # Açılmış değer opsiyonel değil: `!` gereksiz, `+` çalışır.
        self.gecerli(ust + wrap(
            "if let v = belki(1) { let t: Int = v }"))
        # `else` dalında ad yok.
        self.hatali(ust + wrap(
            "if let v = belki(1) { print(v) } else { print(v) }"),
            "tanımsız")
        # Opsiyonel olmayan değer bağlanamaz.
        self.hatali(wrap("if let v = 5 { print(v) }"),
                    "opsiyonel bir değer bekler")
        # Ad bloğun dışına sızmamalı.
        self.hatali(ust + wrap(
            "if let v = belki(1) { print(v) }\nprint(v)"),
            "tanımsız")

    def test_indeksli_dongu(self):
        """İkinci döngü değişkeni sıra numarasıdır."""
        self.gecerli(wrap(
            'for (i, x) in ["a", "b"] { print(i + 1, x) }'))
        self.gecerli(wrap(
            'for (i, c) in "abc" { print(i, c) }'))
        # İndeks Int, öğe kendi tipinde: karıştırmak hata olmalı.
        self.hatali(
            wrap('for (i, x) in ["a"] { print(i.upper()) }'),
            "upper")
        # Aralık zaten sayı üretiyor; ikinci değişken anlamsız.
        self.hatali(
            wrap("for (i, x) in 1..=3 { print(i) }"),
            "aralık üzerinde tek değişken")
        # Üç değişken hiçbir kaynakta yok.
        self.hatali(
            wrap('for (a, b, c) in ["x"] { print(a) }'),
            "döngü değişkeni")

    def test_bilinmeyen_tip(self):
        self.hatali("fn main() { let x: Yok = 1\n print(str(x)) }", "bilinmeyen tip")

    def test_yerlesik_golgelenebilir(self):
        """Kullanıcı bir yerleşiğin adını kullanabilir; kendi tanımı kazanır.

        Eskiden bu bir hataydı. Ama o kural, dile her yeni yerleşik
        eklendiğinde mevcut programları kırma riski taşıyor: `ozet` adlı bir
        yerleşik eklenince depodaki bir örnek derlenemez oldu.
        """
        kaynak = (
            'fn ozet(l: [Int]) -> String = "${l.len()} öğe"\n'
            "fn main() { print(ozet([1, 2, 3])) }"
        )
        module = parse(kaynak, "t.nar")
        checker = Checker(module, kaynak)
        checker.check()  # hata vermemeli

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
