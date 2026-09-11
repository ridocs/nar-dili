"""Çalışma zamanını programın gerçekten kullandığı parçalara indirir.

Üretilen her program çalışma zamanının tamamını başına gömüyordu.
`print("Merhaba")` için bu 26 KB demekti ve %99'u hiç çalışmayan koddu.
Tek dosyalık web sayfalarında, `.ghb` paketlerinde ve deneme alanında bu
doğrudan indirme boyutu olarak görünüyor.

Nasıl çalışır: çalışma zamanı üst düzey bildirimlere bölünür, aralarındaki
çağrı grafiği çıkarılır, üretilen gövdenin adıyla andığı parçalardan
başlanıp geçişli kapanış alınır. Kalanlar atılır.

Doğruluğun dayandığı nokta şu: üretilen kod çalışma zamanı yardımcılarını
**her zaman adıyla** çağırır — dinamik bir çağrı yoktur. Bu yüzden metinde
geçen ad kümesi, gerçekten kullanılan küme ile aynıdır.

Ad kaçırmak programı kırar, fazladan ad almak yalnızca çıktıyı büyütür; o
yüzden şüpheli her yerde fazladan almak yeğlenir. Yine de yorumlar taranmaz:
başlıktaki açıklama satırları her programa her şeyi çekerdi.
"""

from __future__ import annotations

import re

# Üst düzey bir bildirimin başlangıcı. Girintili satırlar bir bildirimin
# içindedir, o yüzden desen satır başına bağlıdır.
_BILDIRIM = re.compile(
    r"^(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)")

_AD = re.compile(r"[A-Za-z_$][\w$]*")


def _yorumlari_at(kaynak: str) -> str:
    """Yorumları boşlukla değiştirir; metin literalleri korunur.

    Satır sayısı ve uzunluklar korunmaz, gerek de yok: bu metin yalnızca
    ad taramak için kullanılır, çıktıya girmez.
    """
    sonuc: list[str] = []
    i = 0
    n = len(kaynak)
    while i < n:
        c = kaynak[i]
        d = kaynak[i + 1] if i + 1 < n else ""

        if c == "/" and d == "/":
            while i < n and kaynak[i] != "\n":
                i += 1
            continue
        if c == "/" and d == "*":
            i += 2
            while i < n and not (kaynak[i] == "*" and i + 1 < n
                                 and kaynak[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c in "\"'`":
            kapanis = c
            sonuc.append(c)
            i += 1
            while i < n:
                if kaynak[i] == "\\":
                    sonuc.append(kaynak[i:i + 2])
                    i += 2
                    continue
                sonuc.append(kaynak[i])
                if kaynak[i] == kapanis:
                    i += 1
                    break
                i += 1
            continue

        sonuc.append(c)
        i += 1
    return "".join(sonuc)


class Parca:
    """Çalışma zamanının bir üst düzey bildirimi ve ona yapışık yorumları."""

    def __init__(self, ad: str, metin: str) -> None:
        self.ad = ad
        self.metin = metin
        self.bagimliliklar: set[str] = set()


def _parcalara_ayir(kaynak: str) -> tuple[str, list[Parca]]:
    """(önsöz, parçalar) döndürür.

    Önsöz ilk bildirimden önceki her şeydir: başlık yorumu ve
    `"use strict"`. Her zaman çıktıya girer.
    """
    satirlar = kaynak.split("\n")
    baslangiclar: list[tuple[int, str]] = []
    for i, satir in enumerate(satirlar):
        m = _BILDIRIM.match(satir)
        if m:
            baslangiclar.append((i, m.group(1)))

    if not baslangiclar:
        return kaynak, []

    # Bildirimin hemen üstündeki yorum bloğu ona aittir; açıklamasız kalan
    # bir yardımcı okunmaz olur.
    def yorum_basi(bitis: int, alt_sinir: int) -> int:
        bas = bitis
        while bas > alt_sinir:
            onceki = satirlar[bas - 1].strip()
            if onceki.startswith("//"):
                bas -= 1
            else:
                break
        return bas

    parcalar: list[Parca] = []
    onsoz_sonu = yorum_basi(baslangiclar[0][0], 0)

    for sira, (satir_no, ad) in enumerate(baslangiclar):
        bas = yorum_basi(satir_no, 0 if sira == 0 else baslangiclar[sira - 1][0])
        if sira + 1 < len(baslangiclar):
            sonraki = baslangiclar[sira + 1][0]
            son = yorum_basi(sonraki, satir_no)
        else:
            son = len(satirlar)
        parcalar.append(Parca(ad, "\n".join(satirlar[bas:son]).rstrip()))

    onsoz = "\n".join(satirlar[:onsoz_sonu]).rstrip()
    return onsoz, parcalar


def _gecen_adlar(metin: str, bilinen: set[str]) -> set[str]:
    kod = _yorumlari_at(metin)
    return {ad for ad in _AD.findall(kod) if ad in bilinen}


def buda(calisma_zamani: str, govde: str) -> str:
    """Gövdenin kullandığı çalışma zamanı parçalarını döndürür.

    `govde`, üretilmiş program metnidir. Ondaki adlardan başlanır ve
    çalışma zamanının kendi içindeki çağrılar geçişli olarak izlenir.
    """
    onsoz, parcalar = _parcalara_ayir(calisma_zamani)
    if not parcalar:
        return calisma_zamani.rstrip()

    ada_gore = {p.ad: p for p in parcalar}
    bilinen = set(ada_gore)

    for p in parcalar:
        p.bagimliliklar = _gecen_adlar(p.metin, bilinen) - {p.ad}

    gerekli: set[str] = set()
    yigin = list(_gecen_adlar(govde, bilinen))
    while yigin:
        ad = yigin.pop()
        if ad in gerekli:
            continue
        gerekli.add(ad)
        yigin.extend(ada_gore[ad].bagimliliklar - gerekli)

    # Kaynaktaki sıra korunur: bildirimler birbirine sırayla bağlı olabilir
    # (`const` bir öncekini kullanabilir).
    tutulan = [p.metin for p in parcalar if p.ad in gerekli]
    if not tutulan:
        return onsoz
    return onsoz + "\n\n" + "\n\n".join(tutulan)


def olcum(calisma_zamani: str, govde: str) -> tuple[int, int, int]:
    """(toplam parça, tutulan parça, kazanılan bayt) — ölçmek için."""
    _, parcalar = _parcalara_ayir(calisma_zamani)
    budanmis = buda(calisma_zamani, govde)
    tutulan = sum(1 for p in parcalar
                  if p.metin in budanmis)
    return len(parcalar), tutulan, len(calisma_zamani) - len(budanmis)
