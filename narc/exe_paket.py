"""Nar uygulamasını tek bir Windows `.exe` dosyasına çevirir.

Neden var: `.ghb` paketi Python'la açılıyordu; uygulamayı alan kişinin
makinesinde Python yoksa dosya hiçbir şey yapmıyordu. Bir uygulama tek
başına açılabilmeli.

Nasıl çalışır: küçük bir C# başlatıcı derlenir, uygulamanın paketi (zip)
exe'nin sonuna eklenir, en sona da 16 baytlık bir kuyruk yazılır:

    <8 bayt: paketin başladığı konum, little-endian> <8 bayt: "NAREXE01">

Exe açılınca kendini okur, kuyruktan paketi bulur, `%LOCALAPPDATA%\\Nar`
altına çıkarır ve Edge'in (ya da Chrome'un) uygulama modunda kendi
penceresinde açar. Python, Node, hiçbir kurulum gerekmez: C# derleyicisi
her Windows'ta .NET Framework ile hazır gelir (`csc.exe`), Edge de öyle.

Aynı başlatıcı `.ghb` dosyalarını da açar: argüman olarak bir `.ghb` yolu
verilirse gömülü paket yerine onu kullanır. `nar uzanti-kur --exe` bunu
çift tıklama işleyicisi yapar; Python devreden çıkar.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from .ghb_paket import paketle as ghb_paketle

KOK = Path(__file__).resolve().parent.parent
IMZA = b"NAREXE01"
KUYRUK_BOYU = 16


class ExeHatasi(Exception):
    """Exe üretilemedi."""


# C# 5 ile yazıldı: .NET Framework'ün kendi derleyicisi bundan yenisini
# bilmez. Metin içi `$"..."`, `?.`, `using static` yok.
BASLATICI_KAYNAGI = r'''
using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

static class NarBaslatici
{
    const string IMZA = "NAREXE01";
    static bool sessiz = false;   // --cikar modunda pencere yerine konsol

    [STAThread]
    static int Main(string[] args)
    {
        try { return Calistir(args); }
        catch (Exception e) { Hata(e.Message); return 1; }
    }

    static int Calistir(string[] args)
    {
        string cikarKlasoru = null;
        string ghb = null;
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--cikar" && i + 1 < args.Length) { cikarKlasoru = args[++i]; sessiz = true; }
            else if (args[i].EndsWith(".ghb", StringComparison.OrdinalIgnoreCase)) ghb = args[i];
        }

        byte[] paket = ghb != null ? File.ReadAllBytes(ghb) : GomuluPaket();
        if (paket == null)
        {
            Hata("Bu dosyanin icinde uygulama yok. Acmak icin bir .ghb dosyasi verin.");
            return 1;
        }

        string ad = "uygulama";
        int en = 1000, boy = 700;
        string hedef;
        using (var arsiv = new ZipArchive(new MemoryStream(paket), ZipArchiveMode.Read))
        {
            var meta = arsiv.GetEntry("nar.json");
            if (meta == null) throw new Exception("pakette nar.json yok; bu bir Nar uygulamasi degil");
            string json;
            using (var r = new StreamReader(meta.Open(), Encoding.UTF8)) json = r.ReadToEnd();
            ad = Metin(json, "ad", ad);
            en = Sayi(json, "genislik", en);
            boy = Sayi(json, "yukseklik", boy);

            hedef = cikarKlasoru ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Nar", "uygulamalar", Guvenli(ad) + "-" + Ozet(paket));
            Cikar(arsiv, hedef);
        }

        string giris = Path.Combine(hedef, "index.html");
        if (!File.Exists(giris)) throw new Exception("pakette index.html yok");
        if (cikarKlasoru != null) { Console.WriteLine(giris); return 0; }
        return PencereAc(giris, en, boy, hedef);
    }

    // Exe'nin kendi sonundaki paket. Kuyruk yoksa null.
    static byte[] GomuluPaket()
    {
        string kendi = Process.GetCurrentProcess().MainModule.FileName;
        byte[] hepsi = File.ReadAllBytes(kendi);
        if (hepsi.Length < 16) return null;
        string imza = Encoding.ASCII.GetString(hepsi, hepsi.Length - 8, 8);
        if (imza != IMZA) return null;
        long bas = BitConverter.ToInt64(hepsi, hepsi.Length - 16);
        long uzunluk = hepsi.Length - 16 - bas;
        if (bas < 0 || uzunluk <= 0) return null;
        byte[] paket = new byte[uzunluk];
        Array.Copy(hepsi, bas, paket, 0, uzunluk);
        return paket;
    }

    // Aynı paket bir kez çıkarılır; klasör adı paketin özetini taşır, yani
    // uygulama güncellenince yeni klasöre çıkar.
    static void Cikar(ZipArchive arsiv, string hedef)
    {
        string isaret = Path.Combine(hedef, ".tamam");
        if (File.Exists(isaret)) return;
        Directory.CreateDirectory(hedef);
        string kokTam = Path.GetFullPath(hedef).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        foreach (var e in arsiv.Entries)
        {
            if (e.FullName.EndsWith("/")) continue;
            string yol = Path.GetFullPath(Path.Combine(hedef, e.FullName.Replace('/', Path.DirectorySeparatorChar)));
            // Zip Slip: paket kendi klasorunun disina yazamaz.
            if (!yol.StartsWith(kokTam, StringComparison.OrdinalIgnoreCase))
                throw new Exception("pakette guvenli olmayan yol: " + e.FullName);
            Directory.CreateDirectory(Path.GetDirectoryName(yol));
            using (var giris = e.Open())
            using (var cikis = File.Create(yol)) giris.CopyTo(cikis);
        }
        File.WriteAllText(isaret, "");
    }

    static int PencereAc(string giris, int en, int boy, string klasor)
    {
        string tarayici = TarayiciBul();
        string adres = new Uri(giris).AbsoluteUri;
        if (tarayici != null)
        {
            string profil = Path.Combine(klasor, ".pencere-profili");
            Directory.CreateDirectory(profil);
            var psi = new ProcessStartInfo(tarayici,
                "--app=\"" + adres + "\" --window-size=" + en + "," + boy +
                " --user-data-dir=\"" + profil + "\" --no-first-run --no-default-browser-check");
            psi.UseShellExecute = false;
            var p = Process.Start(psi);
            p.WaitForExit();
            return 0;
        }
        // Son care: varsayilan tarayici sekmesi.
        var vs = new ProcessStartInfo(giris);
        vs.UseShellExecute = true;
        Process.Start(vs);
        return 0;
    }

    static string TarayiciBul()
    {
        string[] adaylar = {
            Environment.ExpandEnvironmentVariables(@"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            Environment.ExpandEnvironmentVariables(@"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            Environment.ExpandEnvironmentVariables(@"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            Environment.ExpandEnvironmentVariables(@"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            Environment.ExpandEnvironmentVariables(@"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        };
        foreach (var yol in adaylar) if (File.Exists(yol)) return yol;
        return null;
    }

    static string Metin(string json, string ad, string varsayilan)
    {
        var m = Regex.Match(json, "\"" + ad + "\"\\s*:\\s*\"([^\"]*)\"");
        return m.Success ? m.Groups[1].Value : varsayilan;
    }

    static int Sayi(string json, string ad, int varsayilan)
    {
        var m = Regex.Match(json, "\"" + ad + "\"\\s*:\\s*(\\d+)");
        int deger;
        return m.Success && int.TryParse(m.Groups[1].Value, out deger) ? deger : varsayilan;
    }

    static string Guvenli(string ad)
    {
        var sb = new StringBuilder();
        foreach (char c in ad) sb.Append(char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_');
        return sb.Length == 0 ? "uygulama" : sb.ToString();
    }

    static string Ozet(byte[] veri)
    {
        using (var sha = SHA1.Create())
        {
            byte[] h = sha.ComputeHash(veri);
            var sb = new StringBuilder();
            for (int i = 0; i < 5; i++) sb.Append(h[i].ToString("x2"));
            return sb.ToString();
        }
    }

    static void Hata(string mesaj)
    {
        if (sessiz) { Console.Error.WriteLine("hata: " + mesaj); return; }
        MessageBox.Show(mesaj, "Nar", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }
}
'''


def csc_bul() -> Path | None:
    """.NET Framework'ün C# derleyicisi. Her Windows'ta vardır."""
    if os.name != "nt":
        return None
    kok = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET"
    for alt in ("Framework64", "Framework"):
        aday = kok / alt / "v4.0.30319" / "csc.exe"
        if aday.exists():
            return aday
    return None


def _kaynak_ozeti() -> str:
    return hashlib.sha256(BASLATICI_KAYNAGI.encode("utf-8")).hexdigest()[:12]


def baslatici_derle(onbellek: Path | None = None) -> Path:
    """Başlatıcıyı derler; kaynak değişmediyse önbellektekini verir."""
    csc = csc_bul()
    if csc is None:
        raise ExeHatasi(
            "C# derleyicisi (csc.exe) bulunamadı; .exe yalnızca Windows'ta "
            "üretilebilir")

    onbellek = onbellek or (KOK / ".narbuild")
    onbellek.mkdir(parents=True, exist_ok=True)
    hedef = onbellek / f"nar-baslatici-{_kaynak_ozeti()}.exe"
    if hedef.exists():
        return hedef

    kaynak = onbellek / "nar_baslatici.cs"
    kaynak.write_text(BASLATICI_KAYNAGI, encoding="utf-8-sig")
    simge = KOK / "site" / "nar.ico"

    komut = [
        str(csc), "/nologo", "/target:winexe", "/optimize+",
        "/platform:anycpu", f"/out:{hedef}",
        "/r:System.dll", "/r:System.IO.Compression.dll",
        "/r:System.IO.Compression.FileSystem.dll", "/r:System.Windows.Forms.dll",
    ]
    if simge.exists():
        komut.append(f"/win32icon:{simge}")
    komut.append(str(kaynak))

    sonuc = subprocess.run(komut, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if sonuc.returncode != 0 or not hedef.exists():
        raise ExeHatasi("başlatıcı derlenemedi:\n" + (sonuc.stdout + sonuc.stderr).strip())
    return hedef


def exe_yaz(baslatici: Path, paket: bytes, hedef: Path) -> Path:
    """Başlatıcının sonuna paketi ve kuyruğu ekleyip exe'yi yazar."""
    govde = baslatici.read_bytes()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with open(hedef, "wb") as f:
        f.write(govde)
        f.write(paket)
        f.write(struct.pack("<q", len(govde)))
        f.write(IMZA)
    return hedef


