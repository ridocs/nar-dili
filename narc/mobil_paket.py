"""`nar build --target mobil` — Nar programını Android/iOS projesine paketler.

Üretilen klasör bir **Capacitor** projesidir. Capacitor, bir web sayfasını
gerçek bir mobil uygulamanın içine koyar; uygulama mağazaya yüklenebilir,
telefonun kamerasına/dosyalarına eklentilerle erişebilir.

Bu paketleyici projeyi hazır eder ama derlemez — Android derlemesi için
Android Studio, iOS için macOS + Xcode gerekir. Üretilen `BENIOKU.md`
hangi komutların çalıştırılacağını yazar.

Klasör aynı zamanda tek başına bir web sayfasıdır: `www/index.html`
tarayıcıda doğrudan açılabilir. Yani telefon olmadan da denenebilir.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Sayfa; masaüstü şablonunun mobil karşılığı. Farkları: dokunma için
# yakınlaştırma kapalı, güvenli alan (çentik) boşluğu, daha büyük dokunma
# hedefleri ve telefon genişliğinde yerleşim.
HTML_SABLONU = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1,
      maximum-scale=1, viewport-fit=cover">
<meta name="format-detection" content="telephone=no">
<title>{baslik}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; }}
  body {{
    margin: 0;
    padding: calc(16px + env(safe-area-inset-top)) 16px
            calc(16px + env(safe-area-inset-bottom));
    background: #FDFCFB;
    color: #1C1917;
    font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
    overscroll-behavior: none;
  }}
  /* Dokunma hedefleri parmakla rahat basılacak kadar büyük olmalı. */
  button, input, select, textarea {{
    font: inherit;
    min-height: 44px;
  }}
  #cikti {{
    margin-top: 16px;
    font-family: ui-monospace, "SFMono-Regular", "Menlo", "Consolas", monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-word;
  }}
  #cikti:empty {{ display: none; }}
</style>
</head>
<body>
<div id="uygulama"></div>
<div id="cikti"></div>
<script>
// `print` çıktısı hem konsola hem sayfaya gider.
(function () {{
  var hedef = document.getElementById("cikti");
  var asil = console.log.bind(console);
  console.log = function () {{
    var parcalar = Array.prototype.slice.call(arguments);
    asil.apply(null, parcalar);
    hedef.textContent += parcalar.join(" ") + "\\n";
  }};
}})();
</script>
<script>
{kod}
</script>
</body>
</html>
"""

BENIOKU = """# {baslik}

Bu klasör, Nar ile yazılmış bir **mobil uygulamadır** (Android ve iOS).
Capacitor projesi olarak hazırlandı.

## Önce tarayıcıda dene

Telefon gerekmez:

```
www/index.html
```

dosyasını tarayıcıda aç. Uygulamanın tamamı burada çalışır.

## Android

Gerekenler: **Node.js**, **Android Studio** (içinde JDK gelir).

```
npm install
npx cap add android
npx cap open android
```

Son komut Android Studio'yu açar; oradaki yeşil ▶ düğmesiyle telefonda
ya da emülatörde çalıştırırsın. Mağazaya yüklenecek dosyayı
(`.aab`) Android Studio'nun *Build > Generate Signed Bundle* menüsünden
alırsın.

## iOS

Gerekenler: **macOS**, **Xcode**, **CocoaPods**.

```
npm install
npx cap add ios
npx cap open ios
```

## Kodu değiştirince

Nar dosyanı değiştirdiğinde bu klasörü yeniden üret, sonra:

```
npx cap sync
```

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `www/index.html` | Uygulamanın kendisi (Nar'dan üretilmiş JavaScript gömülü) |
| `capacitor.config.json` | Uygulama kimliği, adı, açılış ayarları |
| `package.json` | Capacitor bağımlılıkları |

`android/` ve `ios/` klasörleri `npx cap add` komutuyla oluşur; bu
paketleyici onları üretmez çünkü platform araçları gerektirir.

---
Kaynak: `{kaynak}` · Nar ile üretildi.
"""

GITIGNORE = """node_modules/
android/
ios/
.DS_Store
"""


def uygulama_kimligi(ad: str) -> str:
    """Dosya adından ters alan adı biçiminde bir uygulama kimliği türetir.

    Android paket adı ve iOS bundle id aynı kurala uyar: noktayla ayrılmış
    parçalar, her parça bir harfle başlar, yalnızca harf/rakam içerir.
    """
    temiz = re.sub(r"[^a-z0-9]+", "", ad.lower())
    if not temiz or not temiz[0].isalpha():
        temiz = "uygulama" + temiz
    return f"com.nar.{temiz}"


def paketle(js_kodu: str, hedef: Path, baslik: str, kaynak_adi: str,
            kimlik: str | None = None) -> list[Path]:
    """Capacitor proje klasörünü oluşturur, yazılan dosyaları döndürür."""
    hedef.mkdir(parents=True, exist_ok=True)
    www = hedef / "www"
    www.mkdir(exist_ok=True)

    sayfa = www / "index.html"
    sayfa.write_text(HTML_SABLONU.format(baslik=baslik, kod=js_kodu), encoding="utf-8")

    app_id = kimlik or uygulama_kimligi(Path(kaynak_adi).stem)

    yapilandirma = hedef / "capacitor.config.json"
    yapilandirma.write_text(
        json.dumps(
            {
                "appId": app_id,
                "appName": baslik,
                "webDir": "www",
                "server": {"androidScheme": "https"},
                "android": {"allowMixedContent": False},
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    paket = hedef / "package.json"
    paket.write_text(
        json.dumps(
            {
                "name": re.sub(r"[^a-z0-9\-]+", "-", baslik.lower()).strip("-") or "nar-uygulamasi",
                "version": "1.0.0",
                "private": True,
                "description": f"{baslik} — Nar ile yazıldı",
                "scripts": {
                    "android": "cap add android && cap open android",
                    "ios": "cap add ios && cap open ios",
                    "sync": "cap sync",
                },
                "devDependencies": {
                    "@capacitor/cli": "^6.0.0",
                },
                "dependencies": {
                    "@capacitor/android": "^6.0.0",
                    "@capacitor/core": "^6.0.0",
                    "@capacitor/ios": "^6.0.0",
                },
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    yoksay = hedef / ".gitignore"
    yoksay.write_text(GITIGNORE, encoding="utf-8")

    benioku = hedef / "BENIOKU.md"
    benioku.write_text(
        BENIOKU.format(baslik=baslik, kaynak=kaynak_adi), encoding="utf-8")

    return [sayfa, yapilandirma, paket, yoksay, benioku]
