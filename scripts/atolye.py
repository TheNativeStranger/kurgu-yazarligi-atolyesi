#!/usr/bin/env python3
"""Kurgu Yazarlığı Atölyesi yardımcı betiği.

Kesin olması gereken işleri yapar: metni çıkarma, bölümleme, paragraf
numaralama, kelime sayma ve imla ön taraması. Yalnız Python standart
kütüphanesini kullanır.

Kullanım:
    atolye.py hazirla <dosya>... --calisma <eser>/atolye/.calisma
    atolye.py tara --calisma <eser>/atolye/.calisma
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

SURUM = 1
KOK = Path(__file__).resolve().parent.parent
KURALLAR = KOK / "kurallar"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

KELIME = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")

BOLUM_DESENLERI = [
    # "BÖLÜM 3", "Bölüm III", "BÖLÜM 3: Kaçış"
    re.compile(r"^\s*b[öo]l[üu]m\s+(\d+|[ivxlc]+)\b\s*[.:\-–—]?\s*(.*)$", re.I),
    # "3. Bölüm", "3. Bölüm: Kaçış"
    re.compile(r"^\s*(\d+)\s*\.\s*b[öo]l[üu]m\b\s*[.:\-–—]?\s*(.*)$", re.I),
]
# "1 İstanbul", "2. Vertigo", "10 – Hatırlayış": yalnız kısa ve noktalamasız satırlarda
NUMARALI_BASLIK = re.compile(r"^\s*(\d{1,3})\s*[.:\-–—]?\s+(\S.*)$")
BASLIK_STILLERI = {"heading 1", "heading 2", "title", "başlık 1", "başlık 2", "konu başlığı"}


class AtolyeHatasi(Exception):
    pass


# Türkçe büyük ve küçük harf

def tr_kucuk(metin):
    """Türkçeye uygun küçültme; uzunluk değişmez (İ→i, I→ı)."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def tr_buyuk_harf(harf):
    return {"i": "İ", "ı": "I"}.get(harf, harf.upper())


def harf_durumunu_tasi(kaynak, hedef):
    """Kaynakta büyük olan konumları hedefte de büyütür."""
    return "".join(
        tr_buyuk_harf(h) if i < len(kaynak) and kaynak[i].isupper() else h
        for i, h in enumerate(hedef)
    )


def kelime_say(metin):
    return len(KELIME.findall(metin))


# Kaynak okuma

def _stil_adlari(zf):
    try:
        kok = ET.fromstring(zf.read("word/styles.xml"))
    except KeyError:
        return {}
    adlar = {}
    for stil in kok.iter(W + "style"):
        ad = stil.find(W + "name")
        if ad is not None:
            adlar[stil.get(W + "styleId")] = ad.get(W + "val", "").lower()
    return adlar


def _paragraf_metni(p):
    parcalar = []
    for el in p.iter():
        if el.tag == W + "t":
            parcalar.append(el.text or "")
        elif el.tag == W + "tab":
            parcalar.append("\t")
        elif el.tag in (W + "br", W + "cr"):
            parcalar.append(" ")
    return "".join(parcalar)


def docx_oku(yol):
    """(metin, baslik_mi, kaynak_sirasi) üçlüleri döner."""
    with zipfile.ZipFile(yol) as zf:
        try:
            belge = ET.fromstring(zf.read("word/document.xml"))
        except KeyError:
            raise AtolyeHatasi(f"{yol.name} geçerli bir .docx değil: word/document.xml yok.")
        stiller = _stil_adlari(zf)
    govde = belge.find(W + "body")
    satirlar = []
    for sira, p in enumerate(govde.iter(W + "p")):
        ppr = p.find(W + "pPr")
        baslik = False
        if ppr is not None:
            stil = ppr.find(W + "pStyle")
            if stil is not None and stiller.get(stil.get(W + "val"), "") in BASLIK_STILLERI:
                baslik = True
            seviye = ppr.find(W + "outlineLvl")
            if seviye is not None and seviye.get(W + "val") in ("0", "1"):
                baslik = True
        satirlar.append((_paragraf_metni(p), baslik, sira))
    return satirlar


