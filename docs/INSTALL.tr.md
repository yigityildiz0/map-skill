# Türkçe kurulum

## En kolay yöntem: GitHub plugin kaynağı

```bash
codex plugin marketplace add yigityildiz0/map-skill
```

Ardından ChatGPT masaüstü uygulamasını yeniden başlat:

1. **Plugins** bölümünü aç.
2. Kaynaklardan **Map Skill** seç.
3. **Map Skill** eklentisini kur.
4. Temiz test için yeni bir sohbet aç.

Kaynağı kontrol et:

```bash
codex plugin marketplace list
```

Güncelle:

```bash
codex plugin marketplace upgrade map-skill
```

## Yalnız Universal skill

Windows PowerShell:

```powershell
$mapZip = Join-Path $env:TEMP 'map-skill-universal.zip'
Invoke-WebRequest 'https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-universal.zip' -OutFile $mapZip
New-Item -ItemType Directory -Force (Join-Path $env:USERPROFILE '.agents\skills') | Out-Null
Expand-Archive $mapZip (Join-Path $env:USERPROFILE '.agents\skills') -Force
```

Şu dosya oluşmalı:

```text
%USERPROFILE%\.agents\skills\plan-smart-routes\SKILL.md
```

Skill görünmezse Codex/ChatGPT masaüstü uygulamasını yeniden başlat.

## İstanbul sürümü

Aynı işlemi şu ZIP ile yap:

```text
https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-istanbul.zip
```

Klasör adı `plan-smart-routes-istanbul` olduğu için Universal ile yan yana çalışabilir.

## Diğer şehir sürümleri

Her şehir ZIP'i tek, bağımsız bir skill klasörü içerir. Örnek:

```text
map-skill-london.zip       → plan-smart-routes-london/
map-skill-hong-kong.zip    → plan-smart-routes-hong-kong/
map-skill-toronto.zip      → plan-smart-routes-toronto/
```

Universal zaten 16 şehrin resmî kaynak kayıtlarını içerir. Şehir sürümleri, ilgili şehirde daha kesin tetikleme ve profil yükleme sağlar.

## Hızlı test

```text
Yarın 09:00'da Kadıköy'den Maslak'taki şu konumda olmam gerekiyor.
Toplu taşıma kullanacağım; güvenilir, hızlı ve az aktarmalı seçenekleri karşılaştır.
```

Başlangıç, tam hedef, tarih veya çıkış/varış saati eksikse skill önce tek kısa soruyla bunları ister. Bu hata değil; yanlış rota üretmesini engelleyen kuraldır.

Açık çağırma örneği:

```text
$plan-smart-routes-istanbul Kadıköy'den Maslak'a yarın 09:00'da varacağım şekilde rota planla.
```

## Dosya doğrulama

```powershell
Get-FileHash .\map-skill-universal.zip -Algorithm SHA256
```

Sonucu GitHub sürümündeki `SHA256SUMS.txt` ile karşılaştır.

## Güncelleme ve kaldırma

Plugin kaynağını güncelle:

```bash
codex plugin marketplace upgrade map-skill
```

Plugin kaynağını kaldır:

```bash
codex plugin marketplace remove map-skill
```

Tekil skill'i kaldıracaksan yalnız şu kesin klasörü hedefle; üstteki `.agents\skills` klasörünü komple silme:

```text
%USERPROFILE%\.agents\skills\plan-smart-routes
```
