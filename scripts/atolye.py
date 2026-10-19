#!/usr/bin/env python3
"""Kurgu Yazarlığı Atölyesi yardımcı betiği.

Kesin olması gereken işleri yapar: metni çıkarma, bölümleme, paragraf
numaralama, kelime sayma, imla ön taraması, sözlük sorgusu, alıntı
doğrulama ve imla raporu. Yalnız Python standart kütüphanesini kullanır.

Kullanım:
    atolye.py hazirla <dosya>... --calisma <eser>/atolye/.calisma [--kimlik <eser>/atolye/kimlik.md]
    atolye.py tara --calisma <eser>/atolye/.calisma
    atolye.py dogrula --calisma <eser>/atolye/.calisma
    atolye.py sozluk --calisma <eser>/atolye/.calisma
    atolye.py rapor --calisma <eser>/atolye/.calisma --cikti <dosya.md> [--eser <ad>]
"""

import argparse
import datetime
import json
import re
import shutil
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
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
# Bu alt ağaçlardaki metin belgede görünmez: yedek kopya, silinen ve taşınmadan önceki metin.
DOCX_ATLA = {MC + "Fallback", W + "del", W + "moveFrom"}

KELIME = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")

# "BÖLÜM 3", "Bölüm III", "BÖLÜM 3: Kaçış" — sayıdan sonra yalnız boşluk, satır sonu ya da ayraç
BOLUM_DESENLERI = [
    re.compile(r"^b[öo]l[üu]m\s+(\d+|[ivxlc]+)(?=$|\s|[.:\-–—])\s*[.:\-–—]?\s*(.*)$", re.I),
    re.compile(r"^(\d+)\s*\.\s*b[öo]l[üu]m(?=$|\s|[.:\-–—])\s*[.:\-–—]?\s*(.*)$", re.I),
]
# "Birinci Bölüm", "ON İKİNCİ BÖLÜM: Dönüş" (Türkçe küçültülmüş metinde aranır)
SIRALI_BOLUM = re.compile(
    r"^((on|yirmi|otuz|kırk|elli)\s+)?(birinci|ikinci|üçüncü|dördüncü|beşinci|altıncı|yedinci|sekizinci|"
    r"dokuzuncu|onuncu|yirminci|otuzuncu|kırkıncı|ellinci)\s+bölüm\s*[.:\-–—]?\s*(?P<ad>.*)$"
)
# Satırın tamamı bir sayı ya da Roma rakamı: "1", "II.", "— 3 —"
TEK_NUMARA = re.compile(r"^[—–-]?\s*(\d{1,3}|[IVXLC]+)\.?\s*[—–-]?$")
# "1 İstanbul", "2. Vertigo", "10 – Hatırlayış": yalnız kısa ve noktalamasız satırlarda
NUMARALI_BASLIK = re.compile(r"^\s*(\d{1,3})\s*[.:\-–—]?\s+(\S.*)$")
BASLIK_STILLERI = {"heading 1", "heading 2", "title", "başlık 1", "başlık 2", "konu başlığı"}
DESTEKSIZ = {
    ".pdf": "PDF'in metnini okuyup .txt olarak verin.",
    ".doc": "Word'de 'Farklı Kaydet → Word Belgesi (.docx)' ile kaydedin.",
    ".odt": "'Farklı Kaydet → Word Belgesi (.docx)' ile kaydedin.",
    ".rtf": "Word'de 'Farklı Kaydet → Word Belgesi (.docx)' ile kaydedin.",
    ".pages": "Pages'te 'Dosya → Dışa Aktar → Word' ile .docx olarak kaydedin.",
}


class AtolyeHatasi(Exception):
    pass


# Türkçe büyük ve küçük harf

