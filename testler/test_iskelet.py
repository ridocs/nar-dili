"""Sayfa iskeleti bileşenleri ve vitrin kartı.

CSS kütüphanelerinin (Bootstrap, Foundation, MUI, Semantic) ortak
dağarcığından gelen parçalar: üst şerit, açılış, bölüm, dip, yol, düğme
grubu, yıldız, katla, yan panel, liste grubu, ortam, zaman, kaydırak.

Vurgu davranışta: hangi bağ etkin, tıklayınca hangi sayı geliyor, uçta
sarılıyor mu, kapalıyken gerçekten çizilmiyor mu. Görsel denetim ayrı
(vitrin sayfası); burada test edilen mantık.
"""

from __future__ import annotations

import unittest

from test_gorunum import NODE, sahnede_calistir


def tekil(govde: str, durum: str = "0") -> str:
    """Tek bir görünümü çizen en küçük program."""
    return (
        'import "@ARAYUZ@"\n'
        "\n"
        "var uygulama: Uygulama<Int>? = none\n"
        "\n"
        "fn guncelle(n: Int) {\n"
        "  if uygulama != none {\n"
        "    uygulama!.degistir(n)\n"
        "  }\n"
        "}\n"
        "\n"
        f"fn ciz(n: Int) -> Gorunum = {govde}\n"
        "\n"
        "fn main() {\n"
        f"  uygulama = uygulamaBaslat(\"#uygulama\", {durum}, ciz)\n"
        "}\n"
    )


