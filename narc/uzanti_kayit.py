"""`.ghb` uzantısını Windows'ta Nar Çalıştırıcı'ya bağlar.

Kayıtlar **yalnızca kullanıcı için** yazılır (HKEY_CURRENT_USER). Yönetici
hakkı gerekmez ve `nar uzanti-kaldir` ile tamamen geri alınır; sistem
genelinde hiçbir şey değişmez.

Yazılan anahtarlar:

    HKCU\\Software\\Classes\\.ghb          → "Nar.Uygulama"
    HKCU\\Software\\Classes\\Nar.Uygulama  → görünen ad, simge, açma komutu

Bu, Windows'un belgelenmiş dosya ilişkilendirme yoludur.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

UZANTI = ".ghb"
TUR_ADI = "Nar.Uygulama"
GORUNEN_AD = "Nar Uygulaması"


def desteklenir_mi() -> bool:
    return os.name == "nt"


def baslatici_betigi(kok: Path) -> Path:
    """Çift tıklamada çalışan giriş betiği.

    Ayrı bir betik gerekli: `-m narc` çağrısı paketin Python yolunda
    olmasını ister, çift tıklamada ise çalışma dizini paketin yeri değil.
    Bu betik kendi konumundan projeyi bulur.
    """
    return kok / "nar_ac.py"


def baslatici_komutu(kok: Path) -> str:
    """Çift tıklamada çalışacak komut satırı.

    `pythonw.exe` seçilir: konsol penceresi açmaz. Bulunamazsa `python.exe`
    kullanılır — uygulama yine açılır, yanında bir konsol da görünür.
    """
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    yorumlayici = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{yorumlayici}" "{baslatici_betigi(kok)}" "%1"'


def kur(kok: Path) -> tuple[bool, str]:
    """İlişkilendirmeyi kurar. (başarılı, mesaj) döndürür."""
    if not desteklenir_mi():
        return False, "dosya ilişkilendirme yalnızca Windows'ta kuruluyor"

    betik = baslatici_betigi(kok)
    if not betik.exists():
        return False, f"başlatıcı betiği bulunamadı: {betik}"

    import winreg

    komut = baslatici_komutu(kok)
    simge = kok / "site" / "nar.ico"

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              rf"Software\Classes\{UZANTI}") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, TUR_ADI)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              rf"Software\Classes\{TUR_ADI}") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, GORUNEN_AD)

        if simge.exists():
            with winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    rf"Software\Classes\{TUR_ADI}\DefaultIcon") as k:
                winreg.SetValueEx(k, None, 0, winreg.REG_SZ, f"{simge},0")

        with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{TUR_ADI}\shell\open\command") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, komut)

        _kabuga_haber_ver()
        return True, (
            f"{UZANTI} uzantısı bağlandı.\n"
            f"  komut: {komut}\n"
            "Artık bir .ghb dosyasına çift tıklayınca uygulama açılır.\n"
            "Geri almak için: nar uzanti-kaldir"
        )
    except OSError as e:
        return False, f"kayıt yazılamadı: {e}"


def kaldir() -> tuple[bool, str]:
    """İlişkilendirmeyi tamamen kaldırır."""
    if not desteklenir_mi():
        return False, "dosya ilişkilendirme yalnızca Windows'ta kuruluyor"

    import winreg

    # Alt anahtarlar önce silinmeli: dolu bir anahtar silinemez.
    silinecek = [
        rf"Software\Classes\{TUR_ADI}\shell\open\command",
        rf"Software\Classes\{TUR_ADI}\shell\open",
        rf"Software\Classes\{TUR_ADI}\shell",
        rf"Software\Classes\{TUR_ADI}\DefaultIcon",
        rf"Software\Classes\{TUR_ADI}",
        rf"Software\Classes\{UZANTI}",
    ]
    silinen = 0
    for yol in silinecek:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, yol)
            silinen += 1
        except FileNotFoundError:
            pass
        except OSError:
            pass

    _kabuga_haber_ver()
    if silinen == 0:
        return True, f"{UZANTI} zaten bağlı değildi"
    return True, f"{UZANTI} uzantısı kaldırıldı ({silinen} kayıt silindi)"


def durum() -> str:
    """İlişkilendirmenin şu anki durumunu anlatır."""
    if not desteklenir_mi():
        return "bu sistemde dosya ilişkilendirme desteklenmiyor"

    import winreg

    try:
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{TUR_ADI}\shell\open\command") as k:
            komut = winreg.QueryValueEx(k, None)[0]
        return f"{UZANTI} bağlı:\n  {komut}"
    except FileNotFoundError:
        return f"{UZANTI} bağlı değil (kurmak için: nar uzanti-kur)"


def _kabuga_haber_ver() -> None:
    """Gezgin'e ilişkilendirmelerin değiştiğini bildirir.

    Bu çağrı olmadan değişiklik Gezgin yeniden başlayana kadar görünmez.
    """
    try:
        import ctypes
        # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass
