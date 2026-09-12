"""Arayüz kütüphanesi (`araclar/arayuz.nar`) uçtan uca testleri.

Kütüphane sayfaya çizim yaptığı için Node'da sahte bir DOM kurulur
(`testler/sahte_dom.js`). Böylece "durum değişince ekran yenilenir" iddiası
tarayıcı açmadan doğrulanabilir: düğmeye tıklanır, ekranın metni okunur.
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

from narc.driver import compile_file  # noqa: E402

NODE = shutil.which("node")
SAHTE_DOM = Path(__file__).resolve().parent / "sahte_dom.js"
ARAYUZ = KOK / "araclar" / "arayuz.nar"


def sahnede_calistir(nar_kaynagi: str, senaryo: str) -> list:
    """Nar programını sahte DOM'da çalıştırır; senaryonun bastığı JSON'u döndürür.

    `senaryo`, program `main()`'i çalıştıktan sonra yürütülen JavaScript'tir.
    `$dom` yardımcılarıyla tıklar, yazar ve `$yaz(...)` ile sonuç bildirir.
    """
    with tempfile.TemporaryDirectory() as tmp:
        kaynak = Path(tmp) / "program.nar"
        # Kütüphaneye göreli import'un çözülebilmesi için mutlak yol yazılır.
        kaynak.write_text(
            nar_kaynagi.replace("@ARAYUZ@", ARAYUZ.as_posix()), encoding="utf-8",
        )
        kod = compile_file(kaynak).to_js()

        betik = Path(tmp) / "sahne.js"
        betik.write_text(
            f'require({json.dumps(str(SAHTE_DOM))});\n'
            '$dom.kokKur("uygulama");\n'
            'const $kayit = [];\n'
            'globalThis.$yaz = (x) => $kayit.push(x);\n'
            '\n'
            f'{kod}\n'
            '\n'
            f'{senaryo}\n'
            'console.log("###" + JSON.stringify($kayit));\n',
            encoding="utf-8",
        )

        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
        )

    if sonuc.returncode != 0:
        raise AssertionError(f"node hata verdi:\n{sonuc.stderr}")
    for satir in sonuc.stdout.splitlines():
        if satir.startswith("###"):
            return json.loads(satir[3:])
    raise AssertionError(f"senaryo sonuç bildirmedi:\n{sonuc.stdout}\n{sonuc.stderr}")


SAYAC = '''import "@ARAYUZ@"

var uygulama: Uygulama<Int>? = none

fn ciz(n: Int) -> Gorunum = Sutun([
  Baslik("Sayaç"),
  Metin("değer: ${n}"),
  Dugme("Artır", || {
    if uygulama != none {
      uygulama!.degistir(uygulama!.durum + 1)
    }
  })
])

fn main() {
  uygulama = uygulamaBaslat("#uygulama", 0, ciz)
}
'''


SAYACLI_HAREKET = '''import "@ARAYUZ@"

var uygulama: Uygulama<Int>? = none

fn ciz(n: Int) -> Gorunum = Sutun([
  Hareketli(YUKSEL, Metin("değer: ${n}")),
  Dugme("Artır", || {
    if uygulama != none {
      uygulama!.degistir(uygulama!.durum + 1)
    }
  }),
  Dugme("Sıfırla", || {
    hareketDefteriniSil()
    if uygulama != none {
      uygulama!.degistir(0)
    }
  })
])

fn main() {
  uygulama = uygulamaBaslat("#uygulama", 0, ciz)
}
'''

@unittest.skipIf(NODE is None, "node bulunamadı")
class GorunumTesti(unittest.TestCase):
    def test_ilk_cizim(self):
        kayit = sahnede_calistir(SAYAC, '$yaz($dom.satirlar($dom.govde));')
        self.assertEqual(kayit[0], ["Sayaç", "değer: 0", "Artır"])

    def test_dugme_durumu_degistirir_ve_ekran_yenilenir(self):
        kayit = sahnede_calistir(SAYAC, '''
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$yaz($dom.satirlar($dom.govde));
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], ["Sayaç", "değer: 1", "Artır"])
        self.assertEqual(kayit[1], ["Sayaç", "değer: 3", "Artır"])

    def test_giris_alani_durumu_besler(self):
        src = '''import "@ARAYUZ@"

var uygulama: Uygulama<String>? = none

fn yazildi(y: String) {
  if uygulama != none {
    uygulama!.degistir(y)
  }
}

fn ciz(ad: String) -> Gorunum = Sutun([
  Giris("adın?", ad, yazildi),
  Metin("merhaba ${ad}")
])

fn main() {
  uygulama = uygulamaBaslat("#uygulama", "", ciz)
}
'''
        kayit = sahnede_calistir(src, '''
$dom.yaz($dom.giris($dom.govde), "Nar");
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], ["<giris:Nar|adın?>", "merhaba Nar"])

    def test_ic_ice_yerlesim(self):
        src = '''import "@ARAYUZ@"

fn main() {
  uygulamaBaslat("#uygulama", 0, |_| Kutu([
    Baslik("Kart"),
    Cizgi,
    Satir([Metin("sol"), Metin("sağ")]),
    Bosluk(8),
    Sutun([Metin("bir"), Metin("iki")])
  ]))
}
'''
        kayit = sahnede_calistir(src, '$yaz($dom.satirlar($dom.govde));')
        self.assertEqual(kayit[0], ["Kart", "sol", "sağ", "bir", "iki"])

    def test_yapilacaklar_ornegi_calisir(self):
        """Depodaki gerçek örnek: ekle, işaretle, bitenleri temizle."""
        kaynak = (KOK / "ornekler" / "yapilacaklar_uygulamasi.nar").read_text(
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory() as tmp:
            # Örnek dosyayı yerinde derleyip senaryoyu üstüne ekliyoruz.
            kod = compile_file(KOK / "ornekler" / "yapilacaklar_uygulamasi.nar").to_js()
            betik = Path(tmp) / "sahne.js"
            betik.write_text(
                f'require({json.dumps(str(SAHTE_DOM))});\n'
                '$dom.kokKur("uygulama");\n'
                'const $kayit = [];\n'
                'globalThis.$yaz = (x) => $kayit.push(x);\n'
                f'{kod}\n'
                '''
$yaz($dom.satirlar($dom.govde));
$dom.yaz($dom.giris($dom.govde), "Süt al");
$dom.tikla($dom.dugme($dom.govde, "Ekle"));
$yaz($dom.satirlar($dom.govde));
$dom.tikla($dom.govde.querySelectorAll("button")[0]);
$dom.tikla($dom.dugme($dom.govde, "Bitenleri temizle"));
$yaz($dom.satirlar($dom.govde));
console.log("###" + JSON.stringify($kayit));
''',
                encoding="utf-8",
            )
            sonuc = subprocess.run(
                [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
            )

        self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
        kayit = next(
            json.loads(s[3:]) for s in sonuc.stdout.splitlines() if s.startswith("###")
        )

        # 1) açılış: iki görev, biri bitmiş
        self.assertEqual(kayit[0][:2], ["Yapılacaklar", "1 / 2 kaldı"])
        self.assertIn("Nar ile bir uygulama yaz", kayit[0])

        # 2) ekleme: yeni görev listeye girdi, sayaç ve giriş tazelendi
        self.assertEqual(kayit[1][1], "2 / 3 kaldı")
        self.assertIn("Süt al", kayit[1])
        self.assertIn("<giris:|yeni görev...>", kayit[1])

        # 3) ilk kutucuk işaretlenip bitenler silindi: iki görev kaldı
        self.assertEqual(kayit[2][1], "2 / 2 kaldı")
        self.assertNotIn("Nar ile bir uygulama yaz", kayit[2])

        # örnek dosyasının kendisi hâlâ arayüz kütüphanesini kullanıyor olmalı
        self.assertIn("arayuz.nar", kaynak)

    def test_yenilemeden_sonra_odak_ayni_alanda_kalir(self):
        """Yazarken ağaç yeniden çizilir; imleç yerinde kalmalı.

        Bu davranış olmadan alan her tuştan sonra odağı kaybeder ve
        kullanıcı yalnızca ilk harfi girebilir.
        """
        src = '''import "@ARAYUZ@"

var uygulama: Uygulama<String>? = none

fn ciz(ad: String) -> Gorunum = Sutun([
  Giris("adın?", ad, |y| {
    if uygulama != none {
      uygulama!.degistir(y)
    }
  }),
  Metin("merhaba ${ad}")
])

fn main() {
  uygulama = uygulamaBaslat("#uygulama", "", ciz)
}
'''
        kayit = sahnede_calistir(src, """
