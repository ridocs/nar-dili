"""JSON kütüphanesi (`araclar/json.nar`) uçtan uca testleri.

Kütüphane IDE ile sunucu arasındaki her cevabı okur; buradaki bir yanlış
IDE'de "hata yokken hata" olarak görünür.
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

from narc.driver import compile_file  # noqa: E402

NODE = shutil.which("node")
JSON_NAR = KOK / "araclar" / "json.nar"


def calistir(govde: str) -> str:
    """`main` gövdesini json.nar ile derler, Node ile çalıştırır, çıktıyı döndürür."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak = Path(tmp) / "program.nar"
        # Kütüphaneye göreli import'un çözülebilmesi için mutlak yol yazılır.
        kaynak.write_text(
            f'import "{JSON_NAR.as_posix()}"\n\nfn main() {{\n{govde}\n}}\n',
            encoding="utf-8",
        )
        kod = compile_file(kaynak).to_js()
        betik = Path(tmp) / "program.js"
        betik.write_text(kod, encoding="utf-8")
        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
        )
    return (sonuc.stdout + sonuc.stderr).strip()


@unittest.skipIf(NODE is None, "node bulunamadı")
class JsonTesti(unittest.TestCase):
    def test_null_alan_yok_sayilir(self):
        """`{"hata": null}` ile alanın hiç olmaması aynı şeydir.

        Sunucu başarıda `"hata": null` yollar; IDE bunu `if let` ile
        yakalayınca hata yokken hata bloğu basıyordu.
        """
        self.assertEqual(calistir('''
  let veri = jsonOku("{\\"kod\\": \\"x\\", \\"hata\\": null}")
  if let hata = alan(veri, "hata") {
    print("HATA YAKALANDI")
  } else {
    print("hata yok")
  }
  print(alan(veri, "hata") == none)
  print(alan(veri, "yok") == none)
  print(metinAl(alan(veri, "kod")) ?? "?")
'''), "hata yok\ntrue\ntrue\nx")

    def test_dizin_null_yok_sayilir(self):
        self.assertEqual(calistir('''
  let veri = jsonOku("[1, null]")
  print(dizin(veri, 0) != none)
  print(dizin(veri, 1) == none)
  print(dizin(veri, 2) == none)
'''), "true\ntrue\ntrue")

    def test_gercek_null_yazilir(self):
        """Okuma tarafı `null`'ı yok sayar; yazma tarafı onu korur."""
        self.assertEqual(calistir('''
  print(jsonYaz(Json.Nesne({"a": Json.Bos})))
'''), '{"a":null}')


if __name__ == "__main__":
    unittest.main()
