# Hafta 4: Politika Kuralları ve Güvenlik Taramaları

**Konu:** PR akışını "maliyeti gösteren" bir sistemden "maliyete ve riske göre **karar veren**" bir sisteme dönüştürmek. Kural motoru (Conftest/OPA), Terraform güvenlik taraması (Checkov), Docker imaj taraması (Trivy) ve sistemi kanıtlayan dört demo PR.

## Özet

Hafta 3'te sistem fiyatı gösteriyordu. Bu hafta fiyata ve risklere bakıp PR'ı **otomatik reddeden veya uyaran** kurallar eklendi. Kurallar kod olarak yazıldı (Rego dili), kendi birim testleri var (13 test) ve her PR'da çalışır. Ayrıca Terraform kodu Checkov ile, Docker imajı Trivy ile taranır. Sonuçta `main` dalına girebilmek için dört kontrolün (`app`, `terraform`, `infracost`, `security`) tamamı yeşil olmalıdır.

Sistemin kararı iki kademelidir, bu proje tanımındaki "sert ihlal = reddet; yalnızca risk = uyarı" mantığının ilk yarısıdır:

| Kademe | Davranış | Örnek |
|---|---|---|
| **`deny` (sert ihlal)** | İş kırmızı olur, birleştirme kilitlenir | Bütçe aşımı, yasaklı kaynak, eksik etiket |
| **`warn` (yumuşak risk)** | İş yeşil kalır, mesaj yazılır | Büyük görev boyutu, büyük fiyat artışı |

Yapay zekâ katmanı (Hafta 6-8) bu mekanizmaya bağlanacak: modelin yalnızca kendi başına verdiği risk işareti "uyarı + manuel onay" olacak, model hiçbir zaman tek başına reddetmeyecek.

| Çıktı | Durum |
|---|---|
| 3 kural dosyası (bütçe, etiket, yasaklı kaynak) ve boyut uyarıları | Tamam |
| 13 birim testi, CI'da her PR'da çalışıyor | Tamam |
| Checkov taraması, bulgular kararlarla sınıflandırıldı | Tamam |
| Trivy imaj taraması: 0 zafiyet | Tamam |
| 4 demo PR ile sistemin kanıtlanması | Tamam |
| Dört kontrol zorunlu | Tamam |

## Bu haftanın kavramları

| Kavram | Açıklama |
|---|---|
| **Policy as Code** | Kuralları belgede değil, çalıştırılabilir kodda yazmak |
| **OPA / Rego** | Kural yazma altyapısı ve dili ("şu koşulda şu mesajla reddet") |
| **Conftest** | Rego kurallarını JSON gibi dosyalara uygulayan komut satırı aracı |
| **`deny` / `warn`** | İhlalde iş kırmızı olur / yalnızca uyarı yazılır |
| **Plan JSON** | `terraform plan`'ın makinece okunabilir hâli: "şu kaynaklar oluşacak" |
| **Checkov** | Terraform kodunu güvenlik yanlış yapılandırmaları için tarar |
| **Trivy** | Docker imajını bilinen güvenlik açıkları (CVE) için tarar |
| **CVE** | Yazılımlarda keşfedilmiş, numaralandırılmış güvenlik açığı |
| **Risk kabulü** | Bir bulguyu düzeltmemeye, gerekçesini yazarak bilinçli karar vermek |

## Kural dosyaları (`policy/`)

```
policy/
├─ cost/
│   ├─ budget.rego          bütçe kuralları
│   └─ budget_test.rego     5 test
└─ terraform/
    ├─ tags.rego            zorunlu etiketler
    ├─ forbidden.rego       yasaklı kaynak türleri
    ├─ sizing.rego          boyut uyarıları
    └─ policy_test.rego     8 test
```

| Kural | Girdi | Koşul | Sonuç |
|---|---|---|---|
| **Aylık bütçe** | Infracost JSON | PR sonrası toplam aylık tahmin > **$30** | **deny** |
| **Büyük artış** | Infracost JSON | Tek PR'da artış > **$15** | warn |
| **Zorunlu etiket** | Terraform plan JSON | `Project`, `Owner` veya `Environment` etiketi eksik | **deny** |
| **Yasaklı kaynak** | Terraform plan JSON | NAT Gateway, ALB, RDS, EKS, ElastiCache, Redshift oluşturuluyor veya güncelleniyor | **deny** |
| **Fargate CPU** | Terraform plan JSON | CPU > 512 | warn |
| **Fargate bellek** | Terraform plan JSON | Bellek > 1024 MiB | warn |
| **Görev sayısı** | Terraform plan JSON | `desired_count` > 2 | warn |

