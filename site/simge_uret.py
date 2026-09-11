"""Nar simgesini (`nar.ico`) üretir.

Dış bağımlılık kullanmadan: PNG'ler zlib ile elle yazılır, ICO kabuğu da
birkaç bayttan ibarettir. Böylece simge depoda bir ikili dosya olarak
değil, onu üreten kodla birlikte durur — değiştirmek isteyen burayı
düzenler.

Çizim: koyu kırmızı bir nar, üstünde yeşil bir sap ve gövdesinde açık
renkli birkaç tane.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

# Palet — sitedeki vurgu rengiyle aynı aileden.
KABUK = (163, 42, 47)          # #A32A2F
KABUK_KOYU = (124, 30, 34)
TANE = (255, 214, 214)
SAP = (74, 124, 89)
SEFFAF = (0, 0, 0, 0)


def _daire_icinde(x: float, y: float, mx: float, my: float, r: float) -> bool:
    return (x - mx) ** 2 + (y - my) ** 2 <= r * r


def pikselleri_uret(n: int) -> list[list[tuple]]:
    """`n × n` boyutunda RGBA piksel dizisi."""
    orta = n / 2.0
    yaricap = n * 0.36
    govde_merkezi_y = orta + n * 0.06

    satirlar: list[list[tuple]] = []
    for sy in range(n):
        satir: list[tuple] = []
        for sx in range(n):
            # Piksel merkezleri; kenarları yumuşatmak için 2×2 örnekleme.
            kapsam = 0
            for ox in (0.25, 0.75):
                for oy in (0.25, 0.75):
                    x, y = sx + ox, sy + oy
                    if _daire_icinde(x, y, orta, govde_merkezi_y, yaricap):
                        kapsam += 1
            if kapsam == 0:
                satir.append(SEFFAF)
                continue

            # Işık sol üstten gelir. Gölge keskin bir çizgiyle değil,
            # ışığa olan uzaklıkla kademeli koyulaşır.
            x, y = sx + 0.5, sy + 0.5
            uzaklik = ((x - orta) + (y - govde_merkezi_y)) / (yaricap * 2)
            karisim = min(1.0, max(0.0, (uzaklik + 0.35) * 1.1))
            renk = tuple(
                int(KABUK[i] + (KABUK_KOYU[i] - KABUK[i]) * karisim)
                for i in range(3)
            )

            # Taneler: gövdenin ortasına simetrik birkaç nokta
            tane_r = max(1.0, n * 0.058)
            tane_yerleri = [
                (orta, govde_merkezi_y - n * 0.13),
                (orta - n * 0.13, govde_merkezi_y - n * 0.01),
                (orta + n * 0.13, govde_merkezi_y - n * 0.01),
                (orta - n * 0.07, govde_merkezi_y + n * 0.14),
                (orta + n * 0.07, govde_merkezi_y + n * 0.14),
            ]
            for tx, ty in tane_yerleri:
                if _daire_icinde(x, y, tx, ty, tane_r):
                    renk = TANE
                    break

            alfa = int(255 * kapsam / 4)
            satir.append((renk[0], renk[1], renk[2], alfa))
        satirlar.append(satir)

    # Sap: gövdenin üstünde kısa bir çubuk
    sap_x0 = int(orta - n * 0.045)
    sap_x1 = int(orta + n * 0.045)
    sap_y0 = int(govde_merkezi_y - yaricap - n * 0.14)
    sap_y1 = int(govde_merkezi_y - yaricap + n * 0.04)
    for sy in range(max(0, sap_y0), min(n, sap_y1)):
        for sx in range(max(0, sap_x0), min(n, sap_x1 + 1)):
            satirlar[sy][sx] = (SAP[0], SAP[1], SAP[2], 255)

    return satirlar


def png_yaz(pikseller: list[list[tuple]]) -> bytes:
    """RGBA piksel dizisini PNG baytlarına çevirir."""
    yukseklik = len(pikseller)
    genislik = len(pikseller[0])

    ham = bytearray()
    for satir in pikseller:
        ham.append(0)  # filtre türü: yok
        for r, g, b, a in satir:
            ham.extend((r, g, b, a))

    def parca(tur: bytes, veri: bytes) -> bytes:
        govde = tur + veri
        return (struct.pack(">I", len(veri)) + govde
                + struct.pack(">I", zlib.crc32(govde) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", genislik, yukseklik, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + parca(b"IHDR", ihdr)
            + parca(b"IDAT", zlib.compress(bytes(ham), 9))
            + parca(b"IEND", b""))


def ico_yaz(boyutlar: list[int]) -> bytes:
    """Birden çok boyutu tek ICO dosyasında toplar.

    Windows küçük listede 16'yı, masaüstünde 48'i, büyük simgede 256'yı
    kullanır; hepsini koymak her yerde net görünmesini sağlar.
    """
    pngler = [png_yaz(pikselleri_uret(b)) for b in boyutlar]

    baslik_boyu = 6 + 16 * len(boyutlar)
    ofset = baslik_boyu
    girdiler = bytearray()
    for boyut, png in zip(boyutlar, pngler):
        # ICO'da 256, sıfır olarak yazılır.
        en = 0 if boyut >= 256 else boyut
        girdiler.extend(struct.pack(
            "<BBBBHHII", en, en, 0, 0, 1, 32, len(png), ofset))
        ofset += len(png)

    return (struct.pack("<HHH", 0, 1, len(boyutlar))
            + bytes(girdiler) + b"".join(pngler))


def main() -> int:
    kok = Path(__file__).resolve().parent
    ico = kok / "nar.ico"
    ico.write_bytes(ico_yaz([16, 32, 48, 64, 128, 256]))

    png = kok / "nar.png"
    png.write_bytes(png_yaz(pikselleri_uret(256)))

    print(f"yazıldı: {ico}  ({ico.stat().st_size // 1024} KB)")
    print(f"yazıldı: {png}  ({png.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
