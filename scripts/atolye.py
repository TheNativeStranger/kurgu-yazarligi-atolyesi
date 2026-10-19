#!/usr/bin/env python3
"""Kurgu Yazarlığı Atölyesi yardımcı betiği.

Kesin olması gereken işleri yapar: metni çıkarma, bölümleme, paragraf
numaralama, kelime sayma, imla ön taraması, sözlük sorgusu, alıntı
doğrulama ve imla raporu. Yalnız Python standart kütüphanesini kullanır.

Kullanım:
    atolye.py hazirla <dosya>... --calisma <eser>/atolye/.calisma
    atolye.py tara --calisma <eser>/atolye/.calisma
    atolye.py sozluk --calisma <eser>/atolye/.calisma
    atolye.py dogrula --calisma <eser>/atolye/.calisma [--atolye <eser>/atolye]
    atolye.py rapor --calisma <eser>/atolye/.calisma --cikti <dosya.md>
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
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


# Ortak yardımcılar

KESINLIKLER = ("kesin", "buyuk-ihtimal", "tercih")
KESINLIK_ADLARI = {"kesin": "Kesin hata", "buyuk-ihtimal": "Büyük ihtimalle hata", "tercih": "Tercih"}
TIRNAKLAR = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"', "„": '"', "«": '"', "»": '"'})


def esle(metin):
    """Alıntı karşılaştırması için ortak biçim: NFC, tek tip tırnak, tek boşluk."""
    metin = unicodedata.normalize("NFC", metin or "").translate(TIRNAKLAR).replace("…", "...")
    return re.sub(r"\s+", " ", metin).strip()


def kural_bilgileri():
    """kurallar/tdk.md → {kimlik: {"ad", "kural", "kesinlik"}}"""
    bilgiler = {}
    for blok in re.split(r"^### ", (KURALLAR / "tdk.md").read_text(encoding="utf-8"), flags=re.M)[1:]:
        baslik, _, govde = blok.partition("\n")
        kimlik, _, ad = baslik.partition(" · ")
        kural = re.search(r"^Kural: (.*)$", govde, re.M)
        kesinlik = re.search(r"^Kesinlik: (.*)$", govde, re.M)
        bilgiler[kimlik.strip()] = {
            "ad": ad.strip(),
            "kural": kural.group(1).strip() if kural else "",
            "kesinlik": kesinlik.group(1).strip() if kesinlik else "bağlam",
        }
    return bilgiler


def yazim_karti_ornekleri(yol):
    """yazim-karti.md tablosundaki 'Örnek' sütunu: yazarın onayladığı yazımlar."""
    if not yol or not Path(yol).exists():
        return []
    ornekler = []
    satirlar = [s for s in Path(yol).read_text(encoding="utf-8").splitlines() if s.strip().startswith("|")]
    for satir in satirlar[1:]:
        hucreler = [h.strip() for h in satir.strip().strip("|").split("|")]
        if len(hucreler) < 2 or set(hucreler[1]) <= set("-: "):
            continue
        ornek = hucreler[1].strip("`\"“” ")
        if ornek:
            ornekler.append(esle(ornek))
    return ornekler


def karar_alintilari(yol):
    if not yol or not Path(yol).exists():
        return []
    return [esle(m.group(1).strip("\"“” "))
            for m in re.finditer(r"^Alıntı:\s*(.+)$", Path(yol).read_text(encoding="utf-8"), re.M)]


def paragraflari_yukle(calisma):
    paragraflar = {}
    for dosya in sorted((Path(calisma) / "metin").glob("bolum-*.json")):
        bolum = json.loads(dosya.read_text(encoding="utf-8"))
        for p in bolum["paragraflar"]:
            paragraflar[p["p"]] = (bolum["no"], esle(p["metin"]))
    if not paragraflar:
        raise AtolyeHatasi("Önce 'hazirla' çalıştırılmalı: numaralı metin yok.")
    return paragraflar


def yer_bul(alinti, bolum, paragraf, paragraflar):
    """Alıntıyı önce verilen paragrafta, sonra aynı bölümde, sonra bütün eserde arar."""
    aranan = esle(alinti)
    if not aranan:
        return None
    if paragraf in paragraflar and aranan in paragraflar[paragraf][1]:
        return paragraflar[paragraf][0], paragraf
    for kapsam in (lambda b: b == bolum, lambda b: True):
        for p, (b, metin) in paragraflar.items():
            if kapsam(b) and aranan in metin:
                return b, p
    return None


def gorus_dosyalari(calisma, dogrulanmis=False):
    klasor = Path(calisma) / "gorusler"
    dosyalar = sorted(klasor.glob("*.json")) if klasor.exists() else []
    if dogrulanmis:
        return [d for d in dosyalar if d.name.endswith(".dogrulanmis.json")]
    return [d for d in dosyalar if not d.name.endswith(".dogrulanmis.json")]


# Alıntı doğrulama ve yazım kartı süzgeci

def dogrula(calisma, atolye=None):
    calisma = Path(calisma)
    atolye = Path(atolye) if atolye else calisma.parent
    paragraflar = paragraflari_yukle(calisma)
    kart = yazim_karti_ornekleri(atolye / "yazim-karti.md")
    kararlar = karar_alintilari(atolye / "karar-defteri.md")
    dosyalar = gorus_dosyalari(calisma)
    if not dosyalar:
        raise AtolyeHatasi("Doğrulanacak görüş yok: .calisma/gorusler/ boş.")

    sayac = Counter()
    for dosya in dosyalar:
        gorus = json.loads(dosya.read_text(encoding="utf-8"))

        imla = []
        for bulgu in gorus.get("imla", []):
            mevcut, oneri = bulgu.get("mevcut", ""), bulgu.get("oneri")
            # Boşlukları tekleştirmeden karşılaştır: yalnız çift boşluğu düzelten öneri de geçerlidir.
            if not mevcut or (oneri is not None and unicodedata.normalize("NFC", oneri) == unicodedata.normalize("NFC", mevcut)):
                sayac["imla_gecersiz"] += 1
                continue
            if any(o in esle(mevcut) for o in kart):
                sayac["imla_kart"] += 1
                continue
            yer = yer_bul(mevcut, bulgu.get("bolum"), bulgu.get("paragraf"), paragraflar)
            if yer is None:
                sayac["imla_bulunamadi"] += 1
                continue
            if yer != (bulgu.get("bolum"), bulgu.get("paragraf")):
                sayac["imla_yer_duzeltildi"] += 1
                bulgu["bolum"], bulgu["paragraf"] = yer
            if bulgu.get("kesinlik") not in KESINLIKLER:
                bulgu["kesinlik"] = "buyuk-ihtimal"
            bulgu.setdefault("sozluk", None)
            bulgu.setdefault("docx", None)
            imla.append(bulgu)
            sayac["imla_kalan"] += 1

        bulgular = []
        for bulgu in gorus.get("bulgular", []):
            kanitlar = []
            for kanit in bulgu.get("kanitlar", []):
                yer = yer_bul(kanit.get("alinti", ""), kanit.get("bolum"), kanit.get("paragraf"), paragraflar)
                if yer is None:
                    sayac["kanit_bulunamadi"] += 1
                    continue
                kanit["bolum"], kanit["paragraf"] = yer
                kanitlar.append(kanit)
            if not kanitlar:
                sayac["bulgu_dustu"] += 1
                continue
            bulgu["kanitlar"] = kanitlar
            if any(k and (k in esle(x["alinti"]) or esle(x["alinti"]) in k) for k in kararlar for x in kanitlar):
                bulgu["kapali"] = True
                sayac["bulgu_kapali"] += 1
            bulgular.append(bulgu)
            sayac["bulgu_kalan"] += 1

        gorus["imla"], gorus["bulgular"] = imla, bulgular
        hedef = dosya.with_name(dosya.stem + ".dogrulanmis.json")
        hedef.write_text(json.dumps(gorus, ensure_ascii=False, indent=1), encoding="utf-8")

    sonuc = {"surum": SURUM, "dosyalar": [d.name for d in dosyalar], "sayilar": dict(sayac)}
    (calisma / "dogrulama.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


# Sözlük sorgusu

SOZLUK_ADRESI = "https://sozluk.gov.tr/gts?ara="


def sozlukten_getir(kelime):
    """Güncel Türkçe Sözlük'te kelimeyi arar: 'var', 'yok' ya da 'erisilemedi'."""
    try:
        istek = urllib.request.Request(SOZLUK_ADRESI + urllib.parse.quote(kelime),
                                       headers={"User-Agent": "kurgu-yazarligi-atolyesi"})
        with urllib.request.urlopen(istek, timeout=5) as yanit:
            veri = json.loads(yanit.read().decode("utf-8"))
    except Exception:
        return "erisilemedi"
    if isinstance(veri, list) and veri:
        return "var"
    if isinstance(veri, dict) and "error" in veri:
        return "yok"
    return "erisilemedi"


def sozluk(calisma, getir=sozlukten_getir, bekleme=0.3):
    """Redaktörün 'sozluk_sorgu' alanına yazdığı madde başlarını sözlükte arar.

    Hepsi varsa bulgu doğrulanır; biri yoksa 'kesin' etiketi 'buyuk-ihtimal'e iner.
    Sözlüğe erişilemezse bulgu olduğu gibi kalır ve bu raporda belirtilir.
    """
    calisma = Path(calisma)
    onbellek_yolu = calisma / "sozluk.json"
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    dosyalar = gorus_dosyalari(calisma, dogrulanmis=True)
    if not dosyalar:
        raise AtolyeHatasi("Önce 'dogrula' çalıştırılmalı.")

    sayac = Counter()
    ag_kullanildi = False
    for dosya in dosyalar:
        gorus = json.loads(dosya.read_text(encoding="utf-8"))
        for bulgu in gorus.get("imla", []):
            sorgular = bulgu.get("sozluk_sorgu") or []
            if not sorgular:
                continue
            durumlar = []
            for kelime in sorgular:
                anahtar = tr_kucuk(kelime.strip())
                if anahtar not in onbellek:
                    if ag_kullanildi and bekleme:
                        time.sleep(bekleme)
                    durum = getir(kelime.strip())
                    ag_kullanildi = True
                    if durum != "erisilemedi":
                        onbellek[anahtar] = durum
                else:
                    durum = onbellek[anahtar]
                durumlar.append(durum)
            if "yok" in durumlar:
                bulgu["sozluk"] = "yok"
                if bulgu.get("kesinlik") == "kesin":
                    bulgu["kesinlik"] = "buyuk-ihtimal"
                    sayac["indirildi"] += 1
            elif "erisilemedi" in durumlar:
                bulgu["sozluk"] = "erisilemedi"
            else:
                bulgu["sozluk"] = "var"
            sayac[bulgu["sozluk"]] += 1
        dosya.write_text(json.dumps(gorus, ensure_ascii=False, indent=1), encoding="utf-8")

    onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False, indent=1), encoding="utf-8")
    return dict(sayac)