// Harf harf yazmak gerçek kullanımı taklit eder: her tuş bir yenileme
// tetikler, yani odak dört kez kaybolup dört kez geri gelmelidir.
for (const harf of ["A", "Ay", "Ayş", "Ayşe"]) {
  const alan = $dom.giris($dom.govde);
  $dom.yaz(alan, harf);
}
$yaz($dom.satirlar($dom.govde));
$yaz($dom.odak());
""")
        self.assertEqual(kayit[0], ["<giris:Ayşe|adın?>", "merhaba Ayşe"])
        # Odak hâlâ giriş alanında ve imleç metnin sonunda.
        self.assertIsNotNone(kayit[1], "yenilemeden sonra odak kayboldu")
        self.assertEqual(kayit[1]["deger"], "Ayşe")
        self.assertEqual(kayit[1]["basi"], 4)
        self.assertEqual(kayit[1]["sonu"], 4)

    def test_hareket_yalniz_ilk_cizimde_oynar(self):
        """Durum değişiminde giriş hareketi tekrarlanmamalı.

        Her durum değişimi ağacı baştan çizer. Hareket her çizimde
        oynasaydı, bir giriş alanına yazan kişi her tuşta bütün ekranın
        yeniden süzülmesini izlerdi.
        """
        kayit = sahnede_calistir(SAYACLI_HAREKET, """
