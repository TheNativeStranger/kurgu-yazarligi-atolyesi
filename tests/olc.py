#!/usr/bin/env python3
"""Redaktörün imla çıktısını beklenen düzeltmelerle karşılaştırır.

Kullanım:
    python3 tests/olc.py <eser>/atolye/.calisma/gorusler/*.dogrulanmis.json [--beklenen tests/metinler/hatali-30.beklenen.json]

İki hedef ölçülür (BRD, kabul ölçütleri):
    bulma oranı           en az %90
    "kesin" doğruluğu     en az %95
Tuzaklar (doğru yazılmış ama hataya benzeyen yerler) hata olarak gösterilmemelidir.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from atolye import esle  # noqa: E402

VARSAYILAN = Path(__file__).resolve().parent / "metinler" / "hatali-30.beklenen.json"


def eslesir(bulgu, hata):
    """Bulgunun yaptığı değişiklik beklenen düzeltmeyle aynı mı (kısa ya da uzun alıntıyla)."""
    mevcut, oneri = esle(bulgu.get("mevcut")), esle(bulgu.get("oneri"))
    hm, ho = esle(hata["mevcut"]), esle(hata["oneri"])
    if not mevcut or bulgu.get("oneri") is None:
        return False
    if mevcut in hm:
        return hm.replace(mevcut, oneri, 1) == ho
    if hm in mevcut:
        return mevcut.replace(hm, ho, 1) == oneri
    return False


def tuzaga_dustu(bulgu, tuzak):
    """Bulgu tuzağı değiştiriyorsa: tuzak mevcutta geçiyor ama öneride aynen kalmıyor."""
    mevcut, oneri, t = esle(bulgu.get("mevcut")), esle(bulgu.get("oneri")), esle(tuzak)
    return bool(mevcut) and t in mevcut and t not in oneri


def olc(bulgular, beklenen):
    hatalar, tuzaklar = beklenen["hatalar"], beklenen["tuzaklar"]
    bulunan = [h for h in hatalar if any(eslesir(b, h) for b in bulgular)]
    tuzak = [b for b in bulgular if any(tuzaga_dustu(b, t) for t in tuzaklar)]
    dogru = [b for b in bulgular if b not in tuzak and any(eslesir(b, h) for h in hatalar)]
    kesin = [b for b in bulgular if b.get("kesinlik") == "kesin"]
    kesin_dogru = [b for b in kesin if b in dogru]
    return {
        "bulma_orani": len(bulunan) / len(hatalar),
        "kesin_dogrulugu": len(kesin_dogru) / len(kesin) if kesin else 1.0,
        "kacirilan": [h["mevcut"] for h in hatalar if h not in bulunan],
        "fazladan": [b.get("mevcut") for b in bulgular if b not in dogru and b not in tuzak],
        "tuzaga_dusen": [b.get("mevcut") for b in tuzak],
    }


def main(argv=None):
    ayr = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ayr.add_argument("dosyalar", nargs="+")
    ayr.add_argument("--beklenen", default=str(VARSAYILAN))
    arg = ayr.parse_args(argv)

    bulgular = []
    for dosya in arg.dosyalar:
        bulgular.extend(json.loads(Path(dosya).read_text(encoding="utf-8")).get("imla", []))
    sonuc = olc(bulgular, json.loads(Path(arg.beklenen).read_text(encoding="utf-8")))

    print(f"Bulma oranı:       %{sonuc['bulma_orani'] * 100:.0f}  (hedef %90)")
    print(f"Kesin doğruluğu:   %{sonuc['kesin_dogrulugu'] * 100:.0f}  (hedef %95)")
    for baslik, anahtar in (("Kaçırılan", "kacirilan"), ("Fazladan", "fazladan"), ("Tuzağa düşen", "tuzaga_dusen")):
        if sonuc[anahtar]:
            print(f"{baslik}: " + ", ".join(sonuc[anahtar]))
    gecti = sonuc["bulma_orani"] >= 0.9 and sonuc["kesin_dogrulugu"] >= 0.95 and not sonuc["tuzaga_dusen"]
    print("Sonuç: " + ("geçti" if gecti else "geçmedi"))
    return 0 if gecti else 1


if __name__ == "__main__":
    sys.exit(main())
