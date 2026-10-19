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
        self.assertEqual(atolye.oneri_bicimle("İnşaallah", "inşallah"), "İnşallah")
        self.assertEqual(atolye.oneri_bicimle("TDK'nın", "tdk'nin"), "TDK'nin")


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


class KuralBilgileri(unittest.TestCase):
    def test_her_kuralin_adi_ve_kesinligi_var(self):
        bilgiler = atolye.kural_bilgileri()
        self.assertGreaterEqual(len(bilgiler), 30)
        for kimlik, bilgi in bilgiler.items():
            self.assertTrue(bilgi["ad"] and bilgi["kural"], kimlik)
            self.assertIn(bilgi["kesinlik"], {"bağlamdan bağımsız", "bağlam"}, kimlik)

    def test_esle_tirnak_ve_bosluk(self):
        self.assertEqual(atolye.esle("“Gel,”  dedi…  Ahmet’in"), '"Gel," dedi... Ahmet\'in')


BEKLENEN = json.loads((METINLER / "hatali-30.beklenen.json").read_text(encoding="utf-8"))


class ImlaAkisi(unittest.TestCase):
    """hazirla → redaktör (burada elle yazılmış kusursuz bir görüş) → dogrula → sozluk → rapor"""

    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.atolye = Path(self.gecici.name) / "atolye"
        self.calisma = self.atolye / ".calisma"
        atolye.hazirla([METINLER / "hatali-30.txt"], self.calisma)
        self.paragraflar = atolye.paragraflari_yukle(self.calisma)

    def tearDown(self):
        self.gecici.cleanup()

    def yer(self, metin):
        return next((b, p) for p, (b, m) in self.paragraflar.items() if atolye.esle(metin, True) in atolye.esle(m, True))

    def kusursuz_gorus(self, ekler=(), bulgular=()):
        imla = []
        for hata in BEKLENEN["hatalar"]:
            bolum, paragraf = self.yer(hata["mevcut"])
            imla.append({**hata, "bolum": bolum, "paragraf": paragraf, "aciklama": "Açıklama | çizgili.",
                         "kesinlik": "kesin", "sozluk_sorgu": []})
        gorus = {"koltuk": "redaktor", "durum": "incelendi", "ozet": "Deneme.",
                 "imla": imla + list(ekler), "bulgular": list(bulgular), "sorular": ["Gelicem bilinçli mi?"]}
        (self.calisma / "gorusler" / "redaktor.json").write_text(json.dumps(gorus, ensure_ascii=False), encoding="utf-8")
        return gorus

    def test_dogrula_alintilari_ve_suzgeci(self):
        (self.atolye / "yazim-karti.md").write_text(
            "# Yazım kartı\n\n| Tercih | Örnek | Not |\n| --- | --- | --- |\n| Ağız | Gelicem | bilinçli |\n",
            encoding="utf-8")
        (self.atolye / "karar-defteri.md").write_text(
            "## 2026-10-19 · Teyze\nKarar: Kalsın.\nAlıntı: “Kapıda komşumuz göründü.”\n", encoding="utf-8")
        yanlis_yer = {"kural": "YAZ-SOZCUK", "bolum": 1, "paragraf": 1, "mevcut": "Malesef bedeni",
                      "oneri": "Maalesef bedeni", "kesinlik": "kesin"}
        self.kusursuz_gorus(
            ekler=[
                yanlis_yer,
                {"kural": "YAZ-SOZCUK", "bolum": 1, "paragraf": 1, "mevcut": "uydurma cümle", "oneri": "x", "kesinlik": "kesin"},
                {"kural": "YAZ-SOZCUK", "bolum": 1, "paragraf": 2, "mevcut": "Gelicem dedim", "oneri": "Geleceğim dedim",
                 "kesinlik": "kesin"},
                {"kural": "YAZ-SOZCUK", "bolum": 1, "paragraf": 2, "mevcut": "Herkez", "oneri": "Herkez", "kesinlik": "kesin"},
            ],
            bulgular=[
                {"baslik": "Uydurma", "kanitlar": [{"alinti": "Böyle bir cümle yok.", "bolum": 1, "paragraf": 1}]},
                {"baslik": "Kapalı", "kanitlar": [{"alinti": "Kapıda komşumuz göründü.", "bolum": 1, "paragraf": 99}]},
            ],
        )
        sayilar = atolye.dogrula(self.calisma)["sayilar"]
        self.assertEqual(sayilar["imla_kalan"], 31)
        self.assertEqual(sayilar["imla_bulunamadi"], 1)
        self.assertEqual(sayilar["imla_kart"], 1)
        self.assertEqual(sayilar["imla_gecersiz"], 1)
        self.assertGreaterEqual(sayilar["imla_yer_duzeltildi"], 1)
        self.assertEqual((sayilar["bulgu_dustu"], sayilar["bulgu_kalan"], sayilar["bulgu_kapali"]), (1, 1, 1))
        dogrulanmis = json.loads((self.calisma / "gorusler" / "redaktor.dogrulanmis.json").read_text(encoding="utf-8"))
        tasinan = next(b for b in dogrulanmis["imla"] if b["mevcut"] == "Malesef bedeni")
        self.assertEqual((tasinan["bolum"], tasinan["paragraf"]), self.yer("Malesef bedeni"))
        self.assertEqual(dogrulanmis["bulgular"][0]["kanitlar"][0]["paragraf"], self.yer("Kapıda komşumuz göründü.")[1])

    def test_sozluk_kesinligi_dusurur_ve_onbellege_alir(self):
        gorus = self.kusursuz_gorus()
        sorgular = {"İnşaallah": ["inşallah"], "kağıt": ["kâğıt"], "Selamün aleyküm": ["selamünaleyküm"]}
        for bulgu in gorus["imla"]:
            bulgu["sozluk_sorgu"] = sorgular.get(bulgu["mevcut"], [])
        (self.calisma / "gorusler" / "redaktor.json").write_text(json.dumps(gorus, ensure_ascii=False), encoding="utf-8")
        atolye.dogrula(self.calisma)

        cagrilar = []
        cevaplar = {"inşallah": "var", "selamünaleyküm": "yok", "kâğıt": "erisilemedi"}

        def sahte(kelime):
            cagrilar.append(kelime)
            return cevaplar[kelime]

        sayilar = atolye.sozluk(self.calisma, getir=sahte, bekleme=0)
        self.assertEqual(sayilar, {"var": 1, "yok": 1, "erisilemedi": 1, "indirildi": 1})
        imla = {b["mevcut"]: b for b in json.loads(
            (self.calisma / "gorusler" / "redaktor.dogrulanmis.json").read_text(encoding="utf-8"))["imla"]}
        self.assertEqual(imla["Selamün aleyküm"]["kesinlik"], "buyuk-ihtimal")
        self.assertEqual(imla["kağıt"]["kesinlik"], "kesin")
        # Erişilemeyen kelime önbelleğe girmez, bulunanlar girer.
        atolye.sozluk(self.calisma, getir=sahte, bekleme=0)
        self.assertEqual(sorted(cagrilar), ["inşallah", "kâğıt", "kâğıt", "selamünaleyküm"])

    def test_rapor(self):
        self.kusursuz_gorus(bulgular=[{"baslik": "Saat çelişkisi", "aciklama": "Aynı sabah.",
                                       "kanitlar": [{"alinti": "Herkez o sabah erken kalkmıştı.", "bolum": 1, "paragraf": 1}]}])
        atolye.dogrula(self.calisma)
        cikti = self.atolye / "raporlar" / "imla.md"
        sonuc = atolye.rapor(self.calisma, cikti, "Deneme")
        self.assertEqual((sonuc["bulgu"], sonuc["kesin"], sonuc["sureklilik"]), (30, 30, 1))
        metin = cikti.read_text(encoding="utf-8")
        self.assertIn("30 bulgu: 30 kesin hata", metin)
        self.assertIn("Hitaptan sonra virgül", metin)
        self.assertIn("Açıklama \\| çizgili.", metin)
        self.assertIn("## Süreklilik", metin)
        self.assertIn("## Size sorular", metin)
        self.assertEqual(len(re.findall(r"^\| R-\d{3} \|", metin, re.M)), 30)
        imla = json.loads((self.calisma / "imla.json").read_text(encoding="utf-8"))["bulgular"]
        self.assertEqual([b["id"] for b in imla][:2], ["R-001", "R-002"])

    def test_komut_satiri(self):
        self.assertEqual(atolye.main(["dogrula", "--calisma", str(self.calisma)]), 1)
        self.kusursuz_gorus()
        self.assertEqual(atolye.main(["dogrula", "--calisma", str(self.calisma)]), 0)
        self.assertEqual(atolye.main(["rapor", "--calisma", str(self.calisma),
                                      "--cikti", str(self.atolye / "r.md")]), 0)


