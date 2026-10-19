# TDK kuralları

Redaktörün ve `atolye.py`'nin ortak başvurusu. Her kural bir kimlik, bir ad ve dört satırdan oluşur. Kaynak, TDK Yazım Kılavuzu ve Güncel Türkçe Sözlük'tür (sozluk.gov.tr). Bir kurala emin olunamıyorsa kesin gibi sunulmaz; yazar TDK'nin kendi kaynağına yönlendirilir.

Kesinlik satırı iki değer alır:

- **bağlamdan bağımsız:** Kural metnin anlamına bakmadan uygulanabilir. Bulgu "kesin" etiketi alabilir.
- **bağlam:** Kuralın uygulanıp uygulanmayacağı cümlenin anlamına bağlıdır. Bulgu en fazla "büyük ihtimalle hata" olur; yorum payı varsa "tercih".

Kimlik önekleri: `YAZ` yazım, `NOK` noktalama, `DIL` dil bilgisi ve anlatım, `SUR` süreklilik.

## Yazım

### YAZ-SOZCUK · Sözcüğün sözlükteki yazımı
Kural: Sözcükler Güncel Türkçe Sözlük'teki biçimleriyle yazılır.
Doğru / yanlış: "herkes, yalnız, yanlış, şoför, sürpriz" / "herkez, yanlız, yalnış, şöför, süpriz"
Kaynak: Güncel Türkçe Sözlük
Kesinlik: bağlamdan bağımsız

### YAZ-DE-DA · Bağlaç "de / da"
Kural: Bağlaç olan "de / da" ayrı yazılır ve ünlü uyumuna uyar; "te / ta" biçimi yoktur. Bulunma hâli eki "-de / -da / -te / -ta" ise bitişik yazılır.
Doğru / yanlış: "Ben de geldim. Evde kaldım." / "Bende geldim. Ev de kaldım."
Kaynak: Yazım Kılavuzu, Bazı Kelimelerin ve Eklerin Yazılışı, "de" bağlacı
Kesinlik: bağlam

### YAZ-KI · Bağlaç "ki" ve "-ki" eki
Kural: Bağlaç olan "ki" ayrı yazılır. İlgi zamiri ve sıfat yapan "-ki" eki bitişik yazılır. Kalıplaşmış "belki, çünkü, sanki, oysaki, mademki, hâlbuki, meğerki" bitişiktir.
Doğru / yanlış: "Bilmiyordu ki gelecek. Evdeki kitap." / "Bilmiyorduki gelecek. Evde ki kitap."
Kaynak: Yazım Kılavuzu, Bazı Kelimelerin ve Eklerin Yazılışı, "ki" bağlacı ve "-ki" eki
Kesinlik: bağlam

### YAZ-MI · Soru eki "mi"
Kural: Soru eki "mı, mi, mu, mü" ayrı yazılır, ünlü uyumuna uyar; kendisinden sonra gelen ekler ona bitişik yazılır.
Doğru / yanlış: "Geldin mi? Okur musun? Öyle mi?" / "Geldinmi? Okurmusun? Öylemi?"
Kaynak: Yazım Kılavuzu, Bazı Kelimelerin ve Eklerin Yazılışı, soru eki
Kesinlik: bağlamdan bağımsız

### YAZ-BITISIK · Bitişik ve ayrı yazılan kelimeler
Kural: "her şey, bir şey, hiç kimse, her biri, bir gün, her zaman, bir kez, yanı sıra" ayrı; "hiçbir, birkaç, birçok, herhangi, herhâlde" bitişik yazılır. Soru cümlesinde "hiç" "bir kez olsun" anlamındaysa "bir"den ayrı yazılır (Hiç bir kitap okudun mu?).
Doğru / yanlış: "her şey, hiçbir şey, birkaç gün" / "herşey, hiç bir şey, bir kaç gün"
Kaynak: Yazım Kılavuzu, Birleşik Kelimelerin Yazılışı; Güncel Türkçe Sözlük
Kesinlik: bağlamdan bağımsız

