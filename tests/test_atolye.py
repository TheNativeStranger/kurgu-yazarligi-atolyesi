"""atolye.py testleri. Çalıştırma: python3 -m unittest discover tests"""

import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

import atolye  # noqa: E402

METINLER = Path(__file__).resolve().parent / "metinler"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx_yaz(yol, paragraflar):
    """Küçük bir .docx üretir. paragraflar: (metin, stil_kimligi ya da None) listesi."""
    govde = []
    for metin, stil in paragraflar:
        ppr = f'<w:pPr><w:pStyle w:val="{stil}"/></w:pPr>' if stil else ""
        govde.append(f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{metin}</w:t></w:r></w:p>')
    belge = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             f'<w:document xmlns:w="{W_NS}"><w:body>{"".join(govde)}</w:body></w:document>')
    # Türkçe Word'de "Başlık 1" stilinin kimliği "Balk1"dir; adı yine "heading 1" olarak saklanır.
    stiller = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               f'<w:styles xmlns:w="{W_NS}">'
               f'<w:style w:type="paragraph" w:styleId="Balk1"><w:name w:val="heading 1"/></w:style>'
               f'<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
               f'</w:styles>')
    with zipfile.ZipFile(yol, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", belge)
        zf.writestr("word/styles.xml", stiller)


class KelimeSayma(unittest.TestCase):
    def test_kesme_ve_tire_tek_kelime(self):
        self.assertEqual(atolye.kelime_say("İstanbul'da göz-göze geldiler."), 3)

    def test_kivrik_kesme(self):
        self.assertEqual(atolye.kelime_say("Ahmet’in evi"), 2)

    def test_noktalama_sayilmaz(self):
        self.assertEqual(atolye.kelime_say("— Evet, dedi… ve gitti!"), 4)


class TurkceHarf(unittest.TestCase):
    def test_kucultme_uzunlugu_korur(self):
        for metin in ["İnşaallah", "IŞIK", "Iğdır İzmir"]:
            self.assertEqual(len(atolye.tr_kucuk(metin)), len(metin))
        self.assertEqual(atolye.tr_kucuk("IŞIK İzmir"), "ışık izmir")

    def test_harf_durumu_tasinir(self):
        self.assertEqual(atolye.harf_durumunu_tasi("İnşaallah", "inşallah"), "İnşallah")
        self.assertEqual(atolye.harf_durumunu_tasi("TDK'nın", "tdk'nin"), "TDK'nin")


class Hazirla(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.dizin = Path(self.gecici.name)

    def tearDown(self):
        self.gecici.cleanup()

    def bolum(self, no):
        return json.loads((self.dizin / "calisma" / "metin" / f"bolum-{no:02d}.json").read_text(encoding="utf-8"))

    def test_docx_baslik_stili_ve_numaralama(self):
        roman = self.dizin / "roman.docx"
        docx_yaz(roman, [
            ("Roman Adı", None),
            ("İstanbul", "Balk1"),
            ("Sabah erkenden uyandı.", None),
            ("", None),
            ("Kapıyı açtı ve çıktı.", None),
            ("Vertigo", "Balk1"),
            ("Başı döndü.", None),
            ("Taslak: Kayboluş", "Balk1"),
            ("Henüz yazılmadı.", None),
        ])
        eser = atolye.hazirla([roman], self.dizin / "calisma")
        basliklar = [b["baslik"] for b in eser["bolumler"]]
        self.assertEqual(basliklar, ["", "İstanbul", "Vertigo", "Taslak: Kayboluş"])
        self.assertEqual(eser["bolumler"][3]["tur"], "taslak")
        # Paragraflar eser boyunca tek sırayla numaralanır; boş paragraf atlanır, başlık sayılmaz.
        self.assertEqual([p["p"] for p in self.bolum(2)["paragraflar"]], [2, 3])
        self.assertEqual(self.bolum(3)["paragraflar"][0]["p"], 4)
        self.assertEqual(eser["toplam_kelime"], 2 + 3 + 4 + 2 + 2)
        self.assertEqual(eser["duzyazi_kelime"], 2 + 3 + 4 + 2)

    def test_docx_kaynak_sirasi_tutulur(self):
        roman = self.dizin / "roman.docx"
        docx_yaz(roman, [("Bir", "Balk1"), ("", None), ("Birinci paragraf.", None)])
        atolye.hazirla([roman], self.dizin / "calisma")
        self.assertEqual(self.bolum(1)["paragraflar"][0]["k"], 2)

    def test_markdown_baslik(self):
        eser = atolye.hazirla([METINLER / "oyku.md"], self.dizin / "calisma")
        self.assertEqual(len(eser["bolumler"]), 1)
        self.assertEqual(eser["bolumler"][0]["baslik"], "Saat Tamircisi")
        self.assertEqual(eser["toplam_kelime"], 130)

    def test_txt_basliksiz_tek_bolum(self):
        eser = atolye.hazirla([METINLER / "kucurek.txt"], self.dizin / "calisma")
        self.assertEqual(len(eser["bolumler"]), 1)
        self.assertEqual(eser["paragraf_sayisi"], 3)
        self.assertLess(eser["toplam_kelime"], 500)

    def test_metin_icindeki_bolum_desenleri(self):
        kaynak = self.dizin / "roman.txt"
        kaynak.write_text(
            "BÖLÜM 1\n\nİlk satır.\n\n2. Bölüm: Kaçış\n\nİkinci satır.\n\n"
            "3 kişi geldi\n\n10 Hatırlayış\n\nSon satır.\n",
            encoding="utf-8",
        )
        eser = atolye.hazirla([kaynak], self.dizin / "calisma")
        self.assertEqual([b["baslik"] for b in eser["bolumler"]], ["", "Kaçış", "Hatırlayış"])
        # "3 kişi geldi" küçük harfle başladığı için başlık sayılmaz.
        self.assertEqual(eser["bolumler"][1]["kelime"], 2 + 3)

    def test_kimlikteki_taslak_ve_not(self):
        kaynak = self.dizin / "roman.md"
        kaynak.write_text("# Bir\n\nMetin.\n\n# İki\n\nMetin.\n\n# Üç\n\nMetin.\n", encoding="utf-8")
        kimlik = self.dizin / "kimlik.md"
        kimlik.write_text("- Ad: Deneme\n- Taslak ve not bölümleri: 2 taslak; 3 not\n", encoding="utf-8")
        eser = atolye.hazirla([kaynak], self.dizin / "calisma", kimlik)
        self.assertEqual([b["tur"] for b in eser["bolumler"]], ["duzyazi", "taslak", "not"])
        self.assertEqual(eser["duzyazi_kelime"], 1)

    def test_desteklenmeyen_bicim(self):
        kaynak = self.dizin / "roman.odt"
        kaynak.write_text("x", encoding="utf-8")
        with self.assertRaises(atolye.AtolyeHatasi):
            atolye.hazirla([kaynak], self.dizin / "calisma")


class SikHatalar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kurallar = atolye.sik_hatalari_yukle()

    def test_kurallar_tdk_md_icinde_tanimli(self):
        tanimli = set(re.findall(r"^### ([A-Z0-9-]+) ·", (KOK / "kurallar" / "tdk.md").read_text(encoding="utf-8"), re.M))
        for kural in self.kurallar:
            self.assertIn(kural["kural"], tanimli, kural["desen"])

    def test_kesinlik_degerleri(self):
        for kural in self.kurallar:
            self.assertIn(kural["kesinlik"], {"kesin", "buyuk-ihtimal", "tercih"}, kural["desen"])

    def test_her_desen_ornegini_yakalar_ve_dogruyu_yakalamaz(self):
        for kural in self.kurallar:
            with self.subTest(desen=kural["desen"]):
                yakalanan = [a for a in atolye.paragraf_tara(kural["yakalar"], [kural])]
                self.assertTrue(yakalanan, f"yakalamadı: {kural['yakalar']}")
                self.assertFalse(atolye.paragraf_tara(kural["yakalamaz"], [kural]),
                                 f"yanlış alarm: {kural['yakalamaz']}")

    def test_oneri_uygulaninca_hata_kalmaz(self):
        for kural in self.kurallar:
            with self.subTest(desen=kural["desen"]):
                metin = kural["yakalar"]
                for aday in sorted(atolye.paragraf_tara(metin, [kural]), key=lambda a: -a["bas"]):
                    metin = metin[:aday["bas"]] + aday["oneri"] + metin[aday["son"]:]
                self.assertFalse(atolye.paragraf_tara(metin, [kural]), metin)

    def test_temiz_metinlerde_aday_yok(self):
        for dosya in ["kucurek.txt", "oyku.md"]:
            metin = (METINLER / dosya).read_text(encoding="utf-8")
            self.assertEqual(atolye.paragraf_tara(metin, self.kurallar), [], dosya)


class Tara(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.dizin = Path(self.gecici.name)

    def tearDown(self):
        self.gecici.cleanup()

    def test_hazirlanmadan_taranamaz(self):
        with self.assertRaises(atolye.AtolyeHatasi):
            atolye.tara(self.dizin / "calisma")

    def test_adaylar_ve_bicim_tutarliligi(self):
        kaynak = self.dizin / "oyku.md"
        kaynak.write_text(
            "# Deneme\n\n"
            "— Herşey yolunda mı, dedi.\n\n"
            "— Evet… Ama  yarın konuşalım.\n\n"
            "- Peki, dedi.\n\n"
            "“Gel,” dedi annesi.\n",
            encoding="utf-8",
        )
        atolye.hazirla([kaynak], self.dizin / "calisma")
        sonuc = atolye.tara(self.dizin / "calisma")
        kurallar = [a["kural"] for a in sonuc["adaylar"]]
        self.assertIn("YAZ-BITISIK", kurallar)
        self.assertIn("NOK-BOSLUK", kurallar)
        self.assertIn("NOK-KONUSMA-CIZGISI", kurallar)
        cizgi = [a for a in sonuc["adaylar"] if a["kural"] == "NOK-KONUSMA-CIZGISI"]
        self.assertTrue(all(a["kesinlik"] == "tercih" for a in cizgi))
        # Çoğunluk uzun çizgi; kısa çizgi ve tırnaklı diyalog işaretlenir.
        self.assertEqual(sorted(a["paragraf"] for a in cizgi), [3, 4])
        herşey = next(a for a in sonuc["adaylar"] if a["kural"] == "YAZ-BITISIK")
        self.assertEqual((herşey["bolum"], herşey["paragraf"], herşey["oneri"]), (1, 1, "Her şey"))
        self.assertTrue((self.dizin / "calisma" / "adaylar.json").exists())


class KomutSatiri(unittest.TestCase):
    def test_hata_kodu(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(atolye.main(["tara", "--calisma", d]), 1)
            self.assertEqual(atolye.main(["hazirla", str(METINLER / "kucurek.txt"), "--calisma", d]), 0)
            self.assertEqual(atolye.main(["tara", "--calisma", d]), 0)


if __name__ == "__main__":
    unittest.main()