class Olcum(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(KOK / "tests"))
        import olc
        self.olc = olc

    def test_kusursuz_redaktor_gecer(self):
        bulgular = [{**h, "kesinlik": "kesin"} for h in BEKLENEN["hatalar"]]
        sonuc = self.olc.olc(bulgular, BEKLENEN)
        self.assertEqual((sonuc["bulma_orani"], sonuc["kesin_dogrulugu"]), (1.0, 1.0))
        self.assertFalse(sonuc["tuzaga_dusen"])

    def test_tuzak_ve_kacirilan(self):
        bulgular = [{**h, "kesinlik": "kesin"} for h in BEKLENEN["hatalar"][:20]]
        bulgular.append({"mevcut": "Bende kalsın", "oneri": "Ben de kalsın", "kesinlik": "kesin"})
        sonuc = self.olc.olc(bulgular, BEKLENEN)
        self.assertAlmostEqual(sonuc["bulma_orani"], 20 / 30)
        self.assertEqual(sonuc["tuzaga_dusen"], ["Bende kalsın"])
        self.assertAlmostEqual(sonuc["kesin_dogrulugu"], 20 / 21)

    def test_on_tarama_tuzaklara_dusmez(self):
        """Betik taraması hatali-30 metnindeki tuzakları yakalamamalı."""
        metin = (METINLER / "hatali-30.txt").read_text(encoding="utf-8")
        adaylar = atolye.paragraf_tara(metin, atolye.sik_hatalari_yukle())
        for tuzak in BEKLENEN["tuzaklar"]:
            yakalanan = [a for a in adaylar if a["gorulen"].strip() and atolye.esle(a["gorulen"]) in atolye.esle(tuzak)]
            self.assertFalse(yakalanan, tuzak)



