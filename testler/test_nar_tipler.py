"""Nar ile yazılan tip sistemi, Python'unkiyle aynı yanıtları vermeli.

`derleyici/tipler.nar`, derleyiciyi kendi diline taşıma yolundaki üçüncü
adımdır (lexer ve çözümleyiciden sonra). Doğruluğunun ölçüsü şu: aynı
tipler için aynı yanıt.

İki taraf tip *tarifi* alışverişi yapmaz; ikisi de aynı sabit listeyi kurar
(`narc/tip_ornekleri.py` ve `testler/nar/tip_ornekleri.nar`). Listelerin
gerçekten örtüştüğü ilk testte, tip yazımı karşılaştırılarak doğrulanır —
o geçmezse diğer karşılaştırmalar anlamsız olurdu.

Karşılaştırılan işlemler:
  - tip yazımı            str(t)          ↔ tipMetni(t)
  - atanabilirlik         assignable      ↔ atanabilir      (40×40 çift)
  - ortak tip             common_type     ↔ ortakTip        (40×40 çift)
  - birleştirme           birlestir       ↔ birlestir       (40×40 çift)
  - tembel alan çözümü    .fields         ↔ .alanlar()
  - tip değişkeni arama   tipdegiskenleri ↔ tipDegiskenleri
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

from narc import types as T  # noqa: E402
from narc.driver import compile_file  # noqa: E402
from narc.tip_ornekleri import (  # noqa: E402
    kutu_sablonu, ornek_struct, ornek_tipler, sonuc_sablonu,
)

NODE = shutil.which("node")
ORNEKLER = KOK / "testler" / "nar" / "tip_ornekleri.nar"


def nar_ciktilari(betik: Path, cagrilar: list[str]) -> dict:
    """Nar tarafındaki sınama işlevlerini çalıştırır (tek Node çağrısı)."""
    satirlar = "\n".join(
        f"  cikti[{ad!r}] = Nar[{ad!r}]();" for ad in cagrilar
    )
    surucu = (
        f"require({str(betik).replace(chr(92), '/')!r});\n"
        "const cikti = {};\n"
        f"{satirlar}\n"
        "process.stdout.write(JSON.stringify(cikti));\n"
    )
    sonuc = subprocess.run(
        [NODE, "-e", surucu], capture_output=True, text=True,
        encoding="utf-8", timeout=300,
    )
    if sonuc.returncode != 0:
        raise AssertionError("Nar tip sistemi çalışmadı:\n" + sonuc.stderr.strip())
    return json.loads(sonuc.stdout)


@unittest.skipIf(NODE is None, "node bulunamadı")
class NarTiplerTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        kod = compile_file(ORNEKLER, kutuphane=True).to_js()
        betik = Path(cls._tmp.name) / "nar-tipler.js"
        betik.write_text(kod, encoding="utf-8")
        cls.cikti = nar_ciktilari(betik, [
            "tipMetinleri", "atanabilirlikTablosu", "ortakTipTablosu",
            "birlestirmeTablosu", "alanMetinleri", "tipDegiskeniMetinleri",
        ])
        cls.tipler = ornek_tipler()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_listeler_ortusuyor(self):
        """İki taraf aynı tipleri aynı sırayla kurmalı.

        Bu geçmezse diğer testler yanlış çiftleri karşılaştırır.
        """
        alinan = self.cikti["tipMetinleri"]
        beklenen = [str(t) for t in self.tipler]
        self.assertEqual(len(alinan), len(beklenen), "liste uzunlukları farklı")
        for i, (a, b) in enumerate(zip(alinan, beklenen)):
            with self.subTest(sira=i):
                self.assertEqual(a, b)

    def test_atanabilirlik(self):
        alinan = self.cikti["atanabilirlikTablosu"]
        for i, hedef in enumerate(self.tipler):
            beklenen = "".join(
                "1" if T.assignable(hedef, kaynak) else "0"
                for kaynak in self.tipler
            )
            if alinan[i] == beklenen:
                continue
            # Hangi çiftte ayrıştığını göster
            for j, (a, b) in enumerate(zip(alinan[i], beklenen)):
                if a != b:
                    self.fail(
                        f"atanabilir({hedef}, {self.tipler[j]}): "
                        f"Nar={a == '1'} Python={b == '1'}"
                    )

    def test_ortak_tip(self):
        alinan = self.cikti["ortakTipTablosu"]
        for i, a in enumerate(self.tipler):
            hucreler = alinan[i].split("|")
            for j, b in enumerate(self.tipler):
                ortak = T.common_type(a, b)
                beklenen = "-" if ortak is None else str(ortak)
                with self.subTest(a=str(a), b=str(b)):
                    self.assertEqual(hucreler[j], beklenen)

    def test_birlestirme(self):
        alinan = self.cikti["birlestirmeTablosu"]
        for i, sablon in enumerate(self.tipler):
            hucreler = alinan[i].split("|")
            for j, somut in enumerate(self.tipler):
                esleme: dict = {}
                oldu = T.birlestir(sablon, somut, esleme)
                beklenen = "-" if not oldu else ",".join(
                    f"{ad}={tip}" for ad, tip in esleme.items()
                )
                with self.subTest(sablon=str(sablon), somut=str(somut)):
                    self.assertEqual(hucreler[j], beklenen)

    def test_tembel_alan_cozumu(self):
        """Generic bir tip uygulandığında alanlar doğru yerine konmalı."""
        alinan = self.cikti["alanMetinleri"]
        kutu = kutu_sablonu()
        sonuc = sonuc_sablonu()

        beklenen = []
        nokta = ornek_struct()
        beklenen.append(",".join(f"{ad}:{t}" for ad, t in nokta.fields.items()))

        for arg in (T.INT, T.STRING, T.ListT(T.INT)):
            u = T.uygula_struct(kutu, (arg,))
            beklenen.append(",".join(f"{ad}:{t}" for ad, t in u.fields.items()))
            beklenen.append(",".join(f"{ad}:{t}" for ad, t in u.methods.items()))

        for args in ((T.INT, T.STRING), (T.STRING, T.INT)):
            e = T.uygula_enum(sonuc, args)
            beklenen.append(";".join(
                f"{ad}({','.join(str(t) for t in yuk)})"
                for ad, yuk in e.variants.items()
            ))

        self.assertEqual(alinan, beklenen)

    def test_tip_degiskenleri(self):
        alinan = self.cikti["tipDegiskeniMetinleri"]
        for i, t in enumerate(self.tipler):
            # Python `set` döndürür; sıra garantisi yok, karşılaştırma küme
            # olarak yapılır.
            nar_kumesi = set(x for x in alinan[i].split(",") if x)
            with self.subTest(tip=str(t)):
                self.assertEqual(nar_kumesi, T.tipdegiskenleri(t))


if __name__ == "__main__":
    unittest.main()