def md_oku(yol):
    satirlar = []
    paragraf = []
    for sira, satir in enumerate(yol.read_text(encoding="utf-8").splitlines()):
        m = re.match(r"^(#{1,2})\s+(.*)$", satir)
        if m:
            if paragraf:
                satirlar.append((" ".join(paragraf), False, sira))
                paragraf = []
            satirlar.append((m.group(2), True, sira))
        elif satir.strip():
            paragraf.append(satir.strip())
        elif paragraf:
            satirlar.append((" ".join(paragraf), False, sira))
            paragraf = []
    if paragraf:
        satirlar.append((" ".join(paragraf), False, sira))
    return satirlar


def txt_oku(yol):
    metin = yol.read_text(encoding="utf-8")
    # Boş satırla ayrılmışsa paragraf boş satırdır; değilse her satır bir paragraftır.
    if re.search(r"\n\s*\n", metin):
        bloklar = re.split(r"\n\s*\n", metin)
        return [(" ".join(b.split()), False, i) for i, b in enumerate(bloklar)]
    return [(s, False, i) for i, s in enumerate(metin.splitlines())]


def pdf_oku(yol):
    if not shutil.which("pdftotext"):
        raise AtolyeHatasi(
            f"{yol.name} bir PDF. Önce metnini çıkarıp .txt olarak verin "
            "(Claude'un okuma aracıyla ya da pdftotext ile)."
        )
    sonuc = subprocess.run(["pdftotext", "-layout", str(yol), "-"], capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise AtolyeHatasi(f"{yol.name} okunamadı: {sonuc.stderr.strip()}")
    return [(" ".join(b.split()), False, i) for i, b in enumerate(re.split(r"\n\s*\n", sonuc.stdout))]


OKUYUCULAR = {".docx": docx_oku, ".md": md_oku, ".txt": txt_oku, ".pdf": pdf_oku}


# Bölümleme

def baslik_coz(metin, stilli):
    """Başlıksa (baslik, numara_var_mi) döner; değilse None."""
    metin = metin.strip()
    for desen in BOLUM_DESENLERI:
        m = desen.match(metin)
        if m:
            return m.group(2).strip(), True
    m = NUMARALI_BASLIK.match(metin)
    if (m and len(metin.split()) <= 6 and m.group(2)[0].isupper()
            and not re.search(r"[.!?…:;,\"“”]$", metin)):
        return m.group(2).strip(), True
    if stilli:
        return metin, False
    return None


def kimlik_turleri(kimlik_yolu):
    """kimlik.md'deki 'Taslak ve not bölümleri' satırından {bolum_no: tur} çıkarır."""
    turler = {}
    if not kimlik_yolu or not kimlik_yolu.exists():
        return turler
    for satir in kimlik_yolu.read_text(encoding="utf-8").splitlines():
        if not tr_kucuk(satir).lstrip("- ").startswith("taslak ve not"):
            continue
        deger = satir.split(":", 1)[-1]
        for parca in re.split(r"[;,]", deger):
            m = re.search(r"(\d+)\s*(?:[-–—]\s*(\d+))?\s*(taslak|not)", tr_kucuk(parca))
            if m:
                bas, son = int(m.group(1)), int(m.group(2) or m.group(1))
                for no in range(bas, son + 1):
                    turler[no] = m.group(3)
    return turler


def tur_bul(baslik):
    kucuk = tr_kucuk(baslik)
    if re.search(r"\btaslak\b", kucuk):
        return "taslak"
    if re.search(r"\bnot(lar|ları)?\b", kucuk):
        return "not"
    return "duzyazi"


def hazirla(dosyalar, calisma, kimlik=None):
    calisma = Path(calisma)
    metin_klasoru = calisma / "metin"
    if metin_klasoru.exists():
        shutil.rmtree(metin_klasoru)
    metin_klasoru.mkdir(parents=True)

    kimlikteki_turler = kimlik_turleri(Path(kimlik) if kimlik else None)
    bolumler = []
    paragraf_no = 0

    for dosya_sirasi, dosya in enumerate(dosyalar):
        yol = Path(dosya)
        if not yol.exists():
            raise AtolyeHatasi(f"Dosya bulunamadı: {yol}")
        okuyucu = OKUYUCULAR.get(yol.suffix.lower())
        if okuyucu is None:
            raise AtolyeHatasi(f"{yol.name}: desteklenmeyen biçim (.docx, .md, .txt ya da .pdf olmalı).")
        satirlar = okuyucu(yol)

        mevcut = None
        for metin, stilli, sira in satirlar:
            metin = unicodedata.normalize("NFC", metin).strip()
            if not metin:
                continue
            baslik = baslik_coz(metin, stilli)
            if baslik is not None:
                mevcut = {"baslik": baslik[0], "dosya": yol.name, "paragraflar": []}
                bolumler.append(mevcut)
                continue
            if mevcut is None:
                # Başlıksız dosya ya da ilk başlıktan önceki metin
                mevcut = {"baslik": "", "dosya": yol.name, "paragraflar": [], "basliksiz": True}
                bolumler.append(mevcut)
            paragraf_no += 1
            mevcut["paragraflar"].append({"p": paragraf_no, "metin": metin, "kaynak": dosya_sirasi, "k": sira})

    bolumler = [b for b in bolumler if b["paragraflar"] or b["baslik"]]
    if not bolumler:
        raise AtolyeHatasi("Kaynak dosyalarda metin bulunamadı.")

    ozet = []
    for no, bolum in enumerate(bolumler, start=1):
        tur = kimlikteki_turler.get(no) or tur_bul(bolum["baslik"])
        kelime = sum(kelime_say(p["metin"]) for p in bolum["paragraflar"])
        kayit = {
            "no": no,
            "baslik": bolum["baslik"],
            "tur": tur,
            "kelime": kelime,
            "paragraflar": bolum["paragraflar"],
        }
        (metin_klasoru / f"bolum-{no:02d}.json").write_text(
            json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        ps = bolum["paragraflar"]
        ozet.append({
            "no": no,
            "baslik": bolum["baslik"],
            "tur": tur,
            "kelime": kelime,
            "ilk_paragraf": ps[0]["p"] if ps else None,
            "son_paragraf": ps[-1]["p"] if ps else None,
            "dosya": bolum["dosya"],
        })

    eser = {
        "surum": SURUM,
        "kaynaklar": [Path(d).name for d in dosyalar],
        "bolumler": ozet,
        "toplam_kelime": sum(b["kelime"] for b in ozet),
        "duzyazi_kelime": sum(b["kelime"] for b in ozet if b["tur"] == "duzyazi"),
        "paragraf_sayisi": paragraf_no,
    }
    (metin_klasoru / "eser.json").write_text(json.dumps(eser, ensure_ascii=False, indent=1), encoding="utf-8")
    return eser


# İmla ön taraması

def sik_hatalari_yukle(yol=None):
    yol = Path(yol) if yol else KURALLAR / "sik-hatalar.tsv"
    kurallar = []
    satirlar = yol.read_text(encoding="utf-8").splitlines()
    basliklar = satirlar[0].split("\t")
    for satir_no, satir in enumerate(satirlar[1:], start=2):
        if not satir.strip() or satir.startswith("#"):
            continue
        alanlar = dict(zip(basliklar, satir.split("\t")))
        try:
            alanlar["desen_derli"] = re.compile(tr_kucuk(alanlar["desen"]))
        except re.error as hata:
            raise AtolyeHatasi(f"sik-hatalar.tsv satır {satir_no}: geçersiz desen ({hata}).")
        kurallar.append(alanlar)
    return kurallar


def paragraf_tara(metin, kurallar):
    kucuk = tr_kucuk(metin)
    adaylar = []
    for kural in kurallar:
        for m in kural["desen_derli"].finditer(kucuk):
            gorulen = metin[m.start():m.end()]
            adaylar.append({
                "kural": kural["kural"],
                "bas": m.start(),
                "son": m.end(),
                "gorulen": gorulen,
                "oneri": harf_durumunu_tasi(gorulen, m.expand(tr_kucuk(kural["oneri"]))),
                "kesinlik": kural["kesinlik"],
                "kaynak": "sik-hatalar",
            })
    for m in re.finditer(r"(?<=\S) {2,}(?=\S)", metin):
        adaylar.append({
            "kural": "NOK-BOSLUK", "bas": m.start(), "son": m.end(), "gorulen": m.group(),
            "oneri": " ", "kesinlik": "kesin", "kaynak": "yerlesik",
        })
    return adaylar


def _bicim_tutarliligi(paragraflar):
    """Eser boyunca karışık kullanılan tırnak, üç nokta ve diyalog biçimlerini bulur."""
    bicimler = {
        "NOK-TIRNAK": {"düz tırnak": re.compile(r'"'), "kıvrık tırnak": re.compile(r"[“”]")},
        "NOK-UC-NOKTA": {"…": re.compile(r"…"), "...": re.compile(r"(?<!\.)\.\.\.(?!\.)")},
        "NOK-KONUSMA-CIZGISI": {
            "uzun çizgi": re.compile(r"^—"),
            "kısa çizgi": re.compile(r"^[-–]\s"),
            "tırnak": re.compile(r'^["“]'),
        },
    }
    adaylar = []
    for kural, secenekler in bicimler.items():
        yerler = {ad: [] for ad in secenekler}
        for bolum_no, p in paragraflar:
            for ad, desen in secenekler.items():
                for m in desen.finditer(p["metin"]):
                    yerler[ad].append((bolum_no, p, m))
        kullanilan = {ad: y for ad, y in yerler.items() if y}
        if len(kullanilan) < 2:
            continue
        cogunluk = max(kullanilan, key=lambda ad: len(kullanilan[ad]))
        for ad, liste in kullanilan.items():
            if ad == cogunluk:
                continue
            for bolum_no, p, m in liste:
                adaylar.append({
                    "kural": kural, "bolum": bolum_no, "paragraf": p["p"],
                    "bas": m.start(), "son": m.end(), "gorulen": m.group(),
                    "oneri": None, "kesinlik": "tercih", "kaynak": "yerlesik",
                    "not": f"Eserde çoğunlukla {cogunluk} kullanılmış; burada {ad}.",
                })
    return adaylar


def tara(calisma, tsv=None):
    calisma = Path(calisma)
    metin_klasoru = calisma / "metin"
    if not (metin_klasoru / "eser.json").exists():
        raise AtolyeHatasi("Önce 'hazirla' çalıştırılmalı: metin/eser.json yok.")
    kurallar = sik_hatalari_yukle(tsv)
    tum_paragraflar = []
    adaylar = []
    for dosya in sorted(metin_klasoru.glob("bolum-*.json")):
        bolum = json.loads(dosya.read_text(encoding="utf-8"))
        for p in bolum["paragraflar"]:
            tum_paragraflar.append((bolum["no"], p))
            for aday in paragraf_tara(p["metin"], kurallar):
                adaylar.append({"bolum": bolum["no"], "paragraf": p["p"], **aday})
    adaylar.extend(_bicim_tutarliligi(tum_paragraflar))
    adaylar.sort(key=lambda a: (a["paragraf"], a["bas"]))
    sonuc = {
        "surum": SURUM,
        "adaylar": adaylar,
        "sayilar": dict(Counter(a["kural"] for a in adaylar)),
    }
    (calisma / "adaylar.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


# Komut satırı

def main(argv=None):
    ayr = argparse.ArgumentParser(prog="atolye.py", description="Kurgu Yazarlığı Atölyesi yardımcı betiği")
    alt = ayr.add_subparsers(dest="komut", required=True)

    h = alt.add_parser("hazirla", help="Metni çıkarır, bölümler, numaralar ve sayar.")
    h.add_argument("dosyalar", nargs="+")
    h.add_argument("--calisma", required=True)
    h.add_argument("--kimlik", help="Eserin atolye/kimlik.md dosyası")

    t = alt.add_parser("tara", help="İmla ön taraması: aday listesi üretir.")
    t.add_argument("--calisma", required=True)
    t.add_argument("--kurallar", help="Başka bir sik-hatalar.tsv")

    arg = ayr.parse_args(argv)
    try:
        if arg.komut == "hazirla":
            eser = hazirla(arg.dosyalar, arg.calisma, arg.kimlik)
            print(f"{len(eser['bolumler'])} bölüm, {eser['paragraf_sayisi']} paragraf, "
                  f"{eser['toplam_kelime']} kelime ({eser['duzyazi_kelime']} düzyazı).")
        elif arg.komut == "tara":
            sonuc = tara(arg.calisma, arg.kurallar)
            print(f"{len(sonuc['adaylar'])} aday bulundu.")
    except AtolyeHatasi as hata:
        print(f"Hata: {hata}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