def tr_kucuk(metin):
    """Türkçeye uygun küçültme; uzunluk değişmez (İ→i, I→ı)."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def tr_buyuk(metin):
    return metin.replace("i", "İ").replace("ı", "I").upper()


def oneri_bicimle(gorulen, oneri):
    """Önerinin büyük harflerini görülen metne uydurur."""
    harfler = [h for h in gorulen if h.isalpha()]
    if len(harfler) > 1 and all(h.isupper() for h in harfler):
        return tr_buyuk(oneri)
    if len(gorulen) == len(oneri):
        return "".join(tr_buyuk(h) if gorulen[i].isupper() else h for i, h in enumerate(oneri))
    if gorulen[:1].isupper():
        return tr_buyuk(oneri[:1]) + oneri[1:]
    return oneri


def kelime_say(metin):
    return len(KELIME.findall(metin))


# Kaynak okuma

def metin_oku(yol):
    """Düz metin dosyasını okur: BOM'a göre UTF-8 ya da UTF-16, yoksa UTF-8, olmazsa Windows-1254."""
    ham = yol.read_bytes()
    if ham.startswith(b"\xef\xbb\xbf"):
        return ham[3:].decode("utf-8", errors="replace")
    if ham.startswith((b"\xff\xfe", b"\xfe\xff")):
        return ham.decode("utf-16")
    for kodlama in ("utf-8", "cp1254"):
        try:
            return ham.decode(kodlama)
        except UnicodeDecodeError:
            continue
    raise AtolyeHatasi(f"{yol.name} okunamadı: kodlaması tanınmadı. Word'de 'Düz metin (UTF-8)' olarak kaydedin.")


def paragraflara_bol(satirlar):
    """Satırları paragraflara toplar.

    Word'ün düz metin çıktısında her paragraf tek satırdır; elle sarılmış metinde ise
    paragraflar boş satırla ayrılır. Diyalog çizgisiyle başlayan satır ve bölüm başlığı
    her durumda yeni paragraftır. Satırların iç boşluklarına dokunulmaz.
    """
    satirlar = [s.strip() for s in satirlar]
    dolu = [i for i, s in enumerate(satirlar) if s]
    ara_bos = bool(dolu) and any(not s for s in satirlar[dolu[0]:dolu[-1]])
    satir_satir = not ara_bos or any(len(s) > 100 for s in satirlar)
    paragraflar, birikim = [], []

    def bitir():
        if birikim:
            paragraflar.append(" ".join(birikim))
            birikim.clear()

    for satir in satirlar:
        if not satir:
            bitir()
            continue
        yalniz = satir_satir or baslik_coz(satir, False) is not None
        if yalniz or re.match(r"^(—|–|- )", satir):
            bitir()
        birikim.append(satir)
        if yalniz:
            bitir()
    bitir()
    return paragraflar


def txt_oku(yol):
    return [(p, False, i) for i, p in enumerate(paragraflara_bol(metin_oku(yol).splitlines()))]


def md_oku(yol):
    """# ve ## bölüm başlığıdır; daha derin başlıklar atlanır."""
    sonuc, parca = [], []

    def bosalt():
        for p in paragraflara_bol(parca):
            sonuc.append((p, False, len(sonuc)))
        parca.clear()

    for satir in metin_oku(yol).splitlines():
        m = re.match(r"^\s*(#{1,6})\s+(.*)$", satir)
        if m:
            bosalt()
            if len(m.group(1)) <= 2:
                sonuc.append((m.group(2).strip(), True, len(sonuc)))
            continue
        parca.append(satir)
    bosalt()
    return sonuc


def _docx_ac(yol):
    try:
        zf = zipfile.ZipFile(yol)
        belge = ET.fromstring(zf.read("word/document.xml"))
        return zf, belge
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        raise AtolyeHatasi(f"{yol.name} açılamadı: .docx değil ya da bozuk. Eski .doc ise Word'de .docx olarak kaydedin.")


def _stil_adlari(zf):
    try:
        kok = ET.fromstring(zf.read("word/styles.xml"))
    except (KeyError, ET.ParseError):
        return {}
    return {s.get(W + "styleId"): s.find(W + "name").get(W + "val", "").lower()
            for s in kok.iter(W + "style") if s.find(W + "name") is not None}


def _paragraf_metni(p):
    """Paragrafın görünen metni ve içindeki metin kutuları (ayrı paragraf olarak okunur)."""
    parcalar, kutular = [], []

    def gez(el):
        for c in el:
            if c.tag in DOCX_ATLA:
                continue
            if c.tag == W + "txbxContent":
                kutular.append(c)
                continue
            if c.tag == W + "t":
                parcalar.append(c.text or "")
            elif c.tag == W + "tab":
                parcalar.append("\t")
            elif c.tag in (W + "br", W + "cr"):
                parcalar.append(" ")
            elif c.tag == W + "noBreakHyphen":
                parcalar.append("-")
            gez(c)

    gez(p)
    return "".join(parcalar), kutular


def docx_oku(yol):
    """(metin, başlık mı, sıra) üçlüleri döner."""
    zf, belge = _docx_ac(yol)
    with zf:
        stiller = _stil_adlari(zf)
    satirlar = []

    def baslik_mi(p):
        ppr = p.find(W + "pPr")
        if ppr is None:
            return False
        stil = ppr.find(W + "pStyle")
        seviye = ppr.find(W + "outlineLvl")
        return ((stil is not None and stiller.get(stil.get(W + "val"), "") in BASLIK_STILLERI)
                or (seviye is not None and seviye.get(W + "val") in ("0", "1")))

    def gez(el):
        for c in el:
            if c.tag in DOCX_ATLA:
                continue
            if c.tag == W + "p":
                metin, kutular = _paragraf_metni(c)
                satirlar.append((metin, baslik_mi(c), len(satirlar)))
                for kutu in kutular:
                    gez(kutu)
            else:
                gez(c)

    gez(belge.find(W + "body"))
    return satirlar


def docx_dipnot_say(yol):
    """Okunmayan dipnot ve sonnotların sayısı (ayraç kayıtları hariç)."""
    zf, _ = _docx_ac(yol)
    sayi = 0
    with zf:
        for parca, etiket in (("word/footnotes.xml", "footnote"), ("word/endnotes.xml", "endnote")):
            try:
                kok = ET.fromstring(zf.read(parca))
            except (KeyError, ET.ParseError):
                continue
            sayi += sum(1 for n in kok.iter(W + etiket)
                        if n.get(W + "type") in (None, "normal") and "".join(t.text or "" for t in n.iter(W + "t")).strip())
    return sayi


OKUYUCULAR = {".docx": docx_oku, ".md": md_oku, ".txt": txt_oku}


# Bölümleme

def baslik_coz(metin, stilli):
    """Başlıksa (başlık metni, numaralı mı) döner; değilse None."""
    metin = metin.strip()
    if TEK_NUMARA.match(metin):
        return "", True
    kisa = len(metin.split()) <= 8 and not re.search(r"[.!?…,;]$", metin)
    if kisa:
        for desen in BOLUM_DESENLERI:
            m = desen.match(metin)
            if m:
                return m.group(2).strip(), True
        m = SIRALI_BOLUM.match(tr_kucuk(metin))
        if m:
            return metin[m.start("ad"):].strip(), True
    m = NUMARALI_BASLIK.match(metin)
    if (m and len(metin.split()) <= 6 and m.group(2)[0].isupper()
            and not re.search(r"[.!?…:;,\"“”]$", metin)):
        return m.group(2).strip(), True
    if stilli:
        return metin, False
    return None


def kimlik_turleri(kimlik_yolu):
    """kimlik.md'deki 'Taslak ve not bölümleri' satırı: ({bölüm no: tür}, satır var mı).

    Satır soldan sağa okunur; sayılar ve aralıklar biriktirilir, 'taslak' ya da 'not'
    kelimesine gelince o türe atanır: "3, 5 taslak; 9 not", "2-4 taslak ve 7 not".
    """
    turler = {}
    if not kimlik_yolu or not Path(kimlik_yolu).exists():
        return turler, False
    var = False
    for satir in metin_oku(Path(kimlik_yolu)).splitlines():
        if not tr_kucuk(satir).lstrip("-* ").startswith("taslak ve not"):
            continue
        var = True
        birikim = []
        for m in re.finditer(r"(\d+)\s*(?:[-–—]\s*(\d+))?|(taslak|not)", tr_kucuk(satir.split(":", 1)[-1])):
            if m.group(3):
                turler.update({no: m.group(3) for no in birikim})
                birikim = []
            else:
                birikim.extend(range(int(m.group(1)), int(m.group(2) or m.group(1)) + 1))
    return turler, var