class GozdenGecirmeDuzeltmeleri(unittest.TestCase):
    """Gözden geçirmede bulunan hataların geri gelmemesi için."""

    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.dizin = Path(self.gecici.name)

    def tearDown(self):
        self.gecici.cleanup()

    def test_word_duz_metni_sahneleri_birlestirmez(self):
        uzun = "Kapıyı kapattı ve mutfağa geçti; tencerenin kapağını kaldırıp uzun uzun baktı, sonra hiçbir şey söylemeden çıktı."
        kaynak = self.dizin / "a.txt"
        kaynak.write_text(f"BÖLÜM 1\n— Geldin mi, dedi annem.\n{uzun}\n\nErtesi sabah yağmur yağıyordu.\n", encoding="utf-8")
        eser = atolye.hazirla([kaynak], self.dizin / "c")
        self.assertEqual(eser["paragraf_sayisi"], 3)

    def test_baslik_desenleri(self):
        for metin in ["BİRİNCİ BÖLÜM", "On İkinci Bölüm", "II", "— 3 —", "1"]:
            self.assertIsNotNone(atolye.baslik_coz(metin, False), metin)
        for metin in ["Bölüm 2'deki hemşire bana baktı ve güldü.", "Bölüm 3 kapanınca bütün hastalar bahçeye çıkarıldı, kimse bilmiyordu."]:
            self.assertIsNone(atolye.baslik_coz(metin, False), metin)

    def test_bom_ve_windows_kodlamasi_ve_bozuk_docx(self):
        (self.dizin / "bom.md").write_bytes("\ufeff# Başlık\n\nMetin burada.\n".encode("utf-8"))
        self.assertEqual(atolye.hazirla([self.dizin / "bom.md"], self.dizin / "c")["bolumler"][0]["baslik"], "Başlık")
        (self.dizin / "ansi.txt").write_bytes("Çocuk ağladı.".encode("cp1254"))
        self.assertEqual(atolye.hazirla([self.dizin / "ansi.txt"], self.dizin / "c")["toplam_kelime"], 2)
        (self.dizin / "bozuk.docx").write_text("x", encoding="utf-8")
        with self.assertRaises(atolye.AtolyeHatasi):
            atolye.hazirla([self.dizin / "bozuk.docx"], self.dizin / "c")

    def test_yer_bul_kelime_siniri_ve_belirsizlik(self):
        paragraflar = {1: (1, "Bende gelirim."), 2: (1, "Bende kalsın."), 3: (1, "Halası geldi.")}
        self.assertIsNone(atolye.yer_bul("ende", 1, 9, paragraflar))
        self.assertIsNone(atolye.yer_bul("Bende", 1, 9, paragraflar))
        self.assertEqual(atolye.yer_bul("Bende", 1, 2, paragraflar), (1, 2))
        self.assertIsNone(atolye.yer_bul("hala", 1, 9, paragraflar))

    def test_yazim_karti_kelime_duzeyinde(self):
        kart = [{"bünyamin", "pîrân"}, {"bi"}]
        self.assertTrue(atolye.kartta_mi("Pîrân'a kimse", "Piran'a kimse", kart))
        self.assertFalse(atolye.kartta_mi("bir kaç dakika", "birkaç dakika", kart))

    def test_koltuk_adi_rapordan_bulgu_dusurmez(self):
        kaynak = self.dizin / "a.txt"
        kaynak.write_text("Herkez geldi.", encoding="utf-8")
        calisma = self.dizin / "atolye" / ".calisma"
        atolye.hazirla([kaynak], calisma)
        (calisma / "gorusler" / "redaktor.json").write_text(json.dumps({"koltuk": "redaktör", "imla": [
            {"kural": "YAZ-SOZCUK", "bolum": 1, "paragraf": 1, "mevcut": "Herkez", "oneri": "Herkes", "kesinlik": "kesin"}]}),
            encoding="utf-8")
        atolye.dogrula(calisma)
        self.assertEqual(atolye.rapor(calisma, self.dizin / "r.md")["bulgu"], 1)
        # Yeniden hazırlık eski görüşleri temizler.
        atolye.hazirla([kaynak], calisma)
        self.assertEqual(list((calisma / "gorusler").iterdir()), [])

    def test_kivrik_kesme_ve_buyuk_harf_onerisi(self):
        kurallar = atolye.sik_hatalari_yukle()
        self.assertEqual([a["oneri"] for a in atolye.paragraf_tara("Türkçe’de böyle.", kurallar)], ["Türkçede"])
        self.assertEqual([a["oneri"] for a in atolye.paragraf_tara("HERŞEY BİTTİ", kurallar)], ["HER ŞEY"])
        self.assertEqual(atolye.paragraf_tara("Bir kaçak yakalandı.", kurallar), [])

class KomutSatiri(unittest.TestCase):
    def test_hata_kodu(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(atolye.main(["tara", "--calisma", d]), 1)
            self.assertEqual(atolye.main(["hazirla", str(METINLER / "kucurek.txt"), "--calisma", d]), 0)
            self.assertEqual(atolye.main(["tara", "--calisma", d]), 0)


if __name__ == "__main__":
    unittest.main()
