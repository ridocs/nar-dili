"""Nar sanal makinesi — dilin kendi çalıştırma modeli.

İki soru sınanıyor:

1. **Doğru mu?** Programlar beklenen çıktıyı veriyor mu, hatalar anlaşılır
   mı?
2. **JavaScript arka ucuyla aynı mı?** İki hedef aynı dili uyguluyor;
   ayrı sonuç vermeleri birinin yanlış olduğu anlamına gelir. Bu yüzden
   aynı programlar hem VM'de hem Node'da çalıştırılıp karşılaştırılıyor.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import bytecode as bc  # noqa: E402
from narc import vm as vm_modulu  # noqa: E402
from narc import vm_metotlar  # noqa: E402
from narc.backends import bytecode_uretici  # noqa: E402
from narc.backends import js as js_backend  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.parser import parse  # noqa: E402

vm_metotlar.kur()

NODE = shutil.which("node")


def derle(kaynak: str):
    module = parse(kaynak, "t.nar")
    checker = Checker(module, kaynak)
    checker.check()
    return module, checker


def vm_cikti(kaynak: str, argumanlar: list | None = None) -> str:
    module, checker = derle(kaynak)
    program = bytecode_uretici.uret(module, checker)
    makine = vm_modulu.calistir(program, argumanlar, cikti_yaz=False)
    return "\n".join(makine.cikti)


def js_cikti(kaynak: str) -> str:
    module, checker = derle(kaynak)
    kod = js_backend.generate(module, checker)
    with tempfile.TemporaryDirectory() as tmp:
        betik = Path(tmp) / "p.js"
        betik.write_text(kod, encoding="utf-8")
        sonuc = subprocess.run([NODE, str(betik)], capture_output=True,
                               text=True, encoding="utf-8", timeout=120)
    return (sonuc.stdout + sonuc.stderr).strip()


def sar(govde: str) -> str:
    return f"fn main() {{\n{govde}\n}}"


class VMTesti(unittest.TestCase):
    def esit(self, kaynak: str, beklenen: str):
        self.assertEqual(vm_cikti(kaynak), beklenen.strip())

    # --- temel ------------------------------------------------------------

    def test_merhaba(self):
        self.esit(sar('print("merhaba")'), "merhaba")

    def test_aritmetik(self):
        self.esit(sar("print(1 + 2 * 3, 10 - 4, 3 * 4)"), "7 6 12")

    def test_tam_bolme_sifira_dogru_kirpar(self):
        """`-7 / 2` → -3 (JavaScript gibi), Python'un -4'ü değil."""
        self.esit(sar("print(7 / 2, -7 / 2, 7 % 3, -7 % 3)"), "3 -3 1 -1")

    def test_ondalik_bolme(self):
        self.esit(sar("print(7 / 2.0, 1.0 + 2, 3.0 * 2)"), "3.5 3.0 6.0")

    def test_metin_islemleri(self):
        self.esit(
            sar('let s = "Merhaba"\n'
                'print(s.upper(), s.len(), s.slice(0, 3), s + " Dünya")'),
            "MERHABA 7 Mer Merhaba Dünya",
        )

    def test_turkce_buyuk_kucuk(self):
        self.esit(
            sar('print("istanbul".upperTr(), "IĞDIR".lowerTr())'),
            "İSTANBUL ığdır",
        )

    def test_karsilastirma_ve_mantik(self):
        self.esit(
            sar("print(3 < 5, 3 == 3, 3 != 3, true && false, true || false, !true)"),
            "true true false false true false",
        )

    def test_kisa_devre(self):
        """`&&` sağ tarafı gereksizse değerlendirmemeli."""
        self.esit(
            "fn yan() -> Bool {\n  print(\"çağrıldı\")\n  return true\n}\n"
            + sar("let a = false && yan()\n  print(a)"),
            "false",
        )

    # --- akış -------------------------------------------------------------

    def test_if_else(self):
        self.esit(
            sar('let n = 7\n'
                'if n > 10 { print("büyük") } else if n > 5 { print("orta") }'
                ' else { print("küçük") }'),
            "orta",
        )

    def test_while_ve_break(self):
        self.esit(
            sar("var i = 0\n  while true {\n    i += 1\n"
                "    if i >= 3 { break }\n  }\n  print(i)"),
            "3",
        )

    def test_continue(self):
        self.esit(
            sar("var t = 0\n  for i in 1..=5 {\n"
                "    if i % 2 == 0 { continue }\n    t += i\n  }\n  print(t)"),
            "9",
        )

    def test_for_aralik_ve_liste(self):
        self.esit(
            sar("var t = 0\n  for i in 0..5 { t += i }\n"
                "  for x in [10, 20] { t += x }\n  print(t)"),
            "40",
        )

    def test_for_metin_ve_esleme(self):
        self.esit(
            sar('var s = ""\n  for c in "abc" { s += c + "-" }\n  print(s)\n'
                '  let m = {"a": 1, "b": 2}\n  var t = 0\n'
                "  for (k, v) in m { t += v }\n  print(t)"),
            "a-b-c-\n3",
        )

    # --- veri yapıları ----------------------------------------------------

    def test_liste_metotlari(self):
        self.esit(
            sar("let l = [5, 3, 8, 1]\n"
                "print(l.sort(), l.reverse(), l.toplam(), l.enBuyuk() ?? 0)"),
            "[1, 3, 5, 8] [1, 8, 3, 5] 17 8",
        )

    def test_map_filter_reduce(self):
        self.esit(
            sar("let l = [1, 2, 3, 4]\n"
                "print(l.map(|x| x * 2), l.filter(|x| x > 2),"
                " l.reduce(|a, b| a + b, 0))"),
            "[2, 4, 6, 8] [3, 4] 10",
        )

    def test_esleme(self):
        self.esit(
            sar('var m = {"a": 1}\n  m.set("b", 2)\n'
                'print(m.len(), m["a"] ?? 0, m.has("b"), m.keys())'),
            '2 1 true ["a", "b"]',
        )

    def test_struct_ve_metot(self):
        self.esit(
            "struct Nokta {\n  var x: Int\n  var y: Int\n"
            "  fn topla() -> Int = self.x + self.y\n"
            "  fn tasi(d: Int) { self.x += d }\n}\n"
            + sar("let n = Nokta { x: 3, y: 4 }\n  print(n.topla())\n"
                  "  n.tasi(2)\n  print(n.x, n)"),
            "7\n5 Nokta { x: 5, y: 4 }",
        )

    def test_enum_ve_match(self):
        self.esit(
            "enum Hava { Gunesli  Yagmurlu(Int) }\n"
            "fn anlat(h: Hava) -> String = match h {\n"
            '  Gunesli -> "güneşli"\n'
            '  Yagmurlu(mm) -> "yağmur ${mm}mm"\n}\n'
            + sar('print(anlat(Gunesli), anlat(Yagmurlu(12)))'),
            "güneşli yağmur 12mm",
        )

    def test_opsiyonel(self):
        self.esit(
            sar('let a: Int? = none\n  let b: Int? = 5\n'
                "print(a ?? 0, b ?? 0, b!)"),
            "0 5 5",
        )

    def test_guvenli_erisim(self):
        self.esit(
            "struct K { ad: String }\n"
            + sar('let yok: K? = none\n'
                  '  let var_: K? = K { ad: "Nar" }\n'
                  'print(yok?.ad ?? "yok", var_?.ad ?? "yok")'),
            "yok Nar",
        )

    # --- işlevler ---------------------------------------------------------

    def test_ozyineleme(self):
        self.esit(
            "fn fib(n: Int) -> Int {\n  if n < 2 { return n }\n"
            "  return fib(n - 1) + fib(n - 2)\n}\n"
            + sar("print(fib(15))"),
            "610",
        )

    def test_closure_yakalama(self):
        self.esit(
            sar("let k = 10\n  let ekle = |x: Int| -> Int { return x + k }\n"
                "print(ekle(5), [1, 2].map(ekle))"),
            "15 [11, 12]",
        )

    def test_ic_ice_closure(self):
        self.esit(
            "fn uretici(n: Int) -> (Int) -> Int = |x| x * n\n"
            + sar("let uc = uretici(3)\n  print(uc(7))"),
            "21",
        )

    def test_blok_ifadesi(self):
        self.esit(
            sar("let x = if true {\n    let a = 2\n    a * 21\n  } else { 0 }\n"
                "print(x)"),
            "42",
        )

    # --- hatalar ----------------------------------------------------------

    def hata_ver(self, kaynak: str, parca: str):
        with self.assertRaises(vm_modulu.NarCalismaHatasi) as ctx:
            vm_cikti(kaynak)
        self.assertIn(parca, str(ctx.exception))

    def test_sifira_bolme(self):
        self.hata_ver(sar("let a = 0\n  print(1 / a)"), "sıfıra bölme")

    def test_liste_disina_erisim(self):
        self.hata_ver(sar("let l = [1, 2]\n  print(l[5])"), "sınır dışı")

    def test_none_acma(self):
        self.hata_ver(sar("let a: Int? = none\n  print(a!)"), "none")

    def test_panik(self):
        self.hata_ver(sar('panic("bir şey ters gitti")'), "bir şey ters gitti")

    def test_cagri_izi(self):
        """Hata iletisinde hangi işlevlerden geçildiği görünmeli."""
        with self.assertRaises(vm_modulu.NarCalismaHatasi) as ctx:
            vm_cikti("fn ic() { panic(\"derin\") }\n"
                     "fn dis() { ic() }\n" + sar("dis()"))
        mesaj = str(ctx.exception)
        self.assertIn("ic içinde", mesaj)
        self.assertIn("dis içinde", mesaj)

    def test_sonsuz_ozyineleme_durduruluyor(self):
        self.hata_ver("fn s() -> Int = s()\n" + sar("print(s())"), "çok derin")

    # --- bytecode dosyası -------------------------------------------------

    def test_bytecode_yazilip_okunuyor(self):
        kaynak = sar('print("gidip geldi", 40 + 2)')
        module, checker = derle(kaynak)
        program = bytecode_uretici.uret(module, checker)

        veri = bc.yaz_dosya(program)
        self.assertTrue(veri.startswith(bc.SIHIR))

        geri = bc.oku_dosya(veri)
        makine = vm_modulu.calistir(geri, cikti_yaz=False)
        self.assertEqual(makine.cikti, ["gidip geldi 42"])

    def test_bozuk_bytecode_reddediliyor(self):
        with self.assertRaises(ValueError) as ctx:
            bc.oku_dosya(b"bu bytecode degil")
        self.assertIn("bytecode dosyası değil", str(ctx.exception))

    def test_ileri_surumlu_bytecode_reddediliyor(self):
        import struct as _struct
        sahte = bc.SIHIR + _struct.pack("<I", bc.BICIM_SURUMU + 9) + b"{}"
        with self.assertRaises(ValueError) as ctx:
            bc.oku_dosya(sahte)
        self.assertIn("biçimi", str(ctx.exception))

    # --- kapsam dışı ------------------------------------------------------

    def test_sayfa_islemleri_net_hata_veriyor(self):
        """DOM sanal makinede yok; mesaj bunu açıkça söylemeli."""
        with self.assertRaises(bytecode_uretici.UretimHatasi) as ctx:
            vm_cikti(sar('let e = bul("#x")'))
        mesaj = str(ctx.exception)
        self.assertIn("sanal makinede yok", mesaj)
        self.assertIn("target web", mesaj)


@unittest.skipIf(NODE is None, "node bulunamadı")
class IkiHedefAyniTesti(unittest.TestCase):
    """Sanal makine ile JavaScript arka ucu aynı sonucu vermeli."""

    ORNEKLER = [
        sar("print(1 + 2 * 3 - 4, 10 / 3, 10 % 3, -7 / 2, -7 % 3)"),
        sar("print(7 / 2.0, 2.0 * 3, 1 + 0.5, 10.0 / 4)"),
        sar('print("a" + 1, "b" + 1.5, "c" + true, "d" + [1, 2])'),
        sar('print([1, 2, 3], {"a": 1}, none, true, false)'),
        sar('print("Merhaba".upper(), "ABC".lower(), "  x  ".trim())'),
        sar('print("istanbul".upperTr(), "IĞDIR".lowerTr())'),
        sar('print("a,b,c".split(","), "a-b".replace("-", "+"))'),
        sar("print([3, 1, 2].sort(), [1, 2].reverse(), [1, 2, 3].join(\"-\"))"),
        sar("print([1, 2, 3].toplam(), [1, 2, 3].ortalama(), [1, 2].carpim())"),
        sar("print([1, 2, 3].map(|x| x * 2).filter(|x| x > 2))"),
        sar("print(abs(-3), min(2, 5), max(2, 5), sqrt(16.0))"),
        sar("print(floor(3.7), ceil(3.2), round(3.5), round(2.5))"),
        sar('print(int("42"), float("3.5"), str(42), len("abc"))'),
        "struct N { x: Int  y: Int }\n" + sar("print(N { x: 1, y: 2 })"),
        "enum E { Bir  Iki(Int) }\n" + sar("print(Bir, Iki(5))"),
        "fn f(n: Int) -> Int {\n  if n < 2 { return n }\n"
        "  return f(n - 1) + f(n - 2)\n}\n" + sar("print(f(18))"),
        sar("var t = 0\n  for i in 1..=100 { t += i }\n  print(t)"),
        sar('var s = ""\n  for c in "abcç" { s += c }\n  print(s, s.len())'),
        sar('let m = {"b": 2, "a": 1}\n  print(m.keys(), m.values(), m.len())'),
        sar("let x: Int? = none\n  print(x ?? 7, x == none)"),
    ]

    def test_ciktilar_ortusuyor(self):
        for i, kaynak in enumerate(self.ORNEKLER):
            with self.subTest(ornek=i):
                self.assertEqual(
                    vm_cikti(kaynak), js_cikti(kaynak),
                    f"örnek {i} iki hedefte ayrışıyor:\n{kaynak}",
                )

    def test_depodaki_ornekler_ortusuyor(self):
        """Gerçek örnek programlar da iki hedefte aynı çıktıyı vermeli."""
        # Sayfa, sunucu ve zamana bağlı olanlar dışarıda: VM'de DOM yok,
        # sunucu sonsuza kadar çalışır, süre ölçümü iki hedefte farklıdır.
        from narc.driver import compile_file

        # Elle dışarıda bırakılanlar: ilki sayfa yerleşiklerini çatı
        # kullanmadan doğrudan çağırıyor, ötekiler zamana ve dış dünyaya
        # bağlı. Bunları kaynağa bakarak ayırmanın kısa bir yolu yok.
        disarida = {"sayac_web.nar", "metin_araclari.nar", "dosya_araci.nar"}

        def sayfa_ya_da_sunucu(yol: Path) -> bool:
            """Tarayıcı/sunucu çatısını içe aktaran örnek VM'de çalışmaz.

            Listeyi elle tutmak her yeni örnekte eskiyordu; içe aktarmaya
            bakmak kendiliğinden güncel kalır.
            """
            kaynak = yol.read_text(encoding="utf-8-sig")
            return any(f'{ad}"' in kaynak
                       for ad in ("arayuz.nar", "web.nar"))

        dosyalar = [p for p in sorted((KOK / "ornekler").glob("*.nar"))
                    if p.name not in disarida and not sayfa_ya_da_sunucu(p)]
        self.assertGreater(len(dosyalar), 1)

        for yol in dosyalar:
            with self.subTest(ornek=yol.name):
                # `compile_file` içe aktarmaları da çözer.
                derleme = compile_file(yol)
                program = bytecode_uretici.uret(derleme.module, derleme.checker)
                makine = vm_modulu.calistir(program, cikti_yaz=False)
                alinan = chr(10).join(makine.cikti)

                with tempfile.TemporaryDirectory() as tmp:
                    betik = Path(tmp) / "p.js"
                    betik.write_text(derleme.to_js(), encoding="utf-8")
                    sonuc = subprocess.run(
                        [NODE, str(betik)], capture_output=True, text=True,
                        encoding="utf-8", timeout=120)
                beklenen = (sonuc.stdout + sonuc.stderr).strip()

                self.assertEqual(alinan, beklenen)


if __name__ == "__main__":
    unittest.main()
