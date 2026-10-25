# Hafta 3: Pull Request İş Akışı ve Maliyet Yorumu

**Konu:** Bir pull request açıldığında GitHub Actions'ın kodu otomatik kontrol etmesi, AWS'e **şifresiz** (OIDC) bağlanıp Terraform planı çıkarması ve Infracost ile değişikliğin aylık maliyete etkisini PR'a yorum olarak yazması.

## Özet

Bu hafta projenin ilk gerçek otomasyonu kuruldu. Her PR'da üç iş çalışır: `app` (lint, test, Docker derleme), `terraform` (biçim, geçerlilik, plan) ve `infracost` (fiyat farkı yorumu). Terraform işi, Hafta 2'de kurulan salt-okunur `plan` rolünü GitHub OIDC ile alır, yani depoda hiçbir AWS erişim anahtarı yoktur. Son olarak GitHub'da bir koruma kuralı (ruleset) tanımlandı: kontroller yeşil olmadan `main` dalına birleştirme yapılamaz.

En önemli kanıt: kodda hiçbir hata olmayan, testleri ve planı geçen bir PR'ın aylık tahmini yaklaşık **$11'den $245'e** çıkardığı, **Infracost yorumuyla birleştirmeden önce** görüldü.

| Çıktı | Durum |
|---|---|
| `app`, `terraform`, `infracost` işleri | Tamam |
| AWS'e OIDC ile şifresiz giriş | Tamam |
| PR'a otomatik maliyet yorumu | Tamam |
| `main` için koruma kuralı (ruleset) | Tamam |
| Maliyet artışı, azalışı ve değişmeme senaryoları kanıtlandı | Tamam |

## Bu haftanın kavramları

| Kavram | Açıklama |
|---|---|
| **GitHub Actions** | GitHub'ın otomasyon sistemi. Ek bir şey kurmak gerekmez |
| **Workflow** | Otomasyonun tarif dosyası (`.github/workflows/pr.yml`, YAML) |
| **Job / Step** | Workflow içindeki bağımsız bölümler / komutlar |
| **Runner** | İşi çalıştıran geçici sanal bilgisayar (`ubuntu-latest`). Her çalışmada sıfırdan başlar |
| **Status check** | PR sayfasında yeşil tik ya da kırmızı çarpı olarak görünen sonuç |
| **Ruleset (koruma kuralı)** | "Şu kontroller geçmeden şu dala birleştirme yapılamaz" kuralı |
| **OIDC** | GitHub, çalışma başına geçici bir kimlik belgesi (JWT) üretir. AWS bunu rolün güven koşuluyla karşılaştırır. Eşleşirse geçici anahtar verir |
| **`sub` claim** | Kimlik belgesindeki "ben kimim" alanı: hangi depo, hangi olay |
| **Secret / Variable** | GitHub'da saklanan gizli değer / gizli olmayan ayar |
| **Infracost** | Terraform kodundan aylık fiyat hesaplayan araç. AWS'e bağlanmaz, kodu ve kendi fiyat listesini okur |
| **Cost diff** | "Önce" ve "sonra" fiyat farkı |

## İş akışı

```
PR açılır (main hedefli)
   │
   ├─ app        ruff ► pytest ► docker build
   │
   ├─ terraform  fmt kontrolü ► AWS'e OIDC ile giriş ► init ► validate ► plan
   │               (plan rolü salt-okunur; PR'dan gelen kod AWS'i DEĞİŞTİREMEZ)
   │
   └─ infracost  main'in fiyatı ► PR'ın fiyatı ► fark ► PR'a yorum
```

### Terraform işinin adımları

| Adım | Ne yapar | Neden |
|---|---|---|
| `fmt -check` | Kod biçimi standart mı | Herkesin kodu aynı görünsün |
| Configure AWS credentials (OIDC) | `plan` rolünü alır | Şifresiz AWS girişi |
| `init` | Eklentileri indirir, S3 state'e bağlanır | Plan, state'i okur |
| `validate` | Söz dizimi ve mantık hataları | Hızlı ve ucuz hata yakalama |
| `plan` | "Ne değişecek" listesi | Değişiklik görünür olsun |
| Job summary | Planı çalışmanın özet sayfasına yazar | Logda gezinmeden okumak |

### Infracost işinin adımları

1. PR dalı ve **hedef (base) dal** iki ayrı klasöre indirilir.
2. Hedef dalın fiyatı hesaplanır (`infracost breakdown`).
3. PR'ın fiyatı hesaplanıp farkı bulunur (`infracost diff --compare-to`).
4. Sonuç PR'a bot yorumu olarak yazılır. Her çalışmada aynı yorum güncellenir (`--behavior=update`).

