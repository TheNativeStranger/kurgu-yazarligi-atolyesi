# Kurgu Yazarlığı Atölyesi

*Editörlük ve Yayın Kurulu*

Kurgu Yazarlığı Atölyesi, Türkçe yazan her kurgu yazarına bir yayınevinin editoryal masasını sunan yalın bir Claude eklentisidir. Küçürek öykü, kısa öykü ya da roman: Masa esere göre kurulur, metni okur, TDK'ya göre denetler, yapısını gösterir ve tavsiye verir.

**Atölye yazarın yerine yazmaz.** Değerlendirir, gösterir, yön önerir. Eserin son metni her zaman sizin cümlelerinizdir.

> **Durum: geliştiriliyor (0.1.0).** Bu sürümde yalnız yardımcı betiğin hazırlık ve imla ön tarama adımları vardır. Editör becerisi, masa ve görsel pano sonraki adımlarda eklenecek. Plan aşağıda.

## Kurulum ve komutlar

Eklentinin kısa adı `atolye`'dir. Claude Code'da:

```
/plugin marketplace add TheNativeStranger/kurgu-yazarligi-atolyesi
/plugin install atolye@kurgu-yazarligi-atolyesi
```

Komut yazmak zorunda değilsiniz: "Şu bölüme bir bakar mısın?" demeniz yeterli. Kısayol isteyenler için üç komut olacak:

| Komut | Ne yapar |
|---|---|
| `/atolye:imla` | Yalnız dil ve imla (TDK) |
| `/atolye:masa` | Hepsi: imla, bütün masa, kararlar, tavsiyeler ve pano |
| `/atolye:harita` | Yalnız görsel pano, son okumadan |

Başka bir eklentide aynı adlı komut yoksa `/imla`, `/masa`, `/harita` yazmak da yeter.

## Masa

| Koltuk | Yalnız bunu yapar | Yapmaz |
|---|---|---|
| **Redaktör ve düzeltmen** (her zaman, ilk) | Yazım, şapka, alıntı kelimeler, ekler ve bağlaçlar, noktalama, dil bilgisi, anlatım bozukluğu, süreklilik | Üsluba karışmaz |
| Editör | Ses, ritim, tekrar, klişe, belirsiz özne | İmla düzeltmez |
| Gelişim editörü | Yapı, karakter, tempo, yapı saati | Satıra inmez |
| Okur | Tepki | Düzeltme önermez |
| Dosya okuru ve ajans | Devamını ister mi, rafı ne, kime uygun | Metne dokunmaz |
| Danışman | Olgu, tarih, kültürel ayrıntı | Dile karışmaz |
| **Yayın yönetmeni** (karar) | Doğrular, en fazla üç karar ve tavsiye verir | Yeni görüş eklemez |

Masa esere göre kurulur: Küçürek öyküde okur, editör ve redaktör; kısa öyküde gelişim editörü de; romanda gerekirse danışman; bitmiş dosyada dosya okuru ve ajans da masaya oturur.

## Çıktılar (planlanan)

- **Dil ve imla raporu:** TDK kuralına dayalı düzeltme tablosu ve Word'de tek tek kabul ya da ret edilen, izlenen değişiklikli bir .docx.
- **Masa raporu:** Koltukların görüşleri, en fazla üç karar ve her karar için "ne yapabilirsiniz".
- **Görsel pano:** Campbell ve Vogler'i iç içe gösteren yapı saati, kurul yorum kartları, roman haritası ve kelime panosu. Tek HTML dosyası, yazdırınca PDF.
- **Yazım kartı ve karar defteri:** Onayladığınız tercihler bir daha hata diye sorulmaz.

## Yardımcı betik

`scripts/atolye.py` yalnız Python 3.9+ standart kütüphanesini kullanır.

```bash
# Metni çıkarır, bölümlere ayırır, paragrafları numaralar, kelimeleri sayar
python3 scripts/atolye.py hazirla bolum-01.docx bolum-02.docx --calisma Eserim/atolye/.calisma

# İmla ön taraması: kurallar/sik-hatalar.tsv ve biçim tutarlılığı
python3 scripts/atolye.py tara --calisma Eserim/atolye/.calisma
```

Ön tarama hüküm vermez, yalnız aday üretir; son kararı redaktör bağlamda verir.

## Kurallar

- `kurallar/tdk.md`: Redaktörün kullandığı TDK kuralları, her biri bir kimlikle.
- `kurallar/sik-hatalar.tsv`: Sık yazım hataları; her satırda desen, kural, öneri, kesinlik ve test örnekleri.
- `kurallar/yapi-sablonlari.md`: Campbell'ın 17 ve Vogler'in 12 aşaması, üç perdeye hizalı.
- `kurallar/masa.md`: Türe göre masa kurma kuralları.

## Testler

```bash
python3 -m unittest discover tests
```

## Yol haritası

1. İskelet ve kural dosyaları ✓
2. Hazırlık ve imla ön taraması ✓
3. İmla kipi: editör becerisi, redaktör, sözlük doğrulaması, alıntı doğrulaması
4. İzlenen değişiklikli .docx
5. Masa kipi: diğer koltuklar, yayın yönetmeni, karar defteri, masa raporu
6. Görsel pano: yapı saati, kurul kartları, roman haritası, kelime panosu
7. Kabul denemesi ve 1.0.0

## Lisans

MIT
