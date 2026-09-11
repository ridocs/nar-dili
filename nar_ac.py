"""Nar Çalıştırıcı — `.ghb` uygulamasını açar.

Bir `.ghb` dosyasına çift tıklandığında Windows bu betiği çağırır.
Ayrı bir dosya olması gerekiyor: çift tıklamada çalışma dizini paketin
bulunduğu yer olur, `-m narc` çağrısı ise projeyi Python yolunda arar.
Bu betik kendi konumundan projeyi bulur.

Elle de çalıştırılabilir:

    python nar_ac.py uygulama.ghb
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from narc.ghb_calistir import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