### Gerekli ayarlar

| Ayar | Tür | Değer |
|---|---|---|
| `INFRACOST_API_KEY` | Secret | Infracost'un ücretsiz API anahtarı |
| `AWS_PLAN_ROLE_ARN` | Variable | Bootstrap çıktısındaki `plan` rolünün ARN'si (gizli değil) |

### Güvenlik tasarımı

- İşlere en az yetki verilir: workflow varsayılanı yalnızca `contents: read`. `terraform` işi ek olarak `id-token: write` (OIDC belgesi isteme), `infracost` işi `pull-requests: write` (yorum yazma) alır.
- Rol güven koşulu: yalnızca **bu depodaki pull request çalışmaları** `plan` rolünü alabilir.
- Depoda kalıcı AWS anahtarı yoktur, çalınacak bir sır yoktur.

## Karşılaşılan en önemli sorun: OIDC `AssumeRoleWithWebIdentity` hatası

**Belirti:** `terraform` işi `Configure AWS credentials` adımında 12 kez yeniden deneyip şu hatayla düştü:

```
Error: Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

**Teşhis (adım adım):**

1. Rol ARN'si doğru muydu? Log'da `role-to-assume` görüldü, biçim doğruydu.
2. Rolün güven politikası doğru muydu? AWS konsolunda `sub` koşulu `repo:<KULLANICI>/<DEPO>:pull_request` idi. Kullanıcı adı ve depo adı GitHub'daki yazımla birebir aynıydı, `aud` ve sağlayıcı ARN'si de doğruydu.
3. Hata tahminle çözülemeyince geçici bir **hata ayıklama adımı** eklendi. Adım, GitHub'dan OIDC belgesini isteyip içindeki `sub` alanını çözümleyerek yazdırır.

**Kök neden:** GitHub'ın gönderdiği `sub` değeri, beklenenden farklı biçimdeydi. Kullanıcı ve depo adlarına **sayısal kimlikler** eklenmişti:

```
beklenen : repo:<KULLANICI>/<DEPO>:pull_request
gerçek   : repo:<KULLANICI>@<KULLANICI_ID>/<DEPO>@<DEPO_ID>:pull_request
```

Rolün koşulu eski biçimi beklediği için AWS belgeyi reddetti.

**Çözüm:** Bootstrap'e `github_owner_id` ve `github_repo_id` değişkenleri eklendi. Rol güven koşulları yeni biçime göre (kimlikli) güncellendi. `apply` rolü de aynı sorunu yaşayacağı için aynı anda düzeltildi. `terraform apply` planı yalnızca **iki rolün güven politikasında yerinde güncelleme** gösterdi, hiçbir şey silinmedi. Sonrasında iş yeşile döndü ve hata ayıklama adımı silindi.

**Kazanım:** Kimlikli `sub`, kullanıcı adı yeniden kullanımına (birisi senin bıraktığın kullanıcı adını alıp rolü ele geçirmeye çalışması) karşı da koruma sağlar, çünkü sayısal kimlik yeniden kullanılamaz. Aynı zamanda "bulut kimlik güveni, tahminle değil gerçek belgenin içeriğiyle doğrulanır" dersi.

## Diğer sorunlar ve çözümleri

| Sorun | Neden | Çözüm |
|---|---|---|
| PR, tüm işler eklenmeden birleştirildi (yalnızca `app` işiyle) | PR birleştirme düğmesine erken basıldı | Kalan işler (`terraform`, `infracost`) yeni bir PR'da eklendi. Not: `pull_request` olayında GitHub, workflow dosyasının **PR dalındaki** sürümünü çalıştırır, bu yüzden yeni işler birleştirmeden önce test edilebildi |
| `main` üzerinde `git restore` sonrası `desired_count` tekrar `1` oluyordu | `main`'de commit edilmiş değer Hafta 2'den kalan `1` idi. Yerelde elle `0` yapıp `git restore` çalıştırmak commit edilmiş değere döndürür | Düzeltme küçük bir PR ile `main`'e girdi. Infracost bu PR'da **−$10** göstererek değişikliğin gerekli olduğunu da kanıtladı |
| `git checkout` ve dal silme sırasında klasör silme uyarıları | Windows'ta dosya kilidi | Zararsız, `n` yazılıp devam edildi |

## Kanıtlar: üç PR, üç senaryo

| PR | Değişiklik | Infracost sonucu | Kontroller |
|---|---|---|---|
| #5 (ucuz) | Sadece README satırı | "Monthly estimate generated", fiyat değişmedi | 3/3 yeşil, Merge açık |
| #6 (pahalı) | `desired_count = 5`, görev 1 vCPU / 4 GB | **+$234 (+%2.260)**, yeni aylık tahmin **$245** | 3/3 yeşil (kod geçerli, ama çok pahalı) |
| #7 (düzeltme) | `desired_count` 1'den 0'a | **−$10**, yeni tahmin **$0** | 3/3 yeşil |

**Yorum:** #6 en kritik örnek. Testler, `validate` ve `plan` geçti, yani klasik CI bu PR'ı **hatasız** bulurdu. Ama değişiklik aylık faturayı yaklaşık 22 katına çıkarıyordu. Bu bilgi, PR birleştirilmeden önce Infracost yorumuyla görüldü. Hafta 4'te bu durum otomatik reddedilmeye dönüştürüldü.

Önemli not: Infracost, kaynakların ay boyunca (730 saat) çalıştığını varsayar. Ortam yalnızca test süresince açık tutulduğu için gerçek harcama bu **tavan tahminden** çok daha düşüktür. Tahmine kullanım bazlı maliyetler (trafik, log hacmi) dahil değildir (`Usage cost*` sütunu boş). Bu boşluğu yapay zekâ katmanının doldurması hedeflenmektedir.

## Koruma kuralı (ruleset)

GitHub, depo ayarlarında bir ruleset ile `main` dalı korundu:

- Hedef: varsayılan dal (`main`).
- PR ile birleştirme zorunlu.
- Zorunlu durum kontrolleri: `app`, `terraform`, `infracost`, `security` (son ikisi Hafta 4'te eklendi).
- Muafiyet listesi (bypass) boş bırakılması önerilir: depo sahibi de kurallara tabi olur.

Bir ruleset'e **hedef dal eklemeden** kaydedilirse "This ruleset does not target any resources and will not be applied" uyarısı çıkar. Hedef olarak `Include default branch` eklenince çözüldü. Bir kontrol adı, listede görünmesi için `main`'e karşı en az bir kez çalışmış olmalıdır.

## Maliyet

Hafta boyunca AWS'te hiçbir kaynak oluşturulmadı. CI'daki `plan` AWS'ten yalnızca okur ve state kovasına küçük bir kilit dosyası yazar. GitHub Actions kullanımı ücretsiz kota içinde kaldı. Infracost ücretsiz plan.

## Sınırlamalar ve bilinen eksikler

| Konu | Durum |
|---|---|
| Actions sürümleri etiketle (`@v4`) sabitlendi, commit SHA ile değil | Üretimde SHA ile sabitlemek daha güvenli |
| Workflow yalnızca **kontrol** ediyor, dağıtım yapmıyor | Hafta 5 |
| Politika kuralları henüz yok, yalnızca fiyat gösteriliyor | Hafta 4 |
| Infracost kullanım maliyetini bilmiyor | Yapay zekâ katmanı (Hafta 6-8) |

## Kontrol listesi

- [x] `INFRACOST_API_KEY` secret ve `AWS_PLAN_ROLE_ARN` variable tanımlı
- [x] `pr.yml` içinde üç iş çalışıyor
- [x] `terraform` işi OIDC ile giriyor, depoda AWS anahtarı yok
- [x] PR'larda Infracost yorumu görünüyor (artış, azalış, değişmeme)
- [x] Ruleset aktif, birleştirme için kontroller zorunlu
- [x] Hata ayıklama adımı silindi, workflow temiz

## Rapora aktarım için

- "Şifresiz bulut erişimi" bölümü: OIDC, iki rol, `sub` koşulu, kalıcı anahtar yok.
- "Hata ayıklama vaka çalışması": yukarıdaki OIDC sorunu (teşhis, kök neden, çözüm, kazanım).
- "Shift-Left FinOps kanıtı": #5, #6, #7 tablosu ve +$234 yorumunun ekran görüntüsü.

## Gereken ekran görüntüleri (`docs/img/`)

1. `h3-cheap-pr.png`: #5, 3 yeşil kontrol ve Infracost yorumu
2. `h3-expensive-pr.png`: #6, Infracost yorumu (+$234, +%2.260, $245)
3. `h3-decrease-pr.png`: #7, Infracost yorumu (−$10)
4. `h3-oidc-error.png`: hata logu (isteğe bağlı)
5. `h3-ruleset.png`: koruma kuralı ayarları