@unittest.skipIf(NODE is None, "node bulunamadı")
class IskeletTesti(unittest.TestCase):
    # --- üst şerit --------------------------------------------------------

    GEZINTI = tekil(
        'Gezinti("Nar", ["Ürün", "Belge", "Fiyat"], n, |i| { guncelle(i) },\n'
        '        Dugme("Başla", || { }))',
        "1",
    )

    def test_gezinti_marka_baglar_ve_eylem(self):
        kayit = sahnede_calistir(self.GEZINTI, "$yaz($dom.satirlar($dom.govde));")
        # Dar ekran menüsü de her zaman basılır: bağlar iki kez görünür.
        self.assertEqual(kayit[0][0], "Nar")
        self.assertIn("Ürün", kayit[0])
        self.assertIn("Başla", kayit[0])

    def test_gezintide_etkin_bag_isaretli(self):
        kayit = sahnede_calistir(self.GEZINTI, '''
const etkin = $dom.sinifliOgeler($dom.govde, "nar-gezinti-etkin");
$yaz(etkin.map((e) => e.textContent));
''')
        self.assertEqual(kayit[0], ["Belge"])

    def test_gezinti_baga_tiklayinca_sirasini_verir(self):
        kayit = sahnede_calistir(self.GEZINTI, '''
const serit = $dom.sinifliOgeler($dom.govde, "nar-gezinti-baglar")[0];
$dom.tikla($dom.dugme(serit, "Fiyat"));
const etkin = $dom.sinifliOgeler($dom.govde, "nar-gezinti-etkin");
$yaz(etkin.map((e) => e.textContent));
''')
        self.assertEqual(kayit[0], ["Fiyat"])

    # --- yol --------------------------------------------------------------

    def test_kirintinin_son_parcasi_dugme_degil(self):
        kaynak = tekil(
            'Kirinti(["Belge", "Arayüz", "Bileşen"], |i| { guncelle(i) })')
        kayit = sahnede_calistir(kaynak, '''
const yol = $dom.sinifliOgeler($dom.govde, "nar-kirinti")[0];
$yaz(yol.querySelectorAll("button").map((d) => d.textContent));
$yaz($dom.sinifliOgeler($dom.govde, "nar-kirinti-son").map((e) => e.textContent));
''')
        self.assertEqual(kayit[0], ["Belge", "Arayüz"])
        self.assertEqual(kayit[1], ["Bileşen"])

    # --- açılış, bölüm, dip ------------------------------------------------

    def test_kahraman_bos_alanlari_cizmez(self):
        dolu = tekil('Kahraman("Yeni", "Başlık", "Açıklama", [Dugme("Git", || { })])')
        bos = tekil('Kahraman("", "Başlık", "", [])')
        self.assertEqual(
            sahnede_calistir(dolu, "$yaz($dom.satirlar($dom.govde));")[0],
            ["Yeni", "Başlık", "Açıklama", "Git"],
        )
        self.assertEqual(
            sahnede_calistir(bos, "$yaz($dom.satirlar($dom.govde));")[0],
            ["Başlık"],
        )

    def test_altbilgi_sutunlari_ve_notu(self):
        kaynak = tekil(
            'AltBilgi(["Ürün", "Kurum"], [\n'
            '  [Bag("Belge", "#"), Bag("Fiyat", "#")],\n'
            '  [Bag("Hakkında", "#")]\n'
            '], "© 2026")')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-altbilgi-sutun").length);
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], 2)
        self.assertEqual(
            kayit[1],
            ["Ürün", "Belge", "Fiyat", "Kurum", "Hakkında", "© 2026"],
        )

    def test_bolum_basligi_yoksa_bas_kutusu_da_yok(self):
        kaynak = tekil('Bolum("", "", Metin("içerik"))')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-bolum-basi").length);
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], 0)
        self.assertEqual(kayit[1], ["içerik"])

    # --- düğme grubu, yıldız ----------------------------------------------

    def test_dugme_grubu_secilini_bildirir(self):
        kaynak = tekil('DugmeGrubu(["Gün", "Hafta", "Ay"], n, |i| { guncelle(i) })', "0")
        kayit = sahnede_calistir(kaynak, '''
const oku = () => $dom.sinifliOgeler($dom.govde, "nar-grup-dugmesi")
  .map((d) => d.getAttribute("aria-pressed"));
$yaz(oku());
$dom.tikla($dom.dugme($dom.govde, "Ay"));
$yaz(oku());
''')
        self.assertEqual(kayit[0], ["true", "false", "false"])
        self.assertEqual(kayit[1], ["false", "false", "true"])

    def test_yildiz_dolu_sayisi_ve_sifirlama(self):
        kaynak = tekil('Yildiz(n, 5, |v| { guncelle(v) })', "3")
        kayit = sahnede_calistir(kaynak, '''
const dolu = () => $dom.sinifliOgeler($dom.govde, "nar-yildiz-dolu").length;
$yaz(dolu());
const yildizlar = $dom.sinifliOgeler($dom.govde, "nar-yildiz-tek");
// Beşinciye basmak beşe çıkarır.
$dom.tikla(yildizlar[4]);
$yaz(dolu());
// Seçili olana tekrar basmak sıfırlar: vazgeçmenin yolu olmalı.
$dom.tikla($dom.sinifliOgeler($dom.govde, "nar-yildiz-tek")[4]);
$yaz(dolu());
''')
        self.assertEqual(kayit, [3, 5, 0])

    # --- katla, yan panel --------------------------------------------------

    def test_katla_kapaliyken_govdeyi_cizmez(self):
        kaynak = tekil(
            'Katla("Ayarlar", Metin("gizli içerik"), n == 1, || { guncelle(1 - n) })',
            "0")
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.satirlar($dom.govde));
$dom.tikla($dom.sinifliOgeler($dom.govde, "nar-katla-basi")[0]);
$yaz($dom.satirlar($dom.govde));
$yaz($dom.sinifliOgeler($dom.govde, "nar-katla")[0].getAttribute("aria-expanded"));
''')
        self.assertEqual(kayit[0], ["Ayarlar"])
        self.assertEqual(kayit[1], ["Ayarlar", "gizli içerik"])

    def test_yan_panel_kapaliyken_hicbir_sey_cizmez(self):
        kaynak = tekil(
            'YanPanel("Filtre", [Metin("içerik")], n == 1, || { guncelle(0) })', "0")
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-yanpanel").length);
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], 0)
        self.assertEqual(kayit[1], [])

    def test_yan_panel_acikken_perdeye_tiklamak_kapatir(self):
        kaynak = tekil(
            'YanPanel("Filtre", [Metin("içerik")], n == 1, || { guncelle(0) })', "1")
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.satirlar($dom.govde));
$dom.tikla($dom.sinifliOgeler($dom.govde, "nar-perde")[0]);
$yaz($dom.sinifliOgeler($dom.govde, "nar-yanpanel").length);
''')
        self.assertEqual(kayit[0], ["Filtre", "içerik"])
        self.assertEqual(kayit[1], 0)

    # --- liste grubu, ortam, zaman, kaydırak -------------------------------

    def test_liste_grubu_her_satiri_sarar(self):
        kaynak = tekil(
            'ListeGrubu([Metin("bir"), Metin("iki"), Metin("üç")])')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-liste-grubu-satir").length);
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], 3)
        self.assertEqual(kayit[1], ["bir", "iki", "üç"])

    def test_ortam_yan_ve_govdeyi_ayirir(self):
        kaynak = tekil('Ortam(Avatar("Ayşe Yılmaz", ""), Metin("yorum"))')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-ortam-yan")[0].textContent);