Notlar:

- Yasaklı kaynak kuralı yalnızca **oluşturma ve güncellemeyi** engeller. Böyle bir kaynağı silmek (maliyet düşürmek) serbesttir.
- Etiket kuralı, etiket destekleyen kaynakların birleştirilmiş etiket kümesine (`tags_all`) bakar. Bu küme provider'ın `default_tags` ayarından gelir. Silinen kaynaklar kontrol dışıdır.
- Bütçe değeri `policy/cost/budget.rego` içindeki `monthly_budget_usd := 30` satırıdır, değiştirmek tek satırlık iştir.

### Kuralların kendi testi

Bir kuralı değiştiren kişi kuralı yanlışlıkla bozabilir. Bu yüzden her kural sahte girdilerle test edilir (`conftest verify`). Toplam **13 test**: bütçe (5), etiket (3), yasaklı kaynak (2), boyut (3). Testler arasında şunlar var:

- Bütçe aşılınca reddet, altındayken reddetme
- Fiyat bilgisi `null` gelirse çökme
- Silinen kaynak etiket kuralına takılmasın
- ALB oluşturmak yasak, ALB'yi silmek serbest
- Varsayılan görev boyutu uyarı üretmesin

Bu testler her PR'da `Policy unit tests` adımında çalışır. Biri kuralı bozarsa PR kırmızı olur.

## CI iş akışındaki değişiklikler

