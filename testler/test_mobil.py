"""`nar build --target mobil` paketleme testleri.

Android/iOS derlemesi platform araçları ister (Android Studio, Xcode); bu
makinede yoklar. Burada doğrulanan şey, üretilen Capacitor projesinin
**eksiksiz ve geçerli** olduğudur: dosyalar yerinde mi, JSON'lar geçerli mi,
uygulama kimliği platformların kuralına uyuyor mu, sayfa telefon için
hazırlanmış mı.

Cihazda çalıştırma denenmemiştir; BENIOKU.md kullanıcıya hangi komutları
çalıştıracağını söyler.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.driver import compile_file  # noqa: E402
from narc.mobil_paket import paketle, uygulama_kimligi  # noqa: E402

# Android paket adı / iOS bundle id kuralı: noktayla ayrılmış parçalar,
# her parça harfle başlar, harf ve rakam içerir.
KIMLIK_KURALI = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*(\.[a-zA-Z][a-zA-Z0-9]*)+$")


class MobilPaketTesti(unittest.TestCase):
    def paketle_ornek(self, tmp: str) -> Path:
        derleme = compile_file(KOK / "ornekler" / "sayac_web.nar")
        hedef = Path(tmp) / "uygulama"
        paketle(derleme.to_js(), hedef, "Sayaç", "sayac_web.nar")
        return hedef

    def test_proje_dosyalari_olusuyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            for ad in ("www/index.html", "capacitor.config.json",
                       "package.json", ".gitignore", "BENIOKU.md"):
                with self.subTest(dosya=ad):
                    self.assertTrue((hedef / ad).exists(), f"{ad} üretilmedi")

    def test_capacitor_yapilandirmasi_gecerli(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            cfg = json.loads((hedef / "capacitor.config.json").read_text(encoding="utf-8"))

            # webDir gerçekten var olmalı; yoksa `npx cap sync` boş uygulama üretir.
            self.assertEqual(cfg["webDir"], "www")
            self.assertTrue((hedef / cfg["webDir"] / "index.html").exists())

            self.assertEqual(cfg["appName"], "Sayaç")
            self.assertRegex(cfg["appId"], KIMLIK_KURALI)

    def test_package_json_gecerli(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            paket = json.loads((hedef / "package.json").read_text(encoding="utf-8"))

            # npm paket adı: küçük harf, boşluksuz.
            self.assertEqual(paket["name"], paket["name"].lower())
            self.assertNotIn(" ", paket["name"])

            for bagimlilik in ("@capacitor/core", "@capacitor/android", "@capacitor/ios"):
                with self.subTest(bagimlilik=bagimlilik):
                    self.assertIn(bagimlilik, paket["dependencies"])
            self.assertIn("@capacitor/cli", paket["devDependencies"])

    def test_kimlik_kurali(self):
        # Türkçe karakterler ve boşluklar kimlikten temizlenmeli.
        for ad, beklenen in (
            ("sayac_web", "com.nar.sayacweb"),
            ("Görev Listesi", "com.nar.grevlistesi"),
            ("123", "com.nar.uygulama123"),
            ("", "com.nar.uygulama"),
        ):
            with self.subTest(ad=ad):
                kimlik = uygulama_kimligi(ad)
                self.assertEqual(kimlik, beklenen)
                self.assertRegex(kimlik, KIMLIK_KURALI)

    def test_sayfa_telefon_icin_hazirlanmis(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            html = (hedef / "www" / "index.html").read_text(encoding="utf-8")

            self.assertIn("<!doctype html>", html)
            self.assertIn('lang="tr"', html)
            self.assertIn('id="uygulama"', html)
            self.assertIn("$bootstrap(main);", html)

            # Çentikli ekranlarda içeriğin altta kalmaması için.
            self.assertIn("viewport-fit=cover", html)
            self.assertIn("safe-area-inset", html)
            # Parmakla basılabilir dokunma hedefi (WCAG 2.5.5 asgari 44px).
            self.assertIn("min-height: 44px", html)
            # Çift dokunmayla yakınlaştırma uygulamada istenmez.
            self.assertIn("maximum-scale=1", html)

    def test_benioku_derleme_komutlarini_veriyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            metin = (hedef / "BENIOKU.md").read_text(encoding="utf-8")
            for komut in ("npm install", "npx cap add android",
                          "npx cap add ios", "npx cap sync"):
                with self.subTest(komut=komut):
                    self.assertIn(komut, metin)

    def test_gitignore_uretilen_platform_klasorlerini_disliyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            yoksay = (hedef / ".gitignore").read_text(encoding="utf-8")
            for satir in ("node_modules/", "android/", "ios/"):
                self.assertIn(satir, yoksay)


if __name__ == "__main__":
    unittest.main()
