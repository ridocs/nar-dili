"""Nar ile yazılan tip denetleyici, Python'unkiyle aynı hataları bulmalı.

`derleyici/denetleyici.nar`, derleyiciyi kendi diline taşıma yolundaki
dördüncü adımdır (lexer, çözümleyici ve tip sisteminden sonra).

**Kapsam:** şu an yalnızca *bildirim* aşaması karşılaştırılıyor — struct,
enum, arayüz, tip takma adı ve fonksiyon imzalarının toplanması, tip
ifadelerinin çözümlenmesi, üstlenilen arayüzlerin doğrulanması ve `main`
denetimi. Gövde denetimi (ifadeler, deyimler) henüz Nar'a taşınmadı.

Bu yüzden karşılaştırma iki yönlü çalışır:
  - Nar'ın bulduğu her hata Python'da da bulunmalı (yanlış alarm yok).
  - Bildirim düzeyindeki örneklerde iki taraf birebir aynı listeyi vermeli.

Karşılaştırma mesajı da konumu da (satır, sütun) kapsar.
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

from narc.checker import Checker  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.driver import compile_file  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")
DENETLEYICI = KOK / "derleyici" / "denetle.nar"


def python_hatalari(kaynak: str, kutuphane: bool = False) -> list[dict]:
    """Python denetleyicisinin bulduğu hatalar: mesaj ve konum (sırayla)."""
    module = parse(kaynak, "t.nar")
    checker = Checker(module, kaynak, kutuphane=kutuphane)
    try:
        checker.check()
    except NarError as err:
        hatalar = getattr(err, "errors", None)
        if hatalar is None:
            hatalar = [err]
        return [
            {"mesaj": h.message, "satir": h.span.line, "sutun": h.span.col}
            for h in hatalar
        ]
    return []


def nar_hatalari(betik: Path, kaynaklar: list[str], kutuphane: bool) -> list:
    surucu = (
        f"require({str(betik).replace(chr(92), '/')!r});\n"
        "let veri = '';\n"
        "process.stdin.setEncoding('utf8');\n"
        "process.stdin.on('data', (p) => { veri += p; });\n"
        "process.stdin.on('end', () => {\n"
        "  const girdi = JSON.parse(veri);\n"
        "  const cikti = girdi.map((k) => {\n"
        f"    const c = Nar.kaynagiDenetle(k, {str(kutuphane).lower()});\n"
        "    if (c.$tag !== 'DTamam') return {cozumHatasi: c.$values[0]};\n"
        "    return {hatalar: c.$values[0].map(\n"
        "      (h) => ({mesaj: h.mesaj, satir: h.satir, sutun: h.sutun}))};\n"
        "  });\n"
        "  process.stdout.write(JSON.stringify(cikti));\n"
        "});\n"
    )
    sonuc = subprocess.run(
        [NODE, "-e", surucu], input=json.dumps(kaynaklar),
        capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    if sonuc.returncode != 0:
        raise AssertionError("Nar denetleyici çalışmadı:\n" + sonuc.stderr.strip())
    return json.loads(sonuc.stdout)


# Bildirim aşamasında üretilen hatalar. Gövde denetimi Nar'a taşınmadığı
# için karşılaştırma bu mesajlarla sınırlı tutulur.
BILDIRIM_HATALARI = (
    "tipi zaten tanımlı",
    "alanı yinelendi",
    "varyantı yinelendi",
    "metodu yinelendi",
    "hem alan hem metot olamaz",
    "parametresi yinelendi",
    "fonksiyonu zaten tanımlı",
    "yerleşik bir fonksiyon",
    "bilinmeyen tip",
    "bilinmeyen arayüz",
    "tip argümanı almaz",
    "tip argümanı alamaz",
    "tip argümanı bekler",
    "eşleme anahtarı",
    "arayüzünü üstleniyor ama",
    "imzası arayüzle uyuşmuyor",
    "programda 'main' fonksiyonu yok",
    "'main' parametre almamalı",
)


def bildirim_hatasi_mi(h: dict) -> bool:
    return any(p in h["mesaj"] for p in BILDIRIM_HATALARI)


@unittest.skipIf(NODE is None, "node bulunamadı")
class NarDenetleyiciTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        kod = compile_file(DENETLEYICI, kutuphane=True).to_js()
        cls.betik = Path(cls._tmp.name) / "nar-denetleyici.js"
        cls.betik.write_text(kod, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def karsilastir(self, kaynaklar: list[str], adlar: list[str],
                    kutuphane: bool = False):
        sonuclar = nar_hatalari(self.betik, kaynaklar, kutuphane)
        for ad, kaynak, sonuc in zip(adlar, kaynaklar, sonuclar):
            with self.subTest(kaynak=ad):
                self.assertNotIn("cozumHatasi", sonuc,
                                 f"{ad}: Nar çözümleyici kaynağı okuyamadı")
                alinan = sonuc["hatalar"]
                beklenen = [h for h in python_hatalari(kaynak, kutuphane)
                            if bildirim_hatasi_mi(h)]
                self.assertEqual(alinan, beklenen, f"{ad}: hata listeleri ayrışıyor")

    def test_dogru_programlarda_hata_yok(self):
        ornekler = [
            'fn main() { print("merhaba") }',
            "struct Nokta { x: Int  y: Int }\nfn main() { }",
            "enum Hava { Gunesli  Yagmurlu(Int) }\nfn main() { }",
            "struct Kutu<T> { deger: T }\nfn main() { }",
            "enum Sonuc<T, H> { Tamam(T)  Hata(H) }\nfn main() { }",
            "type Sayi = Int\nfn main() { }",
            "type Harita = {String: [Int]}\nfn main() { }",
            "interface Yaz { fn yaz() -> String }\n"
            "struct N: Yaz { a: Int\n  fn yaz() -> String = \"n\" }\nfn main() { }",
            "fn f<T>(x: T) -> T = x\nfn main() { }",
            "fn f<T: Yaz>(x: T) -> String = x.yaz()\n"
            "interface Yaz { fn yaz() -> String }\nfn main() { }",
            "struct Dugum { var sonraki: Dugum? }\nfn main() { }",
            "struct A { b: B }\nstruct B { a: Int }\nfn main() { }",
            "fn f(g: (Int, String) -> Bool) -> Bool = g(1, \"a\")\nfn main() { }",
        ]
        self.karsilastir(ornekler, [f"doğru {i}" for i in range(len(ornekler))])

    def test_bildirim_hatalari(self):
        ornekler = [
            # tip adı çakışması
            "struct A { x: Int }\nstruct A { y: Int }\nfn main() { }",
            "struct A { x: Int }\nenum A { Bir }\nfn main() { }",
            "interface I { fn m() -> Int }\ninterface I { fn n() -> Int }\nfn main() { }",
            # yinelenen üyeler
            "struct A { x: Int\n  x: String }\nfn main() { }",
            "enum E { Bir  Bir }\nfn main() { }",
            "interface I { fn m() -> Int\n  fn m() -> String }\nfn main() { }",
            "struct A { x: Int\n  fn x() -> Int = 1 }\nfn main() { }",
            # fonksiyonlar
            "fn f() { }\nfn f() { }\nfn main() { }",
            "fn print() { }\nfn main() { }",
            "fn f(a: Int, a: Int) { }\nfn main() { }",
            # bilinmeyen tip
            "struct A { x: Bilinmeyen }\nfn main() { }",
            "fn f(x: Yok) { }\nfn main() { }",
            "fn f() -> Yok { }\nfn main() { }",
            "type T = Yok\nfn main() { }",
            # tip argümanı sayısı
            "struct Kutu<T> { deger: T }\nfn f(k: Kutu<Int, String>) { }\nfn main() { }",
            "struct Kutu<T> { deger: T }\nfn f(k: Int<String>) { }\nfn main() { }",
            "enum E { Bir }\nfn f(e: E<Int>) { }\nfn main() { }",
            # eşleme anahtarı
            "fn f(m: {[Int]: Int}) { }\nfn main() { }",
            # arayüz uyumu
            "interface Yaz { fn yaz() -> String }\nstruct N: Yaz { a: Int }\nfn main() { }",
            "interface Yaz { fn yaz() -> String }\n"
            "struct N: Yaz { a: Int\n  fn yaz() -> Int = 1 }\nfn main() { }",
            "struct N: Yok { a: Int }\nfn main() { }",
            "interface Yaz { fn yaz() -> String }\nenum E: Yaz { Bir }\nfn main() { }",
            # main
            "fn baska() { }",
            "fn main(x: Int) { }",
        ]
        self.karsilastir(ornekler, [f"hatalı {i}" for i in range(len(ornekler))])

    def test_kutuphane_modunda_main_aranmaz(self):
        self.karsilastir(
            ["fn yardimci() -> Int = 1", "struct A { x: Int }"],
            ["kütüphane 0", "kütüphane 1"],
            kutuphane=True,
        )

    def test_proje_dosyalarinda_yanlis_alarm_yok(self):
        """Nar denetleyici, Python'un görmediği bir hata uydurmamalı.

        Bu dosyalar `import` ile birbirine bağlı; tek başına çözümlendiğinde
        başka dosyadaki tipler bilinmez, iki taraf da "bilinmeyen tip" der.
        Listeler birebir karşılaştırılamaz çünkü Python gövdeleri de
        denetliyor (orada da aynı mesaj çıkabilir) ve Nar henüz denetlemiyor.
        Karşılaştırma bu yüzden alt küme ilişkisi üzerinden yapılır: Nar'ın
        söylediği her şeyi Python da söylemeli.
        """
        dosyalar = []
        for klasor in ("araclar", "derleyici"):
            dosyalar.extend(sorted((KOK / klasor).glob("*.nar")))
        self.assertGreater(len(dosyalar), 5)

        kaynaklar = [d.read_text(encoding="utf-8-sig") for d in dosyalar]
        sonuclar = nar_hatalari(self.betik, kaynaklar, True)
        for yol, kaynak, sonuc in zip(dosyalar, kaynaklar, sonuclar):
            with self.subTest(dosya=yol.name):
                self.assertNotIn("cozumHatasi", sonuc)
                python_kumesi = {
                    (h["mesaj"], h["satir"], h["sutun"])
                    for h in python_hatalari(kaynak, True)
                }
                uydurulan = [
                    h for h in sonuc["hatalar"]
                    if (h["mesaj"], h["satir"], h["sutun"]) not in python_kumesi
                ]
                self.assertEqual(
                    uydurulan, [],
                    f"{yol.name}: Python'un görmediği hata(lar) bildirildi",
                )


if __name__ == "__main__":
    unittest.main()