var say = function () {
  return $dom.sinifliOgeler($dom.govde, 'nar-h').length;
};
$yaz(say());
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$yaz(say());
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$yaz(say());
""")
        self.assertEqual(kayit[0], 1, "ilk çizimde hareket verilmeli")
        self.assertEqual(kayit[1], 0, "yeniden çizimde hareket tekrarlanmamalı")
        self.assertEqual(kayit[2], 0, "sonraki çizimlerde de tekrarlanmamalı")

    def test_hareket_defteri_silinince_yeniden_oynar(self):
        """Sekme ya da sayfa değişiminde hareket yeniden oynayabilmeli."""
        kayit = sahnede_calistir(SAYACLI_HAREKET, """
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$yaz($dom.sinifliOgeler($dom.govde, 'nar-h').length);
$dom.tikla($dom.dugme($dom.govde, "Sıfırla"));
$yaz($dom.sinifliOgeler($dom.govde, 'nar-h').length);
""")
        self.assertEqual(kayit[0], 0)
        self.assertEqual(kayit[1], 1, "defter silinince hareket geri gelmeli")

    def test_sirali_giris_gecikmeyi_artirir(self):
        """Sıralı girişte her öğe bir öncekinden sonra girer."""
        src = '''import "@ARAYUZ@"

fn ciz(n: Int) -> Gorunum = Sirali([
  Metin("bir"),
  Metin("iki"),
  Metin("üç")
])

fn main() {
  uygulamaBaslat("#uygulama", 0, ciz)
}
'''
        kayit = sahnede_calistir(src, """
$yaz($dom.sinifliOgeler($dom.govde, 'nar-h')
  .map(function (e) { return e.stiller['animation-delay'] || '0'; }));
