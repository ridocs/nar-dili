"""Kod biçimlendirici testleri.

Biçimlendiricinin kendisi Nar diliyle yazılmıştır
(`araclar/bicimlendirici.nar`); bu testler onu Node üzerinden çalıştırır.
"""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.bicim import bicimlendir  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")


@unittest.skipIf(NODE is None, "node bulunamadı")
class BicimlendiriciTesti(unittest.TestCase):
    def esit(self, girdi: str, beklenen: str):
        self.assertEqual(bicimlendir(girdi), beklenen)

    def test_girinti_duzeltilir(self):
        self.esit(
            'fn main() {\nprint("a")\n}\n',
            'fn main() {\n  print("a")\n}\n',
        )

    def test_fazla_girinti_geri_alinir(self):
        self.esit(
            'fn main() {\n        print("a")\n}\n',
            'fn main() {\n  print("a")\n}\n',
        )

    def test_ic_ice_bloklar(self):
        self.esit(
            'fn main() {\nif true {\nprint("a")\n}\n}\n',
            'fn main() {\n  if true {\n    print("a")\n  }\n}\n',
        )

    def test_else_ayni_seviyede(self):
        sonuc = bicimlendir('fn main() {\nif true {\nprint("a")\n} else {\nprint("b")\n}\n}\n')
        satirlar = sonuc.splitlines()
        self.assertIn("  } else {", satirlar)

    def test_lambda_iceren_cagri_tek_seviye(self):
        # Regresyon: `f("x", || {` satırı hem ( hem { açar; girinti yine
        # tek seviye artmalı.
        sonuc = bicimlendir(
            'fn main() {\nkayit("t", || {\nprint("ic")\n})\n}\n'
            'fn kayit(a: String, f: () -> Void) { f() }\n'
        )
        self.assertIn('  kayit("t", || {', sonuc)
        self.assertIn('    print("ic")', sonuc)
        self.assertIn("  })", sonuc)

    def test_ic_ice_liste(self):
        # Devam satırlarının kendi aralarındaki hizalaması korunur; hepsi
        # yalnızca açılış satırıyla aynı miktarda kayar.
        sonuc = bicimlendir("fn main() {\nlet a = [[\n1\n]]\n}\n")
        satirlar = sonuc.splitlines()
        self.assertIn("  let a = [[", satirlar)
        self.assertIn("  1", satirlar)
        self.assertIn("  ]]", satirlar)

    def test_devam_satirlari_goreli_kalir(self):
        # Yazar girinti vermişse o girinti korunur (bloğa göre kaydırılır).
        sonuc = bicimlendir("fn main() {\nlet a = [\n  1,\n]\n}\n")
        satirlar = sonuc.splitlines()
        self.assertIn("  let a = [", satirlar)
        self.assertIn("    1,", satirlar)
        self.assertIn("  ]", satirlar)

    def test_satir_sonu_bosluklari_atilir(self):
        self.esit('fn main() {\n  print("a")   \n}\n', 'fn main() {\n  print("a")\n}\n')

    def test_ardisik_bos_satirlar_teke_iner(self):
        sonuc = bicimlendir('fn main() {\n  let a = 1\n\n\n\n  let b = 2\n}\n')
        self.assertNotIn("\n\n\n", sonuc)
        self.assertIn("\n\n", sonuc)

    def test_metin_icindeki_parantez_sayilmaz(self):
        # "{" bir metin içindeyse girinti seviyesini etkilememeli
        sonuc = bicimlendir('fn main() {\nprint("{")\nprint("bitti")\n}\n')
        self.assertIn('  print("{")', sonuc)
        self.assertIn('  print("bitti")', sonuc)

    def test_yorumdaki_parantez_sayilmaz(self):
        sonuc = bicimlendir('fn main() {\n// burada bir { var\nprint("a")\n}\n')
        self.assertIn('  print("a")', sonuc)

    def test_devam_satirlari_korunur(self):
        # Çok satırlı koşulun hizalaması bozulmamalı, yalnızca blokla
        # birlikte kaymalı.
        sonuc = bicimlendir(
            "fn main() {\n"
            "var i = 0\n"
            "while i < 10 && (i % 2 == 0 ||\n"
            "                 i % 3 == 0) {\n"
            "i += 1\n"
            "}\n"
            "}\n"
        )
        satirlar = sonuc.splitlines()
        self.assertIn("  while i < 10 && (i % 2 == 0 ||", satirlar)
        # Devam satırı açılış parantezine göre hizalı kalmalı
        devam = [s for s in satirlar if "i % 3" in s][0]
        acilis = [s for s in satirlar if "i % 2" in s][0]
        self.assertEqual(devam.index("i % 3"), acilis.index("(") + 1)

    def test_cok_satirli_liste_girintilenir(self):
        sonuc = bicimlendir("fn main() {\nlet l = [\n  1,\n  2,\n]\n}\n")
        satirlar = sonuc.splitlines()
        self.assertIn("  let l = [", satirlar)
        self.assertIn("    1,", satirlar)
        self.assertIn("  ]", satirlar)

    def test_blok_yorumu_ici_korunur(self):
        sonuc = bicimlendir(
            "fn main() {\n/* birinci\n     ikinci\n   son */\nprint(\"a\")\n}\n"
        )
        self.assertIn("     ikinci", sonuc)
        self.assertIn('  print("a")', sonuc)

    def test_yarim_kalan_satirin_devami_iceri_alinir(self):
        # `=` ile biten satırdan sonraki satır bir kademe içeri girer.
        sonuc = bicimlendir(
            "struct S {\n"
            "a: String\n"
            "fn ozet() -> String =\n"
            '"${self.a}"\n'
            "}\n"
        )
        satirlar = sonuc.splitlines()
        self.assertIn("  fn ozet() -> String =", satirlar)
        self.assertIn('    "${self.a}"', satirlar)

    def test_virgul_devam_sayilmaz(self):
        # Virgülle biten satır zaten blok içindedir; fazladan girinti almamalı.
        sonuc = bicimlendir(
            "struct S { a: Int  b: Int }\n"
            "fn main() {\n"
            "let s = S {\n"
            "a: 1,\n"
            "b: 2\n"
            "}\n"
            "print(s.a)\n"
            "}\n"
        )
        satirlar = sonuc.splitlines()
        self.assertIn("    a: 1,", satirlar)
        self.assertIn("    b: 2", satirlar)

    def test_kararli(self):
        # İki kez biçimlendirmek aynı sonucu vermeli
        girdi = 'fn main() {\n   if true {\nprint("a")\n     }\n}\n'
        bir = bicimlendir(girdi)
        iki = bicimlendir(bir)
        self.assertEqual(bir, iki)

    def test_bicimlendirilmis_kod_hala_derleniyor(self):
        girdi = ('fn main() {\nlet l = [1, 2]\nfor e in l {\nprint(e)\n}\n}\n')
        sonuc = bicimlendir(girdi)
        module = parse(sonuc, "t.nar")
        Checker(module, sonuc).check()  # hata fırlatmamalı

    def test_cok_satirli_metnin_ici_korunur(self):
        """Üç tırnaklı metnin içindeki boşluk biçim değil, içeriktir.

        Biçimlendirici bu satırları kod sanıp yeniden girintiliyordu; yani
        kodun anlamını değil, verisini değiştiriyordu.
        """
        girdi = (
            'let CSS = """\n'
            ':root {\n'
            '  --a: 1;\n'
            '  --b: bir, iki,\n'
            '       uc, dort;\n'
            '}\n'
            '\n'
            '.kutu { color: red; }\n'
            '"""\n'
        )
        self.assertEqual(bicimlendir(girdi), girdi)

    def test_cagri_icindeki_lambda_govdesi(self):
        """Bir çağrının ortasında açılan blok, çağrının hizasından devam eder.

        Gövde sıfırdan girintileniyor, kapanıştan sonra da sonraki liste
        öğeleri sola kayıyordu.
        """
        girdi = (
            'fn ciz() -> Gorunum = Kart("Girdi", [\n'
            '  Giris("ad", "", |v| {\n'
            '    yaz(v)\n'
            '  }),\n'
            '  Metin("bitti")\n'
            '])\n'
        )
        self.assertEqual(bicimlendir(girdi), girdi)

    def test_cok_satirli_imza_govdeyi_kaydirmaz(self):
        """İkinci satır açılış parantezine hizalanır; gövde yine 2 boşlukta."""
        girdi = (
            'fn uzun(bir: String, iki: String,\n'
            '        uc: Int) {\n'
            '  print(bir)\n'
            '}\n'
        )
        self.assertEqual(bicimlendir(girdi), girdi)

    def test_ok_ile_biten_satir_devam_eder(self):
        """`->` satır sonunda kalırsa gövde bir kademe içeridedir."""
        girdi = (
            'fn ogeYap(g: Gorunum) -> Element = match g {\n'
            '  Kisa(a) -> kisaOge(a)\n'
            '  Uzun(a, b, c) ->\n'
            '    uzunOge(a, b, c)\n'
            '}\n'
        )
        self.assertEqual(bicimlendir(girdi), girdi)

    def test_proje_dosyalari_duzenli(self):
        """Kendi Nar dosyalarımız biçimlendiriciyle uyumlu olmalı."""
        dosyalar = sorted((KOK / "araclar").glob("*.nar")) + \
                   sorted((KOK / "ornekler").glob("*.nar")) + \
                   [KOK / "deneme.nar"]
        for yol in dosyalar:
            with self.subTest(dosya=yol.name):
                kaynak = yol.read_text(encoding="utf-8-sig")
                self.assertEqual(
                    bicimlendir(kaynak), kaynak,
                    f"{yol.name} biçimlendiriciye göre düzensiz",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