$yaz($dom.sinifliOgeler($dom.govde, "nar-ortam-govde")[0].textContent);
''')
        self.assertEqual(kayit[0], "AY")
        self.assertEqual(kayit[1], "yorum")

    def test_zaman_eksik_etiketi_atlar(self):
        # Zaman sayısı olay sayısından az: fazlalık olaylar etiketsiz çizilir.
        kaynak = tekil('Zaman(["09:12"], ["klonlandı", "derlendi"])')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-zaman-oge").length);
$yaz($dom.satirlar($dom.govde));
''')
        self.assertEqual(kayit[0], 2)
        self.assertEqual(kayit[1], ["09:12", "klonlandı", "derlendi"])

    def test_kaydirak_uclarda_sarilir(self):
        kaynak = tekil(
            'Kaydirak([Metin("bir"), Metin("iki"), Metin("üç")], n, |i| { guncelle(i) })',
            "0")
        kayit = sahnede_calistir(kaynak, '''
const pencere = () => $dom.sinifliOgeler($dom.govde, "nar-kaydirak-pencere")[0]
  .textContent;
const geri = () => $dom.sinifliOgeler($dom.govde, "nar-kaydirak-alt")[0]
  .querySelectorAll("button")[0];
const ileri = () => {
  const d = $dom.sinifliOgeler($dom.govde, "nar-kaydirak-alt")[0]
    .querySelectorAll("button");
  return d[d.length - 1];
};
$yaz(pencere());
$dom.tikla(geri());          // baştan geriye: sona sarar
$yaz(pencere());
$dom.tikla(ileri());         // sondan ileriye: başa sarar
$yaz(pencere());
''')
        self.assertEqual(kayit, ["bir", "üç", "bir"])

    def test_kaydirak_noktalari_etkini_isaretler(self):
        kaynak = tekil(
            'Kaydirak([Metin("bir"), Metin("iki")], n, |i| { guncelle(i) })', "1")
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-kaydirak-nokta").length);
$yaz($dom.sinifliOgeler($dom.govde, "nar-kaydirak-etkin")[0]
  .getAttribute("aria-label"));
''')
        self.assertEqual(kayit[0], 2)
        self.assertEqual(kayit[1], "2. öğe")

    # --- yığın -------------------------------------------------------------

    def test_yigin_sutundan_farkli_sinif_alir(self):
        kaynak = tekil('Yigin([Metin("bir"), Metin("iki")])')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.govde, "nar-yigin").length);
$yaz($dom.sinifliOgeler($dom.govde, "nar-sutun").length);
''')
        self.assertEqual(kayit[0], 1)
        self.assertEqual(kayit[1], 0)


@unittest.skipIf(NODE is None, "node bulunamadı")
class OrnekTesti(unittest.TestCase):
    """Vitrin kartı: gösterilen HTML ile çizilen ağaç ayrışamamalı."""

    def test_html_panosu_onizlemenin_kendisini_gosterir(self):
        kaynak = tekil(
            'Ornek("Rozet", "Rozet(\\"bilgi\\", TON_BILGI)",\n'
            '      Rozet("bilgi", TON_BILGI))')
        kayit = sahnede_calistir(kaynak, '''
const panolar = $dom.sinifliOgeler($dom.govde, "nar-ornek-pano");
$yaz(panolar.length);
$yaz($dom.sinifliOgeler(panolar[0], "nar-kod")[0].textContent);
$yaz($dom.sinifliOgeler(panolar[1], "nar-kod")[0].textContent);
$yaz($dom.sinifliOgeler($dom.govde, "nar-onizleme")[0].innerHTML);
''')
        self.assertEqual(kayit[0], 2)
        self.assertIn('Rozet("bilgi", TON_BILGI)', kayit[1])
        # İkinci pano önizlemenin HTML'ini taşır — biçimlenmiş hâliyle.
        html_panosu = kayit[2]
        self.assertIn('<span class="nar-rozet nar-rozet-bilgi">bilgi</span>',
                      html_panosu)
        # Ve o HTML gerçekten çizilen ağacın kendisi.
        self.assertIn('nar-rozet-bilgi', kayit[3])

    def test_bicimlendirme_ic_ice_gectikce_girintiler(self):
        kaynak = tekil(
            'Ornek("", "kod", Sutun([Satir([Metin("iç")])]))')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.sinifliOgeler($dom.govde, "nar-ornek-pano")[1],
  "nar-kod")[0].textContent);
''')
        satirlar = [s for s in kayit[0].split("\n") if s.strip()]
        # Etiket ve yazısı bir arada, kapanış aynı satırda.
        self.assertEqual(satirlar[0], '<div class="nar-sutun">')
        self.assertEqual(satirlar[1], '  <div class="nar-satir">')
        self.assertEqual(satirlar[2], '    <div class="nar-metin">iç</div>')
        self.assertEqual(satirlar[3], '  </div>')
        self.assertEqual(satirlar[4], '</div>')

    def test_bicimlendirme_bos_etiketi_kapatmaz(self):
        # `input` kapanış etiketi almaz; derinliği artırmamalı.
        kaynak = tekil(
            'Ornek("", "kod", Sutun([Giris("ad", "", |v| { }), Metin("alt")]))')
        kayit = sahnede_calistir(kaynak, '''
$yaz($dom.sinifliOgeler($dom.sinifliOgeler($dom.govde, "nar-ornek-pano")[1],
  "nar-kod")[0].textContent);
''')
        satirlar = [s for s in kayit[0].split("\n") if s.strip()]
        self.assertTrue(satirlar[1].startswith("  <input "), satirlar[1])
        # Girdiden sonraki kardeş aynı girinti kademesinde kalır.
        self.assertTrue(satirlar[2].startswith('  <div class="nar-metin">'),
                        satirlar[2])


if __name__ == "__main__":
    unittest.main()
