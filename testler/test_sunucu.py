"""Sunucu tarafı: HTTP sunucusu, yönlendirme, form ve çerez ayrıştırma.

Sunucu gerçekten ayağa kaldırılır ve isteklerle sınanır — bir HTTP
sunucusunun doğruluğu ancak istek atarak anlaşılır.

Türkçe karakterler her katmanda ayrı ayrı doğrulanır: JSON gövdesi, URL
kodlu form gövdesi ve sorgu dizesi. Çok baytlı UTF-8'i yanlış çözen bir
sunucu sessizce bozuk veri kaydeder.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.driver import compile_file  # noqa: E402

NODE = shutil.which("node")


def bos_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def istek(url: str, yontem: str = "GET", govde: bytes | None = None,
          basliklar: dict | None = None) -> tuple[int, str, dict]:
    """Tek bir HTTP isteği; (durum, gövde, başlıklar) döndürür."""
    req = urllib.request.Request(url, data=govde, method=yontem)
    for ad, deger in (basliklar or {}).items():
        req.add_header(ad, deger)
    try:
        with urllib.request.urlopen(req, timeout=10) as y:
            return y.status, y.read().decode("utf-8"), dict(y.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


class Sunucu:
    """Nar kaynağını derleyip sunucu olarak çalıştırır; `with` ile kapanır."""

    def __init__(self, kaynak: str, klasor: Path | None = None):
        self.kaynak = kaynak
        self.klasor = klasor
        self.port = bos_port()

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        kok = Path(self._tmp.name)
        nar = kok / "sunucu.nar"
        # `import` yolları projeye göre çözülsün diye mutlak yazılır.
        nar.write_text(
            self.kaynak.replace("@ARACLAR@", (KOK / "araclar").as_posix()),
            encoding="utf-8",
        )
        betik = kok / "sunucu.js"
        betik.write_text(compile_file(nar).to_js(), encoding="utf-8")

        calisma = str(self.klasor) if self.klasor else str(kok)
        self.surec = subprocess.Popen(
            [NODE, str(betik)], cwd=calisma,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**__import__("os").environ, "PORT": str(self.port)},
        )
        self._bekle()
        return self

    def _bekle(self, saniye: float = 10.0):
        son = time.time() + saniye
        while time.time() < son:
            if self.surec.poll() is not None:
                cikti = self.surec.stderr.read().decode("utf-8", "replace")
                raise AssertionError(f"sunucu başlamadı:\n{cikti}")
            with socket.socket() as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", self.port)) == 0:
                    return
            time.sleep(0.1)
        raise AssertionError("sunucu zamanında ayağa kalkmadı")

    def url(self, yol: str) -> str:
        return f"http://127.0.0.1:{self.port}{yol}"

    def __exit__(self, *_):
        self.surec.kill()
        self.surec.wait(timeout=5)
        self._tmp.cleanup()


YONLENDIRME = '''import "@ARACLAR@/web.nar"

fn main() {
  let u = uygulama()
  u.get("/", |i| yanitHtml("<h1>kök</h1>"))
  u.get("/kisi/:ad", |i| yanitMetin("selam " + (i.parametre("ad") ?? "")))
  u.get("/derin/:a/:b", |i| yanitMetin((i.parametre("a") ?? "") + "-" +
    (i.parametre("b") ?? "")))
  u.post("/yanki", |i| yanitMetin(i.govde()))
  u.post("/form", |i| yanitMetin((i.alan("ad") ?? "yok") + "|" +
    (i.alan("not") ?? "yok")))
  u.get("/sorgu", |i| yanitMetin(i.sorgu("q") ?? "yok"))
  u.sil("/kayit/:no", |i| yanitJson("{\\"silindi\\":" + (i.parametre("no") ?? "0") + "}"))
  u.get("/cerezoku", |i| yanitMetin(i.cerez("oturum") ?? "yok"))
  u.get("/cerezyaz", |i| cerezYaz(yanitMetin("tamam"), "oturum", "değer çğ", 60))
  u.get("/git", |i| yonlendir("/"))
  u.get("/basliklar", |i| yanitMetin(i.baslik("x-deneme") ?? "yok"))
  u.dinle(int(ortam("PORT") ?? "8080") ?? 8080)
}
'''


@unittest.skipIf(NODE is None, "node bulunamadı")
class YonlendirmeTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = Sunucu(YONLENDIRME).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.__exit__()

    def test_kok_yolu(self):
        durum, govde, basliklar = istek(self.sunucu.url("/"))
        self.assertEqual(durum, 200)
        self.assertEqual(govde, "<h1>kök</h1>")
        self.assertIn("text/html", basliklar["Content-Type"])

    def test_yol_parametresi(self):
        _, govde, _ = istek(self.sunucu.url("/kisi/Ayse"))
        self.assertEqual(govde, "selam Ayse")

    def test_yol_parametresinde_turkce(self):
        yol = "/kisi/" + urllib.parse.quote("Ayşe Öz")
        _, govde, _ = istek(self.sunucu.url(yol))
        self.assertEqual(govde, "selam Ayşe Öz")

    def test_iki_parametre(self):
        _, govde, _ = istek(self.sunucu.url("/derin/bir/iki"))
        self.assertEqual(govde, "bir-iki")

    def test_govde_okunuyor(self):
        _, govde, _ = istek(self.sunucu.url("/yanki"), "POST",
                            "merhaba şğüöç".encode("utf-8"))
        self.assertEqual(govde, "merhaba şğüöç")

    def test_form_alanlari(self):
        veri = urllib.parse.urlencode({"ad": "Ayşe Öz", "not": "çğış"})
        _, govde, _ = istek(
            self.sunucu.url("/form"), "POST", veri.encode("utf-8"),
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(govde, "Ayşe Öz|çğış")

    def test_sorgu_dizesi(self):
        yol = "/sorgu?q=" + urllib.parse.quote("şğüöç İ")
        _, govde, _ = istek(self.sunucu.url(yol))
        self.assertEqual(govde, "şğüöç İ")

    def test_silme_yontemi(self):
        durum, govde, _ = istek(self.sunucu.url("/kayit/7"), "DELETE")
        self.assertEqual(durum, 200)
        self.assertEqual(json.loads(govde), {"silindi": 7})

    def test_yontem_uyusmazligi_405(self):
        durum, _, _ = istek(self.sunucu.url("/"), "POST", b"")
        self.assertEqual(durum, 405)

    def test_bulunamayan_yol_404(self):
        durum, govde, _ = istek(self.sunucu.url("/boyle-bir-yol-yok"))
        self.assertEqual(durum, 404)
        self.assertIn("bulunamadı", govde)

    def test_yonlendirme(self):
        req = urllib.request.Request(self.sunucu.url("/git"))

        class Tutucu(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None  # yönlendirmeyi izleme

        acici = urllib.request.build_opener(Tutucu)
        try:
            with acici.open(req, timeout=10) as y:
                self.assertEqual(y.status, 302)
                self.assertEqual(y.headers["Location"], "/")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 302)
            self.assertEqual(e.headers["Location"], "/")

    def test_istek_basligi_okunuyor(self):
        _, govde, _ = istek(self.sunucu.url("/basliklar"), "GET", None,
                            {"X-Deneme": "merhaba"})
        self.assertEqual(govde, "merhaba")

    def test_cerez_yazma_ve_okuma(self):
        _, _, basliklar = istek(self.sunucu.url("/cerezyaz"))
        kural = basliklar["Set-Cookie"]
        self.assertIn("HttpOnly", kural)
        self.assertIn("Max-Age=60", kural)
        self.assertIn("SameSite=Lax", kural)

        # Yazılan çerezi geri gönder; sunucu aynı değeri okumalı.
        deger = kural.split(";")[0].split("=", 1)[1]
        _, govde, _ = istek(self.sunucu.url("/cerezoku"), "GET", None,
                            {"Cookie": f"oturum={deger}"})
        self.assertEqual(govde, "değer çğ")


STATIK = '''import "@ARACLAR@/web.nar"

fn main() {
  let u = uygulama()
  u.klasor("/statik", "www")
  u.dinle(int(ortam("PORT") ?? "8080") ?? 8080)
}
'''


@unittest.skipIf(NODE is None, "node bulunamadı")
class StatikDosyaTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        kok = Path(cls._tmp.name)
        (kok / "www").mkdir()
        (kok / "www" / "index.html").write_text("<p>ana</p>", encoding="utf-8")
        (kok / "www" / "stil.css").write_text("body{color:red}", encoding="utf-8")
        (kok / "www" / "alt").mkdir()
        (kok / "www" / "alt" / "index.html").write_text("<p>alt</p>", encoding="utf-8")
        (kok / "gizli.txt").write_text("görünmemeli", encoding="utf-8")
        cls.sunucu = Sunucu(STATIK, klasor=kok).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.__exit__()
        cls._tmp.cleanup()

    def test_dosya_sunuluyor(self):
        durum, govde, _ = istek(self.sunucu.url("/statik/index.html"))
        self.assertEqual(durum, 200)
        self.assertEqual(govde, "<p>ana</p>")

    def test_icerik_tipi_dogru(self):
        _, _, basliklar = istek(self.sunucu.url("/statik/stil.css"))
        self.assertIn("text/css", basliklar["Content-Type"])

    def test_klasorde_index_bulunuyor(self):
        _, govde, _ = istek(self.sunucu.url("/statik/alt"))
        self.assertEqual(govde, "<p>alt</p>")

    def test_olmayan_dosya_404(self):
        durum, _, _ = istek(self.sunucu.url("/statik/yok.txt"))
        self.assertEqual(durum, 404)

    def test_klasor_disina_cikilamiyor(self):
        """`..` ile kök klasörün dışına erişim reddedilmeli.

        Bu engel olmadan sunucu diskteki her dosyayı servis eder.
        """
        for kotu in ("/statik/../gizli.txt", "/statik/..%2Fgizli.txt"):
            with self.subTest(yol=kotu):
                durum, _, _ = istek(self.sunucu.url(kotu))
                self.assertNotEqual(durum, 200, f"{kotu} sunuldu!")


class DerlemeHiziTesti(unittest.TestCase):
    """Uzun metin birleştirme zinciri hızlı derlenmeli.

    Metin birleştirmede alt ağaç iki kez üretiliyordu; maliyet zincir
    uzunluğunda üstel büyüyordu. 40 parçalı bir metin dakikalarca
    derleniyordu — bu test o hatanın geri gelmesini engeller.
    """

    def test_uzun_birlestirme_zinciri(self):
        from narc.backends import js as js_backend
        from narc.checker import Checker
        from narc.parser import parse

        parcalar = " + ".join(f'"parca{i}"' for i in range(60))
        kaynak = f"let K = {parcalar}\n\nfn main() {{ print(K.len()) }}\n"

        basla = time.time()
        module = parse(kaynak, "t.nar")
        checker = Checker(module, kaynak)
        checker.check()
        js_backend.generate(module, checker)
        gecen = time.time() - basla

        self.assertLess(gecen, 5.0, f"60 parçalı zincir {gecen:.1f} sn sürdü")


if __name__ == "__main__":
    unittest.main()
