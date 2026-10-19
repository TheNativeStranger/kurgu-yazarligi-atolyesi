# Kurgu Yazarlığı Atölyesi

*Editörlük ve Yayın Kurulu*

Kurgu Yazarlığı Atölyesi, Türkçe yazan her kurgu yazarına bir yayınevinin editoryal masasını sunan yalın bir Claude eklentisidir. Küçürek öykü, kısa öykü ya da roman: Masa esere göre kurulur, metni okur, TDK'ya göre denetler, yapısını gösterir ve tavsiye verir.

**Atölye yazarın yerine yazmaz.** Değerlendirir, gösterir, yön önerir. Eserin son metni her zaman sizin cümlelerinizdir.

> **Durum: 0.2.0 — imla kipi.** Bu sürümde editör ve redaktör çalışır: Metninizi TDK'ya göre denetler ve bir imla raporu yazar. Masa (bütün kurul), izlenen değişiklikli .docx ve görsel pano sonraki sürümlerde gelecek. Plan aşağıda.

## Kurulum ve komutlar

Eklentinin kısa adı `atolye`'dir. Claude Code'da:

```
/plugin marketplace add TheNativeStranger/kurgu-yazarligi-atolyesi
/plugin install atolye@kurgu-yazarligi-atolyesi
```

Komut yazmak zorunda değilsiniz: "Şu bölüme bir bakar mısın?" demeniz yeterli. Kısayol isteyenler için komutlar:

| Komut | Ne yapar | Durum |
|---|---|---|
| `/atolye:imla` | Yalnız dil ve imla (TDK) | 0.2.0 ✓ |
| `/atolye:masa` | Hepsi: imla, bütün masa, kararlar, tavsiyeler ve pano | planlandı |
| `/atolye:harita` | Yalnız görsel pano, son okumadan | planlandı |

Başka bir eklentide aynı adlı komut yoksa `/imla` yazmak da yeter.

## İmla kipi nasıl çalışır

1. **Hazırlık:** Metin bölümlere ayrılır, paragraflar numaralanır, kelimeler sayılır.
2. **Ön tarama:** Betik sık yazım hatalarını ve tırnak, üç nokta, diyalog biçimi tutarsızlıklarını aday olarak işaretler.
3. **Redaktör:** Metni baştan sona okur; adayları bağlamda değerlendirir, betiğin yakalayamadığı de / da, ki, şapka, büyük harf, noktalama, dil bilgisi ve süreklilik hatalarını ekler.
4. **Doğrulama:** Her bulgunun metinde gerçekten geçtiği denetlenir; geçmeyen düşer. Yazım kartınızdaki tercihlere uyan bulgular gösterilmez.
5. **Sözlük:** Gerekirse doğru biçim Güncel Türkçe Sözlük'te aranır; sözlükte yoksa "kesin" etiketi düşürülür.
6. **Rapor:** `atolye/raporlar/` altına özet, hata türleri ve düzeltme tablosu yazılır. Sohbette yalnız özet gösterilir.

Atölye dosyalarınıza dokunmaz. Her şey eserinizin klasöründe `atolye/` altında durur:

| Dosya | Ne işe yarar |
|---|---|
| `atolye/raporlar/*-imla.md` | İmla raporları |
| `atolye/yazim-karti.md` | Onayladığınız yazım tercihleri ("Bünyamin Pîrân" gibi); bir daha sorulmaz |
| `atolye/kimlik.md` | Eserin adı, türü, karakterleri, taslak bölümleri |
| `atolye/.calisma/` | Ara dosyalar; silinebilir |

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

# Redaktörden sonra: alıntı doğrulama, sözlük, rapor
python3 scripts/atolye.py dogrula --calisma Eserim/atolye/.calisma
python3 scripts/atolye.py sozluk --calisma Eserim/atolye/.calisma
python3 scripts/atolye.py rapor --calisma Eserim/atolye/.calisma --cikti Eserim/atolye/raporlar/imla.md
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

# Redaktörün gerçek çıktısını ölçmek için (30 bilinen hata + tuzaklar):
python3 tests/olc.py <eser>/atolye/.calisma/gorusler/redaktor.json
```

Hedef: bulma oranı en az %90, "kesin" etiketlerinin en az %95'i gerçekten hata, tuzaklarda sıfır yanlış alarm.

## Yol haritası

1. İskelet ve kural dosyaları ✓
2. Hazırlık ve imla ön taraması ✓
3. İmla kipi: editör becerisi, redaktör, sözlük doğrulaması, alıntı doğrulaması ✓
4. İzlenen değişiklikli .docx
5. Masa kipi: diğer koltuklar, yayın yönetmeni, karar defteri, masa raporu
6. Görsel pano: yapı saati, kurul kartları, roman haritası, kelime panosu
7. Kabul denemesi ve 1.0.0

## Lisans

MIT