""")
        # İlk öğe beklemez; sonrakiler kademenin adım süresinden hesaplanır.
        self.assertEqual(kayit[0], [
            "0",
            "calc(var(--nar-h-adim) * 1)",
            "calc(var(--nar-h-adim) * 2)",
        ])

    def test_hareket_stili_bir_kez_kurulur(self):
        """Stil <head> içine bir kez girer; her çizimde çoğalmamalı."""
        kayit = sahnede_calistir(SAYACLI_HAREKET, """
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$dom.tikla($dom.dugme($dom.govde, "Artır"));
$yaz(document.querySelectorAll('style').length);
""")
        # Biri arayüz kütüphanesinin stili, biri hareket katmanının.
        self.assertEqual(kayit[0], 2)

    def test_mobil_gorunum_ekrana_gore_secilir(self):
        """`.mobil()` dar ekranda yerine geçer; kırılma noktası değişince
        uygulama kendini yeniden çizer."""
        src = '''import "@ARAYUZ@"

fn ciz(n: Int) -> Gorunum = Sutun([
  Metin("geniş").mobil(Metin("dar")),
  Rozet("g", TON_BILGI).mobildeGizle(),
  Rozet("d", TON_BILGI).masaustundeGizle(),
  Satir([Metin("a"), Metin("b")]).mobildeSutun()
])

fn main() {
  uygulamaBaslat("#uygulama", 0, ciz)
}
'''
        kayit = sahnede_calistir(src, """
var metinler = function () {
  return $dom.satirlar($dom.govde).filter(function (s) {
    return s === 'geniş' || s === 'dar';
  });
};
$yaz(metinler());
$dom.genislik(390);
$yaz(metinler());
$dom.genislik(1200);
$yaz(metinler());
$yaz($dom.sinifliOgeler($dom.govde, 'nar-mobilde-gizli').length);
$yaz($dom.sinifliOgeler($dom.govde, 'nar-masaustunde-gizli').length);
$yaz($dom.sinifliOgeler($dom.govde, 'nar-mobilde-sutun').length);
""")
        self.assertEqual(kayit[0], ["geniş"], "açılışta geniş ekran")
        self.assertEqual(kayit[1], ["dar"], "daralınca yeniden çizilmeli")
        self.assertEqual(kayit[2], ["geniş"], "genişleyince geri dönmeli")
        # Gizleme ve sütuna dönme saf CSS sınıfıdır; her ekranda ağaçtadır.
        self.assertEqual(kayit[3:], [1, 1, 1])

    def test_uyum_metotlari_ust_uste_sarmaz(self):
        """Zincirlenen metotlar tek katman üretir: sınıflar aynı öğede."""
        src = '''import "@ARAYUZ@"

fn ciz(n: Int) -> Gorunum =
  Satir([Metin("a")]).mobildeSutun().mobildeGizle()

fn main() {
  uygulamaBaslat("#uygulama", 0, ciz)
}
'''
        kayit = sahnede_calistir(src, """