def tur_bul(baslik):
    """Kimlikte bilgi yoksa: yalnız 'Taslak: …' ya da 'Notlar' biçimindeki başlıklar."""
    m = re.match(r"^(taslak|notlar?)\s*([:\-–—]|$)", tr_kucuk(baslik.strip()))
    return ("taslak" if m.group(1) == "taslak" else "not") if m else "duzyazi"


def calisma_temizle(calisma):
    """Önceki okumadan kalan ara dosyaları siler; sözlük önbelleği kalır."""
    for ad in ("metin", "gorusler"):
        if (calisma / ad).exists():
            shutil.rmtree(calisma / ad)
    for ad in ("adaylar.json", "dogrulama.json", "imla.json"):
        (calisma / ad).unlink(missing_ok=True)


def hazirla(dosyalar, calisma, kimlik=None):
    calisma = Path(calisma)
    calisma_temizle(calisma)
    metin_klasoru = calisma / "metin"
    metin_klasoru.mkdir(parents=True)
    (calisma / "gorusler").mkdir()

    kimlikteki_turler, kimlikte_var = kimlik_turleri(kimlik)
    bolumler = []
    paragraf_no = 0
    dipnot = 0

    for dosya_sirasi, dosya in enumerate(dosyalar):
        yol = Path(dosya)
        if not yol.exists():
            raise AtolyeHatasi(f"Dosya bulunamadı: {yol}")
        uzanti = yol.suffix.lower()
        if uzanti in DESTEKSIZ:
            raise AtolyeHatasi(f"{yol.name} doğrudan okunamıyor. {DESTEKSIZ[uzanti]}")
        okuyucu = OKUYUCULAR.get(uzanti)
        if okuyucu is None:
            raise AtolyeHatasi(f"{yol.name}: desteklenmeyen biçim (.docx, .md ya da .txt olmalı).")
        satirlar = okuyucu(yol)
        if uzanti == ".docx":
            dipnot += docx_dipnot_say(yol)

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
                mevcut = {"baslik": "", "dosya": yol.name, "paragraflar": []}
                bolumler.append(mevcut)
            paragraf_no += 1
            mevcut["paragraflar"].append({"p": paragraf_no, "metin": metin, "kaynak": dosya_sirasi, "k": sira})

    # Kitap adı, içindekiler satırı gibi metni olmayan başlıklar bölüm sayılmaz.
    bolumler = [b for b in bolumler if b["paragraflar"]]
    if not bolumler:
        raise AtolyeHatasi("Kaynak dosyalarda metin bulunamadı.")

    ozet = []
    for no, bolum in enumerate(bolumler, start=1):
        tur = kimlikteki_turler.get(no, "duzyazi") if kimlikte_var else tur_bul(bolum["baslik"])
        kelime = sum(kelime_say(p["metin"]) for p in bolum["paragraflar"])
        kayit = {"no": no, "baslik": bolum["baslik"], "tur": tur, "kelime": kelime, "paragraflar": bolum["paragraflar"]}
        (metin_klasoru / f"bolum-{no:02d}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
        ps = bolum["paragraflar"]
        ozet.append({"no": no, "baslik": bolum["baslik"], "tur": tur, "kelime": kelime,
                     "ilk_paragraf": ps[0]["p"], "son_paragraf": ps[-1]["p"], "dosya": bolum["dosya"]})

    eser = {
        "surum": SURUM,
        "kaynaklar": [Path(d).name for d in dosyalar],
        "bolumler": ozet,
        "toplam_kelime": sum(b["kelime"] for b in ozet),
        "duzyazi_kelime": sum(b["kelime"] for b in ozet if b["tur"] == "duzyazi"),
        "paragraf_sayisi": paragraf_no,
        "okunmayan_dipnot": dipnot,
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
    # Kıvrık kesme (’) düz kesme gibi aranır; uzunluk değişmediği için konumlar korunur.
    kucuk = tr_kucuk(metin).replace("’", "'")
    adaylar = []
    for kural in kurallar:
        for m in kural["desen_derli"].finditer(kucuk):
            gorulen = metin[m.start():m.end()]
            oneri = oneri_bicimle(gorulen, m.expand(tr_kucuk(kural["oneri"])))
            if "’" in gorulen:
                oneri = oneri.replace("'", "’")
            adaylar.append({"kural": kural["kural"], "bas": m.start(), "son": m.end(), "gorulen": gorulen,
                            "oneri": oneri, "kesinlik": kural["kesinlik"], "kaynak": "sik-hatalar"})
    for m in re.finditer(r"(\S+) {2,}(\S+)", metin):
        adaylar.append({"kural": "NOK-BOSLUK", "bas": m.start(), "son": m.end(), "gorulen": m.group(),
                        "oneri": f"{m.group(1)} {m.group(2)}", "kesinlik": "kesin", "kaynak": "yerlesik"})
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


def bolumleri_yukle(calisma):
    klasor = Path(calisma) / "metin"
    if not (klasor / "eser.json").exists():
        raise AtolyeHatasi("Önce 'hazirla' çalıştırılmalı: metin/eser.json yok.")
    return [json.loads(d.read_text(encoding="utf-8")) for d in sorted(klasor.glob("bolum-*.json"))]


def tara(calisma, tsv=None):
    calisma = Path(calisma)
    kurallar = sik_hatalari_yukle(tsv)
    tum_paragraflar, adaylar = [], []
    for bolum in bolumleri_yukle(calisma):
        if bolum["tur"] != "duzyazi":
            continue
        for p in bolum["paragraflar"]:
            tum_paragraflar.append((bolum["no"], p))
            for aday in paragraf_tara(p["metin"], kurallar):
                adaylar.append({"bolum": bolum["no"], "paragraf": p["p"], **aday})
    adaylar.extend(_bicim_tutarliligi(tum_paragraflar))
    adaylar.sort(key=lambda a: (a["paragraf"], a["bas"]))
    sonuc = {"surum": SURUM, "adaylar": adaylar, "sayilar": dict(Counter(a["kural"] for a in adaylar))}
    (calisma / "adaylar.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


# Ortak yardımcılar

KESINLIKLER = ("kesin", "buyuk-ihtimal", "tercih")
KESINLIK_ADLARI = {"kesin": "Kesin hata", "buyuk-ihtimal": "Büyük ihtimalle hata", "tercih": "Tercih"}
TIRNAKLAR = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"', "„": '"', "«": '"', "»": '"'})


def esle(metin, bosluk_koru=False):
    """Alıntı karşılaştırması için ortak biçim: NFC, tek tip tırnak, (istenirse) tek boşluk."""
    metin = unicodedata.normalize("NFC", metin or "").translate(TIRNAKLAR).replace("…", "...")
    return metin if bosluk_koru else re.sub(r"\s+", " ", metin).strip()


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


def _govdeler(metin):
    """Kelimelerin kesmeden önceki gövdeleri, Türkçe küçük harfle: "Pîrân'a" → "pîrân"."""
    return [re.split(r"['’]", k)[0] for k in KELIME.findall(tr_kucuk(metin or ""))]


def yazim_karti_ornekleri(yol):
    """yazim-karti.md tablosunun 'Örnek' sütunu: her örnek bir kelime gövdeleri kümesidir."""
    if not yol or not Path(yol).exists():
        return []
    ornekler = []
    satirlar = [s for s in metin_oku(Path(yol)).splitlines() if s.strip().startswith("|")]
    for satir in satirlar[1:]:
        hucreler = [h.strip() for h in satir.strip().strip("|").split("|")]
        if len(hucreler) < 2 or set(hucreler[1]) <= set("-: "):
            continue
        for ornek in hucreler[1].split(","):
            govdeler = set(_govdeler(ornek.strip("`\"“” ")))
            if govdeler:
                ornekler.append(govdeler)
    return ornekler


def kartta_mi(mevcut, oneri, kart):
    """Değişen her kelimenin gövdesi tek bir kart örneğinin kelimeleri arasındaysa True."""
    once, sonra = _govdeler(mevcut), _govdeler(oneri)
    degisen = [g for g in once if g not in sonra] if oneri is not None else once
    return bool(degisen) and any(set(degisen) <= ornek for ornek in kart)


def karar_alintilari(yol):
    if not yol or not Path(yol).exists():
        return []
    return [esle(m.group(1).strip("\"“” "))
            for m in re.finditer(r"^Alıntı:\s*(.+)$", metin_oku(Path(yol)), re.M)]


def _sinirli(alinti, bosluk_koru=False):
    """Kelime ortasından eşleşmeyen arama deseni: "ende", "Bende"nin içinde bulunmaz."""
    aranan = esle(alinti, bosluk_koru)
    if not aranan.strip():
        return None
    return re.compile(r"(?<![^\W_])" + re.escape(aranan) + r"(?![^\W_])")


def paragraflari_yukle(calisma):
    """{paragraf no: (bölüm no, ham metin)}"""
    paragraflar = {}
    for bolum in bolumleri_yukle(calisma):
        for p in bolum["paragraflar"]:
            paragraflar[p["p"]] = (bolum["no"], p["metin"])
    return paragraflar


def yer_bul(alinti, bolum, paragraf, paragraflar, bosluk_koru=False):
    """Alıntının yeri: verilen paragrafta varsa orası; yoksa bölümde, sonra bütün eserde
    yalnız tek bir paragrafta geçiyorsa orası. Bulunamaz ya da birden çok yerdeyse None."""
    desen = _sinirli(alinti, bosluk_koru)
    if desen is None:
        return None

    def var(p):
        return desen.search(esle(paragraflar[p][1], bosluk_koru)) is not None

    if paragraf in paragraflar and var(paragraf):
        return paragraflar[paragraf][0], paragraf
    for kapsam in ([p for p, (b, _) in paragraflar.items() if b == bolum], list(paragraflar)):
        bulunan = [p for p in kapsam if var(p)]
        if len(bulunan) == 1:
            return paragraflar[bulunan[0]][0], bulunan[0]
        if len(bulunan) > 1:
            return None
    return None


def _json_oku(dosya):
    try:
        veri = json.loads(dosya.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AtolyeHatasi(f"{dosya.name} geçerli JSON değil (satır {e.lineno}, sütun {e.colno}): {e.msg}")
    if not isinstance(veri, dict):
        raise AtolyeHatasi(f"{dosya.name}: en dışta bir JSON nesnesi olmalı.")
    for alan in ("imla", "bulgular", "sorular"):
        veri[alan] = veri.get(alan) or []
        if not isinstance(veri[alan], list):
            raise AtolyeHatasi(f"{dosya.name}: '{alan}' bir liste olmalı.")
    return veri


def dogrulanmis_dosyalar(calisma):
    """dogrula'nın bu okumada yazdığı dosyalar (eski okumalardan kalanlar karışmaz)."""
    yol = Path(calisma) / "dogrulama.json"
    if not yol.exists():
        raise AtolyeHatasi("Önce 'dogrula' çalıştırılmalı.")
    adlar = json.loads(yol.read_text(encoding="utf-8"))["dosyalar"]
    return [Path(calisma) / "gorusler" / ad for ad in adlar]


# Alıntı doğrulama ve yazım kartı süzgeci

def dogrula(calisma, atolye=None):
    calisma = Path(calisma)
    atolye = Path(atolye) if atolye else calisma.parent
    paragraflar = paragraflari_yukle(calisma)
    duzyazi = {b["no"] for b in bolumleri_yukle(calisma) if b["tur"] == "duzyazi"}
    kart = yazim_karti_ornekleri(atolye / "yazim-karti.md")
    kararlar = karar_alintilari(atolye / "karar-defteri.md")
    klasor = calisma / "gorusler"
    dosyalar = sorted(d for d in klasor.glob("*.json") if not d.name.endswith(".dogrulanmis.json")) if klasor.exists() else []
    if not dosyalar:
        raise AtolyeHatasi("Doğrulanacak görüş yok: .calisma/gorusler/ boş.")

    sayac = Counter()
    yazilan = []
    for dosya in dosyalar:
        gorus = _json_oku(dosya)

        imla = []
        for bulgu in gorus["imla"]:
            if not isinstance(bulgu, dict):
                sayac["imla_gecersiz"] += 1
                continue
            mevcut, oneri = bulgu.get("mevcut") or "", bulgu.get("oneri")
            if not mevcut.strip() or (oneri is not None and
                                      unicodedata.normalize("NFC", oneri) == unicodedata.normalize("NFC", mevcut)):
                sayac["imla_gecersiz"] += 1
                continue
            if kartta_mi(mevcut, oneri, kart):
                sayac["imla_kart"] += 1
                continue
            # Yalnız boşlukta ayrışan önerilerde (çift boşluk) boşluklar tekleştirilmeden aranır.
            bosluk = oneri is not None and esle(oneri) == esle(mevcut)
            yer = yer_bul(mevcut, bulgu.get("bolum"), bulgu.get("paragraf"), paragraflar, bosluk)
            if yer is None:
                sayac["imla_bulunamadi"] += 1
                continue
            if yer[0] not in duzyazi:
                sayac["imla_taslak"] += 1
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
        for bulgu in gorus["bulgular"]:
            kanitlar = []
            for kanit in (bulgu.get("kanitlar") or []) if isinstance(bulgu, dict) else []:
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
            if any(_karar_kapsar(k, x["alinti"]) for k in kararlar for x in kanitlar):
                bulgu["kapali"] = True
                sayac["bulgu_kapali"] += 1
            bulgular.append(bulgu)
            sayac["bulgu_kalan"] += 1

        gorus["imla"], gorus["bulgular"] = imla, bulgular
        hedef = dosya.with_name(dosya.stem + ".dogrulanmis.json")
        hedef.write_text(json.dumps(gorus, ensure_ascii=False, indent=1), encoding="utf-8")
        yazilan.append(hedef.name)

    sonuc = {"surum": SURUM, "dosyalar": yazilan, "sayilar": dict(sayac)}
    (calisma / "dogrulama.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


def _karar_kapsar(karar, alinti):
    """Karar defterindeki alıntı ile kanıt örtüşüyor mu: kısa olan en az üç kelime ve uzunun içinde."""
    kisa, uzun = sorted((esle(karar), esle(alinti)), key=len)
    desen = _sinirli(kisa)
    return kelime_say(kisa) >= 3 and desen is not None and desen.search(uzun) is not None


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
    Sözlüğe bir kez erişilemezse bu okumada bir daha denenmez; bulgular olduğu gibi kalır.
    """
    calisma = Path(calisma)
    onbellek_yolu = calisma / "sozluk.json"
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    sayac = Counter()
    ag_kullanildi = ag_kapali = False
    for dosya in dogrulanmis_dosyalar(calisma):
        gorus = json.loads(dosya.read_text(encoding="utf-8"))
        for bulgu in gorus.get("imla", []):
            sorgular = bulgu.get("sozluk_sorgu") or []
            if isinstance(sorgular, str):
                sorgular = [sorgular]
            sorgular = [s.strip() for s in sorgular if isinstance(s, str) and s.strip()]
            if not sorgular:
                continue
            durumlar = []
            for kelime in sorgular:
                anahtar = tr_kucuk(kelime)
                if anahtar in onbellek:
                    durum = onbellek[anahtar]
                elif ag_kapali:
                    durum = "erisilemedi"
                else:
                    if ag_kullanildi and bekleme:
                        time.sleep(bekleme)
                    durum = getir(kelime)
                    ag_kullanildi = True
                    if durum == "erisilemedi":
                        ag_kapali = True
                    else:
                        onbellek[anahtar] = durum
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
    """Tablo hücresi: dikey çizgi kaçırılır, çift boşluk görünür olur (␣)."""
    metin = str(metin or "").replace("|", "\\|").replace("\n", " ")
    return re.sub(r" {2,}", lambda m: "␣" * len(m.group()), metin)


def rapor(calisma, cikti, eser_adi=None):
    calisma = Path(calisma)
    eser = json.loads((calisma / "metin" / "eser.json").read_text(encoding="utf-8"))
    dogrulama = json.loads((calisma / "dogrulama.json").read_text(encoding="utf-8")) if (calisma / "dogrulama.json").exists() else {}
    paragraflar = paragraflari_yukle(calisma)
    kurallar = kural_bilgileri()

    imla, surekli, sorular = [], [], []
    for dosya in dogrulanmis_dosyalar(calisma):
        gorus = json.loads(dosya.read_text(encoding="utf-8"))
        imla.extend(gorus.get("imla", []))
        surekli.extend(b for b in gorus.get("bulgular", []) if not b.get("kapali"))
        sorular.extend(gorus.get("sorular", []))

    def okuma_sirasi(b):
        metin = esle(paragraflar.get(b.get("paragraf"), (0, ""))[1])
        return b.get("paragraf") or 0, metin.find(esle(b.get("mevcut")))

    imla.sort(key=okuma_sirasi)
    for sira, bulgu in enumerate(imla, start=1):
        bulgu["id"] = f"R-{sira:03d}"
    (calisma / "imla.json").write_text(json.dumps({"surum": SURUM, "bulgular": imla}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

    kesinlik_sayilari = Counter(b["kesinlik"] for b in imla)
    kural_sayilari = Counter(b.get("kural", "?") for b in imla)
    okunan = [b for b in eser["bolumler"] if b["tur"] == "duzyazi"]
    okunmayan = len(eser["bolumler"]) - len(okunan)

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
    if okunmayan:
        s.append(f"Taslak ya da not olarak işaretli {okunmayan} bölüm denetlenmedi.")
    if eser.get("okunmayan_dipnot"):
        s.append(f"{eser['okunmayan_dipnot']} dipnot denetlenmedi.")
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
                s += [f"> “{kanit['alinti']}” — Bölüm {kanit['bolum']} · ¶{kanit['paragraf']}", ""]
            yollar = bulgu.get("ne_yapabilirsiniz") or []
            if yollar:
                s += ["Ne yapabilirsiniz:", ""] + [f"- {y}" for y in yollar] + [""]

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
    for akim in (sys.stdout, sys.stderr):
        try:
            akim.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ayr = argparse.ArgumentParser(prog="atolye.py", description="Kurgu Yazarlığı Atölyesi yardımcı betiği")
    alt = ayr.add_subparsers(dest="komut", required=True)

    h = alt.add_parser("hazirla", help="Metni çıkarır, bölümler, numaralar ve sayar.")
    h.add_argument("dosyalar", nargs="+")
    h.add_argument("--calisma", required=True)
    h.add_argument("--kimlik", help="Eserin atolye/kimlik.md dosyası (yoksa yok sayılır)")

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
            ek = f" {eser['okunmayan_dipnot']} dipnot denetlenmeyecek." if eser["okunmayan_dipnot"] else ""
            print(f"{len(eser['bolumler'])} bölüm, {eser['paragraf_sayisi']} paragraf, "
                  f"{eser['toplam_kelime']} kelime ({eser['duzyazi_kelime']} düzyazı).{ek}")
        elif arg.komut == "tara":
            print(f"{len(tara(arg.calisma, arg.kurallar)['adaylar'])} aday bulundu.")
        elif arg.komut == "dogrula":
            print(json.dumps(dogrula(arg.calisma, arg.atolye)["sayilar"], ensure_ascii=False))
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