def paket_ayir(exe: bytes) -> bytes | None:
    """Exe'nin sonundaki paketi verir; kuyruk yoksa None (başlatıcının aynısı)."""
    if len(exe) < KUYRUK_BOYU or exe[-8:] != IMZA:
        return None
    bas = struct.unpack("<q", exe[-16:-8])[0]
    if bas < 0 or bas >= len(exe) - KUYRUK_BOYU:
        return None
    return exe[bas:-KUYRUK_BOYU]


def paketle(js_kodu: str, hedef: Path, baslik: str, kaynak_adi: str,
            genislik: int = 1000, yukseklik: int = 700) -> Path:
    """Programı tek bir `.exe` olarak yazar ve yolunu döndürür."""
    baslatici = baslatici_derle()
    with tempfile.TemporaryDirectory() as tmp:
        ghb = ghb_paketle(js_kodu, Path(tmp) / baslik, baslik, kaynak_adi,
                          genislik, yukseklik)
        paket = ghb.read_bytes()
    return exe_yaz(baslatici, paket, hedef.with_suffix(".exe"))


def calistirici_kur() -> Path:
    """Başlatıcıyı kullanıcının uygulama klasörüne koyar; `.ghb` işleyicisi olur."""
    baslatici = baslatici_derle()
    yer = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Nar"
    yer.mkdir(parents=True, exist_ok=True)
    hedef = yer / "nar-ac.exe"
    shutil.copyfile(baslatici, hedef)
    return hedef