| İş | Eklenen adım | Ne yapar |
|---|---|---|
| `terraform` | Install Conftest, Policy unit tests, Plan to JSON, Policy check (plan) | Planı JSON'a çevirip etiket, yasaklı kaynak ve boyut kurallarını uygular |
| `infracost` | Install Conftest, Budget policy check | PR yorumu yazıldıktan **sonra** bütçe kuralını uygular (yorum kırmızı PR'da da görünsün) |
| `security` (yeni) | Checkov, imajı derleme, Trivy | Terraform ve Docker güvenlik taraması |

Plan JSON dosyası depoya yazılmaz, yalnızca runner'ın geçici klasöründe tutulur.

## Checkov: 16 bulgunun sınıflandırılması

Checkov ilk çalıştırmada çok sayıda kontrolü geçti (OIDC güven politikalarının güvenli claim kullanması, S3 sürümleme ve şifreleme, herkese açık erişim engelleri, ECR değişmez etiketleri ve push taraması, ECS konteynerinin ayrıcalıksız çalışması gibi) ve **16 bulgu** raporladı. Her bulgu için bilinçli karar verildi: düzelt, kabul et veya sonraya bırak.

### Düzeltilenler (3)

| Kural | Kaynak | Yapılan |
|---|---|---|
| `CKV2_AWS_12` | VPC varsayılan güvenlik grubu | Boş `aws_default_security_group` eklendi (hiçbir trafiğe izin vermez) |
| `CKV_AWS_382` | Uygulama güvenlik grubunun çıkış kuralı (tüm trafik) | Çıkış yalnızca `tcp/443` ile sınırlandı (ECR ve log erişimi için yeterli) |
| `CKV2_AWS_61` | State kovası | Yaşam döngüsü kuralı: eski sürümler 90 gün sonra silinir, yarım yüklemeler 7 gün sonra temizlenir |

### Bilinçli kabul edilenler (13), `.checkov.yaml` içinde gerekçeleriyle

| Kural | Konu | Gerekçe |
|---|---|---|
| `CKV_AWS_274` | `apply` rolü AdministratorAccess | **Geçici.** Hafta 6 sonrası en az yetkiye daraltılacak |
| `CKV_AWS_136` | ECR için KMS şifrelemesi | AES256 şifreleme zaten açık, KMS ek aylık ücret getirir |
| `CKV_AWS_158` | Log grubu için KMS | KMS anahtarı aylık ücret |
| `CKV_AWS_145` | State kovası için KMS | SSE-S3 yeterli, KMS ek maliyet ve karmaşıklık |
| `CKV_AWS_338` | Logların 1 yıl saklanması | Maliyet için 7 gün yeterli |
| `CKV_AWS_65` | Container Insights | Ek CloudWatch maliyeti |
| `CKV_AWS_333` | ECS görevine genel IP | **Tasarım kararı:** NAT Gateway yok (aylık sabit maliyet) |
| `CKV2_AWS_11` | VPC flow logs | Log maliyeti |
| `CKV_AWS_394` | AZ veri kaynağı sabitlenmemiş | Her zaman ilk iki bölge kullanılıyor, risk düşük |
| `CKV2_AWS_5` | Güvenlik grubu bir kaynağa bağlı değil | **Yanlış alarm:** Grup, modül çıktısıyla ECS servisine bağlı, Checkov modüller arası bağı görmüyor |
| `CKV_AWS_144` | State kovası çapraz bölge kopya | Ek bölge ve maliyet |
| `CKV2_AWS_62` | State kovası olay bildirimi | Gereksiz |
| `CKV_AWS_18` | State kovası erişim logu | Ayrı log kovası gerektirir |

Bu tablonun çoğu üretim ortamında **açılırdı** (KMS, flow logs, uzun log saklama). Dev ortamında maliyet ve karmaşıklık nedeniyle bilinçli olarak kabul edildi ve gerekçeleri yazıldı. Raporda "risk kabulü yönetimi" olarak sunulabilir.

Düzeltmelerden sonra Checkov `soft_fail: false` (katı mod) ile çalışır: yeni bir bulgu çıkarsa PR kırmızı olur.

## Trivy: Docker imajı temiz

Kendi bilgisayarında ayrıca ve CI'da her PR'da çalıştırılan imaj taraması:

| Katman | Taranan | Sonuç |
|---|---|---|
| İşletim sistemi (Debian 13) | 87 paket | **0 zafiyet** |
| Python paketleri | 10 paket (flask, gunicorn, werkzeug, jinja2, click, blinker, itsdangerous, markupsafe, packaging, pip) | **0 zafiyet** |
| Gizli bilgi taraması | İmaj dosyaları | Bulgu yok |

CI'daki ayar: yalnızca CRITICAL ve HIGH, yalnızca düzeltmesi bulunan zafiyetler (`ignore-unfixed`), bulursa PR kırmızı olur.

**Sınırlama:** Yalnızca iki doğrudan bağımlılık (`flask`, `gunicorn`) sürümle sabitlendi. Dolaylı bağımlılıklar her derlemede güncel sürüme çözülür. Bugün zafiyetsiz, ama derleme tamamen tekrarlanabilir değil. Üretimde kilit dosyası (`pip-tools` veya `uv`) kullanılır.

## Demo PR'lar: sistemin kanıtı

Her demo ayrı bir dalda açıldı, sonuç gözlendi, **birleştirilmeden kapatıldı**. AWS'te hiçbir kaynak oluşmadı.

| Demo | Değişiklik | Kırmızı olan | Kanıt |
|---|---|---|---|
| **1. Bütçe aşımı** (#10) | `desired_count = 5`, görev 1 vCPU / 4 GB | `infracost` | `WARN ... increases the monthly cost by $244.55 (warning threshold $15)` ve `FAIL ... Estimated monthly cost $244.55 exceeds the budget of $30`. Merge düğmesi kilitli |
| **2. Yasaklı kaynak** (#11) | ALB eklendi | `terraform` **ve** `security` | `aws_lb.demo: resource type aws_lb is forbidden by the cost guardrails`. `infracost` **yeşil** (ALB yaklaşık $20, bütçe altında), yani tür yasağı fiyattan bağımsız çalışıyor. Checkov da aynı kaynağı kendi kuralıyla (`CKV2_AWS_28`, genel ALB için WAF) yakaladı: **çok katmanlı savunma** |
| **3. Eksik etiket** (#12) | `Owner` etiketi kaldırıldı | `terraform` | `17 tests, 4 passed, 0 warnings, 13 failures`. Etiket kuralı 13 kaynağın hepsini yakaladı: ECR, log grubu, ECS (küme, servis, görev), IAM rolü, VPC, 2 subnet, internet gateway, rota tablosu, 2 güvenlik grubu. `app`, `infracost`, `security` yeşil kaldı |
| **4. Normal PR** (#13) | Yalnızca README | Hiçbiri | 4 kontrol yeşil, "Monthly estimate generated", Merge açık. Sistem her şeyi reddetmiyor |

Demo 1'de aynı kuralın hem uyarı (artış büyük) hem ret (bütçe aşıldı) üretmesi, iki kademeli karar mekanizmasının çalıştığını gösterir.

## Karşılaşılan sorunlar ve çözümleri

| Sorun | Neden | Çözüm |
|---|---|---|
| `Unable to resolve action aquasecurity/trivy-action@0.28.0` | Trivy action'ın sürüm etiketleri `v` ile başlıyor (`v0.28.0`). Yazdığım etiket mevcut değildi | `@v0.36.0` olarak güncellendi (güncel etiketler GitHub'dan kontrol edildi) |
| `git pull` reddedildi: yerel değişiklikler ezilecekti, `policy_test.rego` ezilecekti | PR zaten birleşmişti, yerelde onaylanmamış düzeltmeler ve aynı dosyanın yerel kopyası vardı | Önce yedek alındı, `git stash` ile değişiklikler kenara alındı, `git pull`, ardından `git stash pop` |
| `stash pop` sonrası `pr.yml` çakışması | Hem `main`'de (Trivy düzeltmesi) hem stash'te değişmişti | `git checkout HEAD -- .github/workflows/pr.yml` ile `main`'in sürümü alınıp Checkov adımı elle yeniden uygulandı |
| Ruleset uyarısı "does not target any resources" | Hedef dal eklenmemişti | `Include default branch` eklendi |
| Demo 3 yanlış nedenle kırmızı: `Format check` | Yorum satırı yapılırken biçim bozulmuştu, politika adımına gelinmedi | Satır düzeltildi, `terraform fmt` uygulandı. Sonraki çalışmada hata doğru adımda (`Policy check (plan)`) çıktı |
| Bütçe değeri | Rehberdeki örnek $50 idi, depodaki değer $30 | Tek gerçek kaynak `policy/cost/budget.rego`. Notlarda $30 kullanıldı |

## Maliyet

Bu hafta da AWS'te hiçbir kaynak oluşturulmadı. Bootstrap'e eklenen S3 yaşam döngüsü kuralı ücretsizdir. Demo PR'lar yalnızca `plan` ve fiyat hesabı çalıştırdı.

## Sınırlamalar ve bilinen eksikler

| Konu | Durum | Plan |
|---|---|---|
| Politika dosyaları PR dalından okunuyor | Biri aynı PR'da kuralı gevşetebilir | Çözüm: `policy/` klasörü için zorunlu inceleme (CODEOWNERS). Şimdilik bilinen sınırlama |
| Güvenlik grubu çıkışı `tcp/443` | AWS'te henüz denenmedi | Hafta 5'te görev ilk başladığında doğrulanacak. Sorun çıkarsa eski hâline dönülür |
| Dolaylı Python bağımlılıkları sabit değil | Bugün zafiyetsiz | Kilit dosyası (gelecek iyileştirme) |
| `apply` rolü AdministratorAccess | Checkov'da "sonra" olarak kayıtlı | Hafta 6 sonrası daraltılacak |
| Infracost kullanım maliyetini bilmiyor | "Tavan tahmin" | Yapay zekâ katmanı |
| "Uyarı + manuel onay" yalnızca uyarı | Onay adımı yok | Hafta 5'te dağıtım hattına eklenecek |

## Kontrol listesi

- [x] `policy/` altında 6 dosya, `conftest verify` 13 test geçiyor
- [x] `pr.yml` içinde 4 iş: `app`, `terraform`, `infracost`, `security`
- [x] Checkov bulguları gerekçeyle sınıflandırıldı, `soft_fail: false`
- [x] Trivy: 0 zafiyet
- [x] Demo 1-4 gözlendi, ekran görüntüleri alındı
- [x] Dört kontrol zorunlu
- [x] Demo PR'lar birleştirilmeden kapatıldı, dallar silindi

## Rapora aktarım için

- "Politika kodu ve kural testleri": kural tablosu, deny/warn ayrımı, 13 birim testi.
- "Çok katmanlı savunma": Demo 2 (aynı kaynağı hem politika hem Checkov yakaladı).
- "Risk yönetimi": Checkov kabul tablosu ve gerekçeleri.
- "Sistem doğrulaması": 4 demo tablosu. İleride yapay zekâ bölümünde karşılaştırma tabanı: "yalnızca kural tabanlı sistemin" doğru karar verme oranı.

## Gereken ekran görüntüleri (`docs/img/`)

1. `h4-demo1-budget.png`: #10, kırmızı `infracost`, Infracost yorumu
2. `h4-demo1-log.png`: `Budget policy check` logu (WARN ve FAIL)
3. `h4-demo2-alb.png`: #11, `terraform` ve `security` kırmızı
4. `h4-demo2-log.png`: `aws_lb is forbidden` logu
5. `h4-demo3-tags.png`: `missing required tags: ["Owner"]` logu
6. `h4-demo4-green.png`: #13, dört yeşil kontrol
7. `h4-checkov.png`: Checkov bulgu listesi (isteğe bağlı)