### YAZ-SAPKA · Düzeltme işareti (şapka)
Kural: Şapka yalnız şu durumlarda kullanılır: yazılışları aynı, anlamları ve okunuşları farklı kelimeleri ayırmak için (hâlâ / hala, âlem / alem, âdet / adet); alıntı kelimelerde ince "g, k" ünsüzlerinden sonraki "a, u" ünlülerinde (kâğıt, dükkân, rüzgâr, mekân); nispet "-î"sinde (millî, dinî, resmî); kişi ve yer adlarında ince "l"den sonra gelen "a, u" ünlülerinde (Lâle, Halûk, Nalân, Selânik).
Doğru / yanlış: "Hâlâ bekliyor. Kâğıdı aldı. Millî maç." / "Hala bekliyor (hâlâ anlamında). Kağıdı aldı. Milli maç."
Kaynak: Yazım Kılavuzu, Düzeltme İşareti
Kesinlik: bağlam

### YAZ-ALINTI · Alıntı kelimeler ve kalıp sözler
Kural: Arapça, Farsça, Kürtçe ve Batı kökenli kelimeler ile kalıplaşmış dua ve selamlaşma sözleri sözlükteki biçimleriyle yazılır. Diyalogdaki bilinçli ağız biçimleri ve başka dilde yazılmış replikler bu kuralın dışındadır.
Doğru / yanlış: "selamünaleyküm, aleykümselam, inşallah, maşallah" / "selamün aleyküm, aleyküm selam, inşaallah, maşaallah"
Kaynak: Güncel Türkçe Sözlük
Kesinlik: bağlamdan bağımsız

### YAZ-BUYUK · Büyük harfler
Kural: Cümle ve özel adlar büyük harfle başlar. Unvan ve saygı sözleri özel adla birlikte büyük harfle başlar (Ali Bey, Ayşe Hanım). Akrabalık adları addan sonra kullanıldığında küçük harfle yazılır (Fahreddin abi, Ayşe teyze); adın önünde lakap olarak kullanıldığında büyük harfle başlar (Dayı Kemal). Ay ve gün adları belirli bir tarih bildirmiyorsa küçük harfle başlar.
Doğru / yanlış: "Ayşe Hanım, Fahreddin abi, 19 Ekim 2026, ekim ayında" / "ayşe hanım, Fahreddin Abi, Ekim ayında"
Kaynak: Yazım Kılavuzu, Büyük Harflerin Kullanıldığı Yerler
Kesinlik: bağlam