var e = $dom.sinifliOgeler($dom.govde, 'nar-mobilde-sutun')[0];
$yaz($dom.siniflar(e).sort());
""")
        self.assertEqual(
            kayit[0], ["nar-mobilde-gizli", "nar-mobilde-sutun", "nar-satir"])


TAKVIM = '''import "@ARAYUZ@"

var uygulama: Uygulama<TakvimDurumu>? = none

fn ciz(d: TakvimDurumu) -> Gorunum = Sutun([
  Takvim(d, |yeni| {
    if uygulama != none {
      uygulama!.degistir(yeni)
    }
  })
])

fn main() {
  // Sabit bir ay: test bugünün tarihine göre değişmesin. `enErken: 0`
  // geçmiş sınırını kaldırır, yoksa 2026 Eylül bir gün kapanabilirdi.
  uygulama = uygulamaBaslat("#uygulama", TakvimDurumu {
    yil: 2026, ay: 9, aySayisi: 1
  }, ciz)
}
'''


def ozet(kok_degiskeni: str = "$dom.govde") -> str:
    """Takvimin alt satırındaki iki metni okuyan senaryo parçası."""
    return (
        f'$yaz([$dom.sinifliOgeler({kok_degiskeni}, "nar-takvim-aralik")'
        '.map(o => o.textContent)[0] || "",'
        f' $dom.sinifliOgeler({kok_degiskeni}, "nar-takvim-gece")'
        '.map(o => o.textContent)[0] || ""]);'
    )


@unittest.skipIf(NODE is None, "node bulunamadı")
class TakvimTesti(unittest.TestCase):
    def test_once_giris_sonra_cikis_secilir(self):
        kayit = sahnede_calistir(TAKVIM, f'''
{ozet()}
$dom.tikla($dom.dugme($dom.govde, "10"));
{ozet()}
$dom.tikla($dom.dugme($dom.govde, "14"));
{ozet()}
$yaz($dom.sinifliOgeler($dom.govde, "nar-gun-arada").length);
''')
        self.assertEqual(kayit[0], ["Tarih seç", "önce giriş, sonra çıkış"])
        self.assertEqual(kayit[1], ["10 Eyl — …", "çıkış gününü seç"])
        self.assertEqual(kayit[2], ["10 Eyl — 14 Eyl", "4 gece"])
        # 11, 12, 13 aradaki günler
        self.assertEqual(kayit[3], 3)

    def test_girisin_oncesine_tiklamak_secimi_tasir(self):
        """Kullanıcı yanlış gün seçtiyse hata vermek yerine seçim taşınır."""
        kayit = sahnede_calistir(TAKVIM, f'''
$dom.tikla($dom.dugme($dom.govde, "20"));
$dom.tikla($dom.dugme($dom.govde, "12"));
{ozet()}
$dom.tikla($dom.dugme($dom.govde, "15"));
{ozet()}
''')
        self.assertEqual(kayit[0], ["12 Eyl — …", "çıkış gününü seç"])
        self.assertEqual(kayit[1], ["12 Eyl — 15 Eyl", "3 gece"])

    def test_aralik_tamamken_yeni_tiklama_bastan_baslatir(self):
        kayit = sahnede_calistir(TAKVIM, f'''
$dom.tikla($dom.dugme($dom.govde, "10"));
$dom.tikla($dom.dugme($dom.govde, "14"));
$dom.tikla($dom.dugme($dom.govde, "22"));
{ozet()}
$yaz($dom.sinifliOgeler($dom.govde, "nar-gun-arada").length);
''')
        self.assertEqual(kayit[0], ["22 Eyl — …", "çıkış gününü seç"])
        self.assertEqual(kayit[1], 0)

    def test_temizle_secimi_siler(self):
        kayit = sahnede_calistir(TAKVIM, f'''
$dom.tikla($dom.dugme($dom.govde, "10"));
$dom.tikla($dom.dugme($dom.govde, "14"));
$dom.tikla($dom.dugme($dom.govde, "Temizle"));
{ozet()}
''')
        self.assertEqual(kayit[0], ["Tarih seç", "önce giriş, sonra çıkış"])

    def test_ay_gecisi(self):
        """İleri oku sonraki aya geçer; gün sayısı ve ad değişir."""
        kayit = sahnede_calistir(TAKVIM, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-ay-adi").map(o => o.textContent));
const ileri = $dom.govde.querySelectorAll("button")
  .filter(d => d.ozellikler["aria-label"] === "sonraki ay");
$dom.tikla(ileri[0]);
$yaz($dom.sinifliOgeler($dom.govde, "nar-ay-adi").map(o => o.textContent));
$yaz($dom.sinifliOgeler($dom.govde, "nar-gun").filter(
  o => !o.siniflar.has("nar-gun-bos")).length);
''')
        self.assertEqual(kayit[0], ["Eylül 2026"])
        self.assertEqual(kayit[1], ["Ekim 2026"])
        self.assertEqual(kayit[2], 31)

if __name__ == "__main__":
    unittest.main()
