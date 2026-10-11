# plan-smart-routes

[English](plan-smart-routes.en.md) · [Türkçe](plan-smart-routes.tr.md) · [Library](../../README.tr.md)

**Ulaşım türü, zamanlama ve canlı veri sınırlarını gözeterek uygulanabilir rota planlar.**

## Örnek istek

> Bu gezi için yürüyüş ve toplu taşıma seçeneklerini karşılaştır.

## Tetikleme ve yönlendirme

İstek, hostun skill açıklamasıyla eşleştirilir. Host destekliyorsa kanonik adla açık seçim de yapılabilir. Sohbete /ad yazmak tek başına kayıtlı bir komut yaratmaz.

<details>
<summary>Kaynak açıklamasının tam metni</summary>

Plans and compares time-aware trips with public transport plus walking by default: live traffic and service checks, weather, opening hours, fares, multi-stop scheduling, ETA uncertainty and map links (Google Maps, Yandex, Moovit, Apple Maps and others). Turkish triggers: buradan şuraya nasıl giderim, kaç dakikada varırım, hangi otobüs/metro, aktarma, yol tarifi, rota planla. More triggers: otobüs saati, metro, çok duraklı rota, trafik.

</details>

## Çalışma mantığı

Başlangıç/bitiş ve kısıtları belirler; ulaşım türlerini karşılaştırır; aktarma/zamanı değerlendirir; canlı veriyle tahmini ayırır.

Kök giriş dosyası görevi karşılar; yalnız gereken modül ve referanslar yüklenir. Betik içermesi çalıştırıldığı anlamına gelmez. Mevcut araç, veri ve kapsam doğrulandıktan sonra görev yürütülür.

## Girdi, çıktı ve doğrulama

- Girdi: örnek istekteki hedef, ilgili dosya/URL/veri ve sonucu değiştiren kısıtlar.
- Çıktı: isteğe uygun yanıt, plan, taslak veya yetkili dosya değişikliği; dayanak ve belirsizlik açık.
- Doğrulama: yapılan kontrol ile önerilen kontrol ayrı belirtilir; erişilmeyen kaynak veya çalıştırılmayan araç kullanılmış sayılmaz.

## Ortam ve sınırlar

Paket model ağırlığı, izin, hesap veya API kredisi sağlamaz. Bu sürüm mevcut host araçları, açık erişim ve yerel işlemi kullanır; ücretli servis otomatik alternatif değildir. Klinik/yatırım çıktıları profesyonel kararın veya emir işleminin yerine geçmez.

## Modüller ve kaynak

[SKILL.md](../../skills/common/plan-smart-routes/SKILL.md) · [Installation](../INSTALL.md) · [License scope](../LICENSE-SCOPE.md)

Bağımsız kök akışı; referanslar giriş dosyasında listelenir.
