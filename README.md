# Kurgu Yazarlığı Atölyesi

*Editörlük ve Yayın Kurulu*

Türkçe yazan kurgu yazarları için bir Claude eklentisi. Küçürek öykünüzü, kısa öykünüzü ya da roman bölümünüzü TDK'ye göre denetler; her bulguyu metninizden bir alıntıyla gösterir ve bir imla raporu yazar.

**Atölye yazarın yerine yazmaz.** Değerlendirir, gösterir, doğrusunu ve dayandığı kuralı söyler. Düzeltmeleri siz yaparsınız.

> **Durum:** İmla denetimi çalışıyor. Masa (bütün yayın kurulu), Word'de izlenen değişiklik ve yapı haritası yolda.

## Kurulum

Claude Code'da:

```
/plugin marketplace add TheNativeStranger/kurgu-yazarligi-atolyesi
/plugin install atolye@kurgu-yazarligi-atolyesi
```

Açılan ekranda kendiniz için kurmayı seçin. Kurulumdan sonra `/` yazın; listede `/atolye:imla` görünmelidir.

Bilgisayarınızda **Python 3.9 ya da üstü** kurulu olmalı. Terminalde `python3 --version` (Windows'ta `py -3 --version`) bir sürüm göstermiyorsa python.org'dan kurun; Windows'ta kurulumda "Add to PATH" kutusunu işaretleyin.

### Kurulumsuz yol: beceri

Claude uygulamasında ya da claude.ai'de kullanmak için `beceri/kurgu-yazarligi-atolyesi` klasörünü zip olarak sıkıştırın; Ayarlar → Yetenekler (Capabilities) → Beceriler (Skills) → Beceri yükle ile ekleyin. Python gerekmez; denetim sohbette, bölüm bölüm yapılır.

## Kullanım

Eserinizin bulunduğu klasörde Claude'a doğal dille söyleyin: "Şu bölümün imlasına bakar mısın?" Ya da kısayolu kullanın: `/atolye:imla bolum-01.docx`

- **Okunan biçimler:** .docx, .md, .txt. PDF'in metnini editör kendisi çıkarır.
- **.doc, Pages ya da Google Dokümanlar:** Önce .docx olarak kaydedin.

## Ne alırsınız

Eserinizin klasöründe `atolye/raporlar/AAAA-AA-GG-imla.md` adlı bir rapor:

- **Özet:** kaç bulgu var, kaçı kesin hata.
- **Hata türleri:** en sık takıldığınız kurallar, her birinin bir cümlelik açıklamasıyla.
- **Düzeltme tablosu:** yer, mevcut yazım, öneri, kesinlik ve kural.
- **Süreklilik notları** ve redaktörün size soruları.

"Bu bende bilinçli" dediğiniz yazımlar `atolye/yazim-karti.md` dosyasına eklenir ve bir daha sorulmaz. Vazgeçerseniz söylemeniz yeterli.

## Dosyalarınız ve gizlilik

Atölye sizin dosyalarınızı değiştirmez; yazdığı her şey eserinizin klasöründe `atolye/` altında durur. Metniniz Claude tarafından işlenir. Sözlük denetiminde yalnız aranan sözcükler sozluk.gov.tr'ye gönderilir.

## Yol haritası

1. İskelet ve kural dosyaları ✓
2. Hazırlık ve imla ön taraması ✓
3. İmla kipi: editör, redaktör, sözlük ve alıntı doğrulaması ✓
4. Word'de izlenen değişiklik olarak düzeltmeler
5. Masa: okur, editör, gelişim editörü, danışman, dosya okuru ve ajans; yayın yönetmeninin en fazla üç kararı ve tavsiyeleri
6. Görsel pano: Campbell ve Vogler yapı saati, roman haritası, kelime panosu
7. Kabul denemesi ve 1.0.0

## Geliştirenler için

- `scripts/atolye.py`: tek yardımcı betik (hazirla, tara, dogrula, sozluk, rapor); yalnız standart kütüphane.
- `kurallar/tdk.md` ve `kurallar/sik-hatalar.tsv`: redaktörün ve betiğin kuralları. `yapi-sablonlari.md` ve `masa.md` sonraki sürümler içindir.
- Testler: `python3 -m unittest discover tests`
- Redaktörü ölçmek: `tests/metinler/hatali-30.txt` dosyasını boş bir klasöre kopyalayıp orada `/atolye:imla hatali-30.txt` çalıştırın, sonra `python3 tests/olc.py <klasör>/atolye/.calisma/gorusler/*.dogrulanmis.json`. Hedef: bulma en az %90, "kesin" doğruluğu en az %95, tuzaklarda sıfır yanlış alarm.

## Lisans

MIT
