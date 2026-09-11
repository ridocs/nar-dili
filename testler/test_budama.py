"""Çalışma zamanı budamasının programı değiştirmediğini doğrular.

Budama bir boyut iyileştirmesidir; davranışı değiştirmesi hata olur. Buradaki
ölçü şu: budanmış çıktı ile çalışma zamanının tamamı gömülmüş çıktı **aynı
sonucu** vermeli.

Ayrıca budanmış çıktıda hiçbir tanımsız yardımcı kalmamalı — eksik alınan bir
ad programı doğrudan kırar, fazladan alınan ad yalnızca çıktıyı büyütür.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import runtime_budama  # noqa: E402
from narc.backends.js import RUNTIME_PATH, JsBackend  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.driver import compile_file  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")

# Çalışma zamanı adları `$` ile başlar; Nar tanımlayıcıları `$` içeremez.
_YARDIMCI = re.compile(r"\$[A-Za-z_][\w$]*")

ORNEKLER = [
    'print("merhaba")',
    'print(1 + 2, 7 / 2, 7.0 / 2.0, -7 / 2)',
    'print("abc".upper(), "ABC".lower(), "a,b".split(","))',
    'print([3, 1, 2].sort(), [1, 2, 3].toplam(), [1, 2].join("-"))',
    'let m = {"a": 1}\n  print(m.keys(), m.values(), m.len())',
    'print([1, 2, 3].map(|x| x * 2).filter(|x| x > 2))',
    'let x: Int? = none\n  print(x ?? 7, x == none)',
    'print(str(3.5), int("42"), float("2"), abs(-3), sqrt(16.0))',
    'var t = 0\n  for i in 1..=10 { t += i }\n  print(t)',
    'print("şğüöçİ".upperTr(), "ŞĞÜÖÇI".lowerTr())',
]


def sar(govde: str) -> str:
    return "fn main() {\n  " + govde.replace("\n", "\n  ") + "\n}\n"


def derle(kaynak: str, ad: str = "t.nar") -> tuple[str, str]:
    """(budanmış, tam) JavaScript döndürür."""
    modul = parse(kaynak, ad)
    denetci = Checker(modul, kaynak)
    denetci.check()

    budanmis = JsBackend(modul, denetci).emit()
    # Karşılaştırma için aynı gövde, çalışma zamanının tamamıyla.
    govde = JsBackend(modul, denetci).govde_uret()
    tam = RUNTIME_PATH.read_text(encoding="utf-8").rstrip() + "\n\n" + govde
    return budanmis, tam


def calistir(kod: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        betik = Path(tmp) / "p.js"
        betik.write_text(kod, encoding="utf-8")
        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True,
            encoding="utf-8", timeout=120)
    return (sonuc.stdout + sonuc.stderr).strip()


def _bildirilenler(kod: str) -> set[str]:
    return set(re.findall(
        r"^(?:async\s+)?(?:function|class|const|let|var)\s+(\$[\w$]*)",
        kod, re.MULTILINE))


# Çalışma zamanının bildirdiği bütün adlar. Ölçüt bununla sınırlanır:
# üretilen kodda `$tag`, `$narName` gibi özellik adları ve `$son1` gibi
# geçici değişkenler de var, onlar yardımcı değil.
TUM_YARDIMCILAR = _bildirilenler(RUNTIME_PATH.read_text(encoding="utf-8"))


def tanimsiz_yardimcilar(kod: str) -> set[str]:
    """Kodda geçen ama budanmış çıktıda tanımı kalmamış yardımcılar."""
    gecen = {ad for ad in _YARDIMCI.findall(kod) if ad in TUM_YARDIMCILAR}
    return gecen - _bildirilenler(kod)


@unittest.skipIf(NODE is None, "node bulunamadı")
class BudamaTesti(unittest.TestCase):
    def test_ciktilar_ayni(self):
        """Budanmış ve tam çıktı aynı sonucu vermeli."""
        for i, govde in enumerate(ORNEKLER):
            with self.subTest(ornek=i):
                budanmis, tam = derle(sar(govde))
                self.assertEqual(calistir(budanmis), calistir(tam),
                                 f"örnek {i} budamadan sonra ayrışıyor:\n{govde}")

    def test_tanimsiz_yardimci_kalmiyor(self):
        """Budanmış çıktıda tanımsız bir çalışma zamanı adı olmamalı.

        Eksik alınan ad programı doğrudan kırar; bu denetim onu örnek
        çalıştırmadan da yakalar.
        """
        for i, govde in enumerate(ORNEKLER):
            with self.subTest(ornek=i):
                budanmis, _ = derle(sar(govde))
                self.assertEqual(tanimsiz_yardimcilar(budanmis), set())

    def test_depodaki_ornekler_ayrismiyor(self):
        """Gerçek örnek programlar da budamadan sonra aynı çıktıyı vermeli."""
        # Sayfa ve sunucu örnekleri burada çalıştırılamaz: DOM yok, sunucu
        # sonsuza kadar çalışır. Zamana bağlı olanlar da dışarıda.
        disarida = {"sayac_web.nar", "metin_araclari.nar", "dosya_araci.nar"}

        def sayfa_ya_da_sunucu(yol: Path) -> bool:
            kaynak = yol.read_text(encoding="utf-8-sig")
            return any(f'{ad}"' in kaynak for ad in ("arayuz.nar", "web.nar"))

        dosyalar = [p for p in sorted((KOK / "ornekler").glob("*.nar"))
                    if p.name not in disarida and not sayfa_ya_da_sunucu(p)]
        self.assertGreater(len(dosyalar), 1)

        for yol in dosyalar:
            with self.subTest(ornek=yol.name):
                derleme = compile_file(yol)
                budanmis = derleme.to_js()
                govde = JsBackend(derleme.module, derleme.checker).govde_uret()
                tam = (RUNTIME_PATH.read_text(encoding="utf-8").rstrip()
                       + "\n\n" + govde)
                self.assertEqual(tanimsiz_yardimcilar(budanmis), set())
                self.assertEqual(calistir(budanmis), calistir(tam))

    def test_kucuk_program_kucuk_cikti(self):
        """Budamanın gerçekten iş yaptığını sayıyla göster."""
        budanmis, tam = derle(sar('print("merhaba")'))
        self.assertLess(len(budanmis), len(tam) // 5,
                        "budama küçük programda belirgin kazanç vermeli")
        self.assertLess(len(budanmis), 4000)


class ParcalamaTesti(unittest.TestCase):
    """Ayırıcının kendi davranışı — Node gerekmez."""

    KAYNAK = (
        '// başlık\n'
        '"use strict";\n'
        '\n'
        '// bir\n'
        'function $bir(x) { return $iki(x); }\n'
        '\n'
        '// iki\n'
        'function $iki(x) { return x + 1; }\n'
        '\n'
        '// kullanılmayan\n'
        'function $uc() { return 3; }\n'
    )

    def test_gecisli_bagimlilik_alinir(self):
        cikti = runtime_budama.buda(self.KAYNAK, "$bir(1);")
        self.assertIn("function $bir", cikti)
        self.assertIn("function $iki", cikti, "geçişli bağımlılık alınmalı")
        self.assertNotIn("function $uc", cikti)

    def test_onsoz_her_zaman_kalir(self):
        cikti = runtime_budama.buda(self.KAYNAK, "")
        self.assertIn('"use strict"', cikti)
        self.assertNotIn("function $bir", cikti)

    def test_yorumlar_bagimlilik_saymaz(self):
        """Yorumda geçen ad parçayı çıktıya sokmamalı.

        Başlıktaki açıklama satırları sayılsaydı her program çalışma
        zamanının tamamını taşırdı.
        """
        kaynak = self.KAYNAK + '\n// $uc burada yalnızca yorumda geçiyor\n'
        cikti = runtime_budama.buda(kaynak, "$iki(1);")
        self.assertNotIn("function $uc", cikti)

    def test_metin_icindeki_ad_sayilir(self):
        """Metin literalindeki ad şüpheli sayılır ve alınır.

        Eksik almak programı kırar, fazladan almak yalnızca büyütür.
        """
        cikti = runtime_budama.buda(self.KAYNAK, 'let a = "$uc";')
        self.assertIn("function $uc", cikti)

    def test_yorum_bildirime_yapisik_kalir(self):
        cikti = runtime_budama.buda(self.KAYNAK, "$iki(1);")
        self.assertIn("// iki\nfunction $iki", cikti)


if __name__ == "__main__":
    unittest.main()