### YAZ-KESME · Kesme işareti
Kural: Özel adlara getirilen çekim ekleri kesmeyle ayrılır (İstanbul'da, Ahmet'in); kitap ve eser adlarına gelen ekler de öyle (Çalıkuşu'nu). Kurum, kuruluş, kurul ve iş yeri adlarına gelen ekler kesmeyle ayrılmaz (Türk Dil Kurumunun). Dil adlarına gelen ekler kesmesizdir (Türkçede); bu kısım bağlamdan bağımsızdır. Yapım ekleri kesmeyle ayrılmaz (İstanbullu).
Doğru / yanlış: "İstanbul'da, Türkçede, İstanbullu" / "İstanbulda, Türkçe'de, İstanbul'lu"
Kaynak: Yazım Kılavuzu, Kesme İşareti
Kesinlik: bağlam

### YAZ-SAYI · Sayıların yazımı
Kural: Edebî metinlerde sayılar genellikle yazıyla yazılır. Tarih, saat ve ölçü gibi kesinlik isteyen yerlerde rakam kullanılabilir; seçim eser boyunca tutarlı olmalıdır.
Doğru / yanlış: "otuz dört e-posta" / "34 e-posta" (edebî metinde)
Kaynak: Yazım Kılavuzu, Sayıların Yazılışı
Kesinlik: bağlam

### YAZ-KISALTMA · Kısaltmalara gelen ekler
Kural: Kısaltmalara getirilen ekler kesmeyle ayrılır ve kısaltmanın okunuşuna uyar.
Doğru / yanlış: "TDK'nin, NATO'ya, THY'de" / "TDK'nın, NATO'ye"
Kaynak: Yazım Kılavuzu, Kısaltmalar
Kesinlik: bağlamdan bağımsız

## Noktalama

### NOK-VIRGUL-HITAP · Hitaptan sonra virgül
Kural: Hitap sözü cümlenin geri kalanından virgülle ayrılır.
Doğru / yanlış: "Yakında terfi alıyorum, abi." / "Yakında terfi alıyorum abi."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Virgül
Kesinlik: bağlam

### NOK-VIRGUL-SIRALI · Eş görevli kelimeler arasında virgül
Kural: Birbiri ardınca sıralanan eş görevli kelime ve kelime grupları virgülle ayrılır; son ikisi arasında "ve" varsa virgül konmaz.
Doğru / yanlış: "Ev, okul ve iş." / "Ev okul ve iş."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Virgül
Kesinlik: bağlam

### NOK-VIRGUL-ZARF-FIIL · Zarf-fiil grubundan sonra virgül
Kural: Metin içinde zarf-fiil eki almış kelimeden sonra virgül konmaz. Art arda gelen zarf-fiil eki almış kelimelerden sonra virgül konur (Bir karara varıp, arkadaşına bakarak konuştu).
Doğru / yanlış: "Sunumunu yaparken sen bu işin hiçbir yerinde yoktun." / "Sunumunu yaparken, sen bu işin hiçbir yerinde yoktun."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Virgül
Kesinlik: bağlam

### NOK-VIRGUL-DE-DA · Tekrarlı bağlaçlarda virgül
Kural: Tekrarlı bağlaçlar (hem ... hem, ne ... ne, de ... de) arasına ve bağlama görevindeki "de / da"dan sonra virgül konmaz. Ara sözü ayıran virgüller bu kuralın dışındadır (Ben de, açıkçası, bilmiyorum).
Doğru / yanlış: "İşlerimizden de performansımızdan da onlar sorumlu." / "İşlerimizden de, performansımızdan da, onlar sorumlu."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Virgül
Kesinlik: bağlam

### NOK-NOKTALI-VIRGUL · Noktalı virgül
Kural: Ögeleri arasında virgül bulunan sıralı cümleleri ya da tür bakımından ayrılan grupları ayırmak için noktalı virgül kullanılır.
Doğru / yanlış: "Kırmızı, beyaz güller; mor, sarı menekşeler." / "Kırmızı, beyaz güller, mor, sarı menekşeler."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Noktalı Virgül
Kesinlik: bağlam

### NOK-IKI-NOKTA · İki nokta
Kural: İki noktadan sonra gelen cümle büyük harfle başlar; cümle niteliği taşımayan açıklama ve sıralamalar küçük harfle başlar.
Doğru / yanlış: "Şunu söyledi: Yarın gelirim." / "Şunu söyledi: yarın gelirim."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, İki Nokta
Kesinlik: bağlam

### NOK-UC-NOKTA · Üç nokta
Kural: Tamamlanmamış cümle ve anlatımın sonunda üç nokta kullanılır. Üç noktanın biçimi ("…" tek karakter ya da "..." üç nokta) eser boyunca aynı olmalıdır.
Doğru / yanlış: Eser boyunca tek biçim / Aynı eserde "…" ve "..." birlikte
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Üç Nokta (işaretin kullanımı); tek biçim şartı editoryaldir, TDK kuralı değildir
Kesinlik: bağlam

### NOK-TIRNAK · Tırnak işareti
Kural: Başkasından aktarılan söz tırnak içinde verilir. Tırnağın biçimi (düz ya da kıvrık) eser boyunca aynı olmalıdır.
Doğru / yanlış: Eser boyunca tek biçim / Aynı eserde “kıvrık” ve "düz" tırnak birlikte
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Tırnak İşareti (işaretin kullanımı); tek biçim şartı editoryaldir, TDK kuralı değildir
Kesinlik: bağlam

### NOK-KONUSMA-CIZGISI · Konuşma çizgisi
Kural: Diyaloglar ya konuşma çizgisiyle (—) ya tırnakla verilir; seçim eser boyunca aynı olmalıdır. Konuşma çizgisi kısa çizgiyle (-) karıştırılmamalıdır.
Doğru / yanlış: "— Geliyorum, dedi." / "- Geliyorum, dedi." (aynı eserde çizgi ve tırnak karışık)
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Uzun Çizgi (işaretin kullanımı); tek biçim şartı editoryaldir, TDK kuralı değildir
Kesinlik: bağlam

### NOK-SORU · Soru işareti
Kural: Soru bildiren cümlelerin sonuna soru işareti konur; soru eki bulunduğu hâlde soru anlamı taşımayan cümlelerde konmaz.
Doğru / yanlış: "Geldin mi?" / "Geldin mi."
Kaynak: Yazım Kılavuzu, Noktalama İşaretleri, Soru İşareti
Kesinlik: bağlam

### NOK-BOSLUK · Çift boşluk
Kural: Kelimeler arasında tek boşluk bırakılır.
Doğru / yanlış: "Bir gün geldi." / "Bir  gün geldi."
Kaynak: Dizgi kuralı
Kesinlik: bağlamdan bağımsız

## Dil bilgisi ve anlatım

### DIL-OZNE-YUKLEM · Özne ile yüklem uyumu
Kural: Yüklem kişi ve sayı bakımından özneyle uyuşur.
Doğru / yanlış: "Ben ve kardeşim geldik." / "Ben ve kardeşim geldi."
Kaynak: Dil bilgisi, anlatım bozuklukları
Kesinlik: bağlam

### DIL-GEREKSIZ-SOZCUK · Gereksiz sözcük
Kural: Aynı anlamı taşıyan sözcükler bir arada kullanılmaz.
Doğru / yanlış: "iade etti" / "geri iade etti"
Kaynak: Dil bilgisi, anlatım bozuklukları
Kesinlik: bağlam

### DIL-YANLIS-SOZCUK · Yanlış anlamda kullanılan sözcük
Kural: Sözcük sözlükteki anlamıyla kullanılır.
Doğru / yanlış: "Bu konuda kesin bir karar verildi." / "Bu konuda kesik bir karar verildi."
Kaynak: Güncel Türkçe Sözlük
Kesinlik: bağlam

### DIL-EK-YANLISI · Ek yanlışı ve eksikliği
Kural: Ortak kullanılan ögelere gelen ekler her ögeye uyar; ek eksikliği ya da yanlış ek anlatımı bozar.
Doğru / yanlış: "Ona inanıyor ve güveniyorum." / "Ona inanıyor ve onu güveniyorum."
Kaynak: Dil bilgisi, anlatım bozuklukları
Kesinlik: bağlam

### DIL-CATI · Çatı uyumsuzluğu
Kural: Ortak ögeye bağlanan yüklemler çatı bakımından uyuşur.
Doğru / yanlış: "Kitap okundu ve rafa kaldırıldı." / "Kitap okundu ve rafa kaldırdı."
Kaynak: Dil bilgisi, anlatım bozuklukları
Kesinlik: bağlam

## Süreklilik

### SUR-ZAMAN · Zaman ve mevsim
Kural: Saat, gün, mevsim ve olayların sırası eser içinde çelişmez.
Doğru / yanlış: — / Aynı gece önce "saat ikiydi", sonra "henüz on birdi"
Kaynak: Editoryal süreklilik
Kesinlik: bağlam

### SUR-MEKAN · Mekân
Kural: Mekânların yeri, düzeni ve aralarındaki uzaklık eser içinde çelişmez.
Doğru / yanlış: — / Bir bölümde ikinci kattaki oda, sonrakinde bahçeye açılıyor
Kaynak: Editoryal süreklilik
Kesinlik: bağlam

### SUR-BILGI · Kim neyi biliyor
Kural: Bir karakter, öğrenmediği bir bilgiyi kullanmaz.
Doğru / yanlış: — / Haberi henüz almamış karakterin ondan söz etmesi
Kaynak: Editoryal süreklilik
Kesinlik: bağlam

### SUR-NESNE · Nesneler
Kural: Nesnelerin yeri, durumu ve sahibi eser içinde çelişmez.
Doğru / yanlış: — / Masada bırakılan anahtarın cepten çıkması
Kaynak: Editoryal süreklilik
Kesinlik: bağlam

### SUR-YAS · Yaş, ad ve geçmiş
Kural: Karakterlerin yaşları, adları ve geçmişleri eser içinde çelişmez.
Doğru / yanlış: — / Babanın kaybı bir yerde yedi, başka bir yerde on yaşında
Kaynak: Editoryal süreklilik
Kesinlik: bağlam
