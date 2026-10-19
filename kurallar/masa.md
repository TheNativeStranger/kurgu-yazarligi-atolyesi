# Masa kuralları

Editör masayı bu dosyaya göre kurar ve kurduğu masayı yazara bir satırla söyler. Yazar isterse değiştirir.

## Türü belirleme

Öncelik sırası:

1. **Yazarın o anki sözü.** "Bu bir küçürek", "romanımın 3. bölümü" gibi açık bir ifade her şeyi geçersiz kılar.
2. **Eser kimliği.** `atolye/kimlik.md` içinde `- Tür:` satırı varsa o kullanılır.
3. **Betik ölçümü** (`metin/eser.json`):
   - Birden çok bölüm ya da bölüm başlığı varsa: **roman**.
   - Tek metin ve 500 kelimenin altındaysa: **küçürek öykü**.
   - Tek metin ve 500 kelime ya da üstüyse: **kısa öykü**.

## Türe göre masa

| Eser | Masada kimler var |
|---|---|
| Küçürek öykü | okur, editor-satir, redaktor |
| Kısa öykü | okur, gelisim-editoru, editor-satir, redaktor |
| Roman (bölüm ya da bölümler) | okur, gelisim-editoru, editor-satir, redaktor; koşul sağlanırsa danisman |
| Roman (bitmiş dosya) | yukarıdakiler ve dosya-okuru-ajans |

Yayın yönetmeni her masada kararı verir. `imla` kipinde masada yalnız redaktör vardır.

## Koşullu koltuklar

**Danışman** metinde şunlardan biri varsa masaya çağrılır; editör nedenini bir satırla söyler:

- gerçek bir tarih ya da tarihî olay,
- gerçek bir mekân, kurum ya da kişi,
- tıbbi, hukuki ya da dinî bilgi,
- alıntı, atıf ya da gerçek bir esere gönderme.

**Dosya okuru ve ajans** yalnız şu durumlarda gelir:

- yazar "yayınevine göndereceğim", "dosyam hazır mı", "ajansa" gibi bir şey söylerse,
- kimlikte `- Durum: bitti` yazıyorsa.