# İmla raporu

def _hucre(metin):
    return str(metin or "").replace("|", "\\|").replace("\n", " ")


def rapor(calisma, cikti, eser_adi=None):
    calisma = Path(calisma)
    dosyalar = gorus_dosyalari(calisma, dogrulanmis=True)
    if not dosyalar:
        raise AtolyeHatasi("Önce 'dogrula' çalıştırılmalı.")
    eser = json.loads((calisma / "metin" / "eser.json").read_text(encoding="utf-8"))
    dogrulama_yolu = calisma / "dogrulama.json"
    dogrulama = json.loads(dogrulama_yolu.read_text(encoding="utf-8")) if dogrulama_yolu.exists() else {"sayilar": {}}
    kurallar = kural_bilgileri()

    imla, surekli, sorular = [], [], []
    for dosya in dosyalar:
        gorus = json.loads(dosya.read_text(encoding="utf-8"))
        if gorus.get("koltuk") != "redaktor":
            continue
        imla.extend(gorus.get("imla", []))
        surekli.extend(b for b in gorus.get("bulgular", []) if not b.get("kapali"))
        sorular.extend(gorus.get("sorular", []))

    imla.sort(key=lambda b: (b.get("paragraf") or 0, b.get("mevcut", "")))
    for sira, bulgu in enumerate(imla, start=1):
        bulgu["id"] = f"R-{sira:03d}"
    (calisma / "imla.json").write_text(json.dumps({"surum": SURUM, "bulgular": imla}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

    kesinlik_sayilari = Counter(b["kesinlik"] for b in imla)
    kural_sayilari = Counter(b.get("kural", "?") for b in imla)
    okunan = [b for b in eser["bolumler"] if b["tur"] == "duzyazi"]

    s = [f"# Dil ve imla raporu{' — ' + eser_adi if eser_adi else ''}", ""]
    s.append(f"{datetime.date.today().isoformat()} · Kaynak: {', '.join(eser['kaynaklar'])} · "
             f"{len(okunan)} bölüm, {eser['duzyazi_kelime']} kelime düzyazı")
    s += ["", "## Özet", ""]
    if imla:
        s.append(f"{len(imla)} bulgu: {kesinlik_sayilari['kesin']} kesin hata, "
                 f"{kesinlik_sayilari['buyuk-ihtimal']} büyük ihtimalle hata, {kesinlik_sayilari['tercih']} tercih.")
    else:
        s.append("Yazım ve noktalama bulgusu yok.")
    sayilar = dogrulama.get("sayilar", {})
    if sayilar.get("imla_kart"):
        s.append(f"Yazım kartınızdaki tercihlere uyan {sayilar['imla_kart']} bulgu gösterilmedi.")
    dusen = sayilar.get("imla_bulunamadi", 0) + sayilar.get("bulgu_dustu", 0)
    if dusen:
        s.append(f"Metinde yeri doğrulanamayan {dusen} bulgu rapordan çıkarıldı.")
    erisilemedi = sum(1 for b in imla if b.get("sozluk") == "erisilemedi")
    if erisilemedi:
        s.append(f"{erisilemedi} bulgu için sözlüğe erişilemedi; bunlar sözlükle doğrulanmadı.")

    if imla:
        s += ["", "## Hata türleri", "", "| Kural | Sayı | Ne diyor |", "| --- | --- | --- |"]
        for kimlik, sayi in kural_sayilari.most_common():
            bilgi = kurallar.get(kimlik, {"ad": kimlik, "kural": ""})
            s.append(f"| {_hucre(bilgi['ad'])} | {sayi} | {_hucre(bilgi['kural'])} |")

        s += ["", "## Düzeltmeler", "",
              "| # | Yer | Mevcut | Öneri | Kesinlik | Kural | Not |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for bulgu in imla:
            bilgi = kurallar.get(bulgu.get("kural"), {"ad": bulgu.get("kural", "")})
            oneri = bulgu.get("oneri")
            s.append(
                f"| {bulgu['id']} | Bölüm {bulgu.get('bolum')} · ¶{bulgu.get('paragraf')} | {_hucre(bulgu['mevcut'])} | "
                f"{_hucre(oneri) if oneri is not None else '—'} | {KESINLIK_ADLARI[bulgu['kesinlik']]} | "
                f"{_hucre(bilgi['ad'])} | {_hucre(bulgu.get('aciklama'))} |"
            )

    if surekli:
        s += ["", "## Süreklilik", ""]
        for bulgu in surekli:
            s += [f"### {bulgu.get('baslik', 'Süreklilik')}", "", bulgu.get("aciklama", ""), ""]
            for kanit in bulgu["kanitlar"]:
                s.append(f"> “{kanit['alinti']}” — Bölüm {kanit['bolum']} · ¶{kanit['paragraf']}")
                s.append("")

    if sorular:
        s += ["", "## Size sorular", ""]
        s += [f"- {soru if isinstance(soru, str) else soru.get('soru', '')}" for soru in sorular]

    s += ["", "---", "",
          "Öneriler TDK Yazım Kılavuzu'na ve Güncel Türkçe Sözlük'e dayanır. Son karar sizindir: "
          "Bir tercihi kalıcı yapmak için yazım kartınıza ekleyin, bir daha sorulmaz."]
    cikti = Path(cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text("\n".join(s) + "\n", encoding="utf-8")
    return {"bulgu": len(imla), **{k: kesinlik_sayilari[k] for k in KESINLIKLER}, "sureklilik": len(surekli)}


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

    d = alt.add_parser("dogrula", help="Alıntıları kaynakta arar, yazım kartı ve karar defteri süzgecini uygular.")
    d.add_argument("--calisma", required=True)
    d.add_argument("--atolye", help="Eserin atolye/ klasörü (varsayılan: --calisma'nın bir üstü)")

    s = alt.add_parser("sozluk", help="Redaktörün istediği madde başlarını Güncel Türkçe Sözlük'te arar.")
    s.add_argument("--calisma", required=True)

    r = alt.add_parser("rapor", help="Doğrulanmış redaktör görüşünden imla raporu yazar.")
    r.add_argument("--calisma", required=True)
    r.add_argument("--cikti", required=True, help="Raporun yazılacağı .md dosyası")
    r.add_argument("--eser", help="Eserin adı")

    arg = ayr.parse_args(argv)
    try:
        if arg.komut == "hazirla":
            eser = hazirla(arg.dosyalar, arg.calisma, arg.kimlik)
            print(f"{len(eser['bolumler'])} bölüm, {eser['paragraf_sayisi']} paragraf, "
                  f"{eser['toplam_kelime']} kelime ({eser['duzyazi_kelime']} düzyazı).")
        elif arg.komut == "tara":
            sonuc = tara(arg.calisma, arg.kurallar)
            print(f"{len(sonuc['adaylar'])} aday bulundu.")
        elif arg.komut == "dogrula":
            sonuc = dogrula(arg.calisma, arg.atolye)
            print(json.dumps(sonuc["sayilar"], ensure_ascii=False))
        elif arg.komut == "sozluk":
            print(json.dumps(sozluk(arg.calisma), ensure_ascii=False))
        elif arg.komut == "rapor":
            sonuc = rapor(arg.calisma, arg.cikti, arg.eser)
            print(f"{sonuc['bulgu']} bulgu ({sonuc['kesin']} kesin, {sonuc['buyuk-ihtimal']} büyük ihtimal, "
                  f"{sonuc['tercih']} tercih) → {arg.cikti}")
    except AtolyeHatasi as hata:
        print(f"Hata: {hata}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
