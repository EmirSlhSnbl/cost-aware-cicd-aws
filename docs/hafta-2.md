# Hafta 2: Terraform, Uzak State, OIDC ve Dev Ortamı

**Konu:** AWS altyapısını elle tıklayarak değil **kodla** kurmak. Terraform ile state kovası, GitHub için şifresiz giriş rolleri (OIDC) ve çalışan bir dev ortamı (ağ, imaj deposu, konteyner servisi).

## Özet

Bu hafta altyapı koda döküldü. Önce Terraform'un "defterini" (state) tutacak güvenli bir S3 kovası ve GitHub Actions'ın AWS'e **kalıcı şifre olmadan** girmesini sağlayan iki IAM rolü kuruldu (bootstrap). Ardından yeniden kullanılabilir modüllerle (ağ, ECR, ECS) dev ortamı yazıldı, Hafta 1'deki Docker imajı ECR'a gönderildi ve ECS Fargate üzerinde çalıştırılarak `/health` ucundan yanıt alındı. Maliyet kontrolü için iş bitince ortam `terraform destroy` ile silindi.

| Çıktı | Durum |
|---|---|
| Bootstrap: state kovası, OIDC sağlayıcısı, `plan` ve `apply` rolleri | Tamam |
| Modüller: `network`, `ecr`, `ecs` | Tamam |
| Dev ortamı `apply` ile kalktı, `/health` yanıt verdi | Tamam |
| `terraform destroy` ile temizlendi | Tamam |
| Kod PR ile `main` dalına girdi | Tamam |

## Bu haftanın kavramları

| Kavram | Açıklama |
|---|---|
| **Terraform** | "Şu kaynaklar olsun" diye yazdığın kodu okuyup AWS'te oluşturan araç |
| **`init`, `plan`, `apply`, `destroy`** | Hazırla, ne yapacağını göster (hiçbir şey değiştirmez), uygula, sil |
| **State (durum) dosyası** | Terraform'un oluşturduğu kaynakların kaydı. Kaybolursa Terraform kafayı karıştırır |
| **Remote state** | State'i bilgisayarda değil, güvenli bir S3 kovasında tutmak |
| **State kilidi** | İki işlemin state'i aynı anda bozmasını önleyen mekanizma. Terraform 1.10'dan itibaren S3'in kendi kilidi yeterli (`use_lockfile`), DynamoDB tablosu gerekmez |
| **Modül** | Tekrar kullanılabilir Terraform klasörü (değişken alır, çıktı verir) |
| **VPC, subnet, internet gateway** | AWS içindeki özel ağ, bölümleri ve internet çıkış kapısı |
| **Security group** | Sanal güvenlik duvarı: hangi porta kim erişebilir |
| **ECR** | Docker imajlarının saklandığı AWS deposu |
| **ECS Fargate** | Sunucu yönetmeden konteyner çalıştıran servis |
| **Task definition / Service** | Konteyner tarifi / "bu tariften N tane çalışsın" |
| **GitHub OIDC** | GitHub'ın her çalışmada geçici bir kimlik belgesi üretip AWS'e göstermesi. Kalıcı erişim anahtarı gerekmez |
| **IAM rolü** | "Bu kimlik şunları yapabilir" izin kümesi |
| **Etiket (tag)** | Kaynaklara iliştirilen anahtar-değer. Maliyeti gruplamak için kullanılır |

## Mimari

```
Bootstrap (bir kez, elle çalıştırılır)       Dev ortamı (tekrar tekrar kurulup silinebilir)
├─ S3 kovası (state defteri)                 ├─ VPC + 2 genel subnet + internet gateway
├─ GitHub OIDC sağlayıcısı                   ├─ Güvenlik grubu (uygulama portu)
├─ Rol "plan"  (salt-okunur, PR için)        ├─ ECR (imaj deposu)
└─ Rol "apply" (sadece main dalı için)       └─ ECS Fargate (küme, görev tanımı, servis)
```

Klasör yapısı:

```
terraform/
├─ bootstrap/          state kovası + OIDC rolleri (yerel state, bir kez uygulanır)
├─ modules/
│   ├─ network/        VPC, subnet, rota, güvenlik grubu
│   ├─ ecr/            imaj deposu ve yaşam döngüsü
│   └─ ecs/            log grubu, roller, küme, görev, servis
└─ envs/dev/           modülleri birleştirir, uzak state'i kullanır
```

## Bootstrap neden ayrı?

Terraform'un defterini S3 kovasında tutacağız, ama bu kovayı da Terraform ile oluşturmamız gerekiyor. Bu "önce tavuk mu yumurta mı" sorununun standart çözümü, kovayı ve rolleri ayrı, küçük bir ön kurulumda **yerel state ile** oluşturmaktır. Bu klasörün state dosyası (`terraform.tfstate`) bilgisayarda kalır, git'e girmez, **yedeklenir**.

### Bootstrap'in oluşturduğu kaynaklar

| Kaynak | Ayar | Neden |
|---|---|---|
| S3 kovası `finops-guard-tfstate-<HESAP_NO>` | Sürümleme, AES256 şifreleme, tüm herkese açık erişim engelli | State bozulursa eski sürüme dönülebilir, içerik korunur. Ad hesap numarasını içerir çünkü S3 adları dünya çapında benzersiz olmalı |
| OIDC sağlayıcısı | `token.actions.githubusercontent.com` | AWS'in GitHub kimlik belgelerine güvenmesi |
| Rol `finops-guard-gha-plan` | `ReadOnlyAccess` + state kovası erişimi; yalnız pull request çalışmaları alabilir | PR'dan gelen kod AWS'te hiçbir şeyi **değiştiremez** |
| Rol `finops-guard-gha-apply` | `AdministratorAccess` (geçici); yalnız `main` dalı alabilir | Değişikliği sadece gözden geçirilmiş, birleştirilmiş kod yapar |

Her kaynağa `default_tags` ile `Project`, `Owner`, `Environment`, `ManagedBy` etiketleri otomatik eklenir. Hafta 4'teki etiket kuralı bu etiketlere dayanır.

## Dev ortamı kararları ve gerekçeleri

| Karar | Gerekçe |
|---|---|
| **Yük dengeleyici (ALB) yok** | Aylık sabit maliyet getirir. Görev kendi genel IP'siyle erişilebilir |
| **NAT Gateway yok** | Ayda onlarca dolar tutar. Görev genel IP ile imajı ECR'dan çeker |
| En küçük Fargate boyutu (0.25 vCPU, 512 MiB) | En ucuz seçenek |
| İlk `apply`'da `desired_count = 0` | ECR başta boştur. Önce imaj gönderilir, sonra görev başlatılır |
| ECR etiketleri **IMMUTABLE** | Bir sürüm etiketi bir kez yazılır, üzerine yazılamaz. Hangi kodun çalıştığı her zaman bilinir |
| ECR yaşam döngüsü: son 10 imaj | Depolama maliyeti sıfıra yakın kalır |
| Log saklama 7 gün | Uzun saklama maliyettir |
| **Deployment circuit breaker** (rollback açık) | Yeni sürüm sağlıksızsa ECS otomatik önceki sürüme döner |
| İki ayrı OIDC rolü | En az yetki ilkesi: okuma ve yazma ayrı kimlikler |
| `apply` rolü geçici olarak `AdministratorAccess` | Hafta 2-5'te izin hatalarıyla vakit kaybetmemek için öğrenme kısayolu. Hafta 6 sonrası en az yetkiye daraltılacak |

## Yapılanlar (adım adım)

1. **Bootstrap:** `terraform init`, `plan`, `apply`. Çıktılar not alındı: `state_bucket`, `plan_role_arn`, `apply_role_arn`. `terraform.tfstate` yedeklendi.
2. **Backend:** `terraform/envs/dev/backend.tf` içindeki kova adı bootstrap çıktısıyla dolduruldu.
3. **İlk apply (görev sayısı 0):** VPC, ECR, ECS kümesi ve servis oluştu, çalışan görev yok (maliyet yaklaşık sıfır).
4. **İmaj gönderimi:** ECR'a Docker ile giriş, `docker build --platform linux/amd64`, `v1` etiketiyle `push`.
5. **Görevi başlatma:** `desired_count = 1`, `apply`. Konsolda görev `RUNNING` olunca genel IP'den `http://<IP>:8080/health` çağrıldı, `{"status":"ok"}` döndü.
6. **Temizlik:** `terraform destroy`. Bootstrap (kova ve roller) silinmedi, maliyeti sent düzeyindedir ve sonraki haftalarda gerekli.
7. **Kod PR ile `main` dalına birleştirildi.**

> **Ekran görüntüsü:** ECS görevi `RUNNING` durumunda.
> **Ekran görüntüsü:** Tarayıcıda `/health` yanıtı.
> **Ekran görüntüsü:** ECR'da `v1` etiketli imaj.

### Önemli ayrıntı: `--platform linux/amd64`

Apple Silicon (M serisi) bir Mac'te bu bayrak yazılmazsa imaj ARM mimarisinde derlenir ve Fargate'te `exec format error` ile çalışmaz. Bayrak her bilgisayarda zararsızdır, bu yüzden hep yazıldı.

## Karşılaşılan sorunlar ve çözümleri

| Sorun | Neden | Çözüm |
|---|---|---|
| `git checkout` sırasında `Deletion of directory ... failed. Should I try again?` | Git, dal değiştirirken boş klasörleri silmeye çalışıyor ama Windows'ta başka bir program (OneDrive, VS Code, antivirüs) o klasörü kısa süre tutuyor | Zararsız. `n` yazıp devam edilir. Dosyalar bozulmaz. |
| Proje OneDrive klasöründeydi | OneDrive, `.git` ve `.terraform` gibi sık değişen büyük dosyaları eşitlemeye çalışıp kilit sorunları üretebilir | Proje `C:\dev\cost-aware-cicd-aws` altına taşındı. Taşımadan önce `terraform.tfstate` yedeklendi ve taşıma sonrası yerinde olduğu doğrulandı |

Not: Kilit uyarıları proje OneDrive dışına taşındıktan sonra da ara sıra çıktı. Demek ki tek neden OneDrive değil. Uyarı davranışı etkilemiyor.

## Maliyet

- Bootstrap: S3'te birkaç KB, IAM ve OIDC ücretsiz. Aylık sent düzeyi.
- Dev ortamı: Görev çalışırken küçük bir saatlik ücret (Fargate ve genel IPv4 adresi). Kullanılmadığı zaman `destroy` edildiği için pratikte yok.
- Infracost, bir görevin ay boyunca sürekli çalıştığını varsaydığında yaklaşık **10 USD/ay** tahmin ediyor (Hafta 3'te görüldü). Gerçek harcama, ortam sadece test süresince açık kaldığı için bunun çok altında.

## Sınırlamalar ve bilinen eksikler

| Konu | Durum | Plan |
|---|---|---|
| `apply` rolü `AdministratorAccess` | Bilinçli öğrenme kısayolu | Hafta 6 sonrası en az yetkiye daraltılacak |
| Güvenlik grubu uygulama portunu tüm internete açıyor | Dev'de bilinçli; görev kısa süre çalışıyor | Gerekirse `allowed_cidrs` ile kendi IP'ne kısıtlanır (IP depoya yazılmaz) |
| Bootstrap state'i yalnız bilgisayarda | Yerel state, yedekli | Gelecek: uzak state'e taşınabilir |
| HTTPS yok | ALB ve sertifika maliyet nedeniyle yok | Kapsam dışı |

## Kontrol listesi

- [x] Bootstrap uygulandı; kova, iki rol, OIDC sağlayıcısı var
- [x] Üç çıktı (`state_bucket`, iki rol ARN'si) not alındı
- [x] `terraform validate` temiz
- [x] İmaj ECR'da, görev `RUNNING`, `/health` yanıt veriyor
- [x] `terraform destroy` temiz çalıştı
- [x] State dosyaları git'e girmedi
- [x] Kod `main` dalına PR ile girdi

## Rapora aktarım için

- "Altyapı kod olarak" bölümü: Terraform, modüller, uzak state, state kilidi.
- "Şifresiz güvenlik" bölümü: OIDC, iki rol, en az yetki, kalıcı anahtar yok.
- "Maliyet bilinci" bölümü: ALB ve NAT'ın bilinçli olarak dışarıda bırakılması, en küçük boyut, günlük `destroy`.

## Gereken ekran görüntüleri (`docs/img/`)

1. `h2-ecs-running.png`: ECS görevi `RUNNING`
2. `h2-health.png`: tarayıcıda `/health` yanıtı
3. `h2-ecr-image.png`: ECR'da `v1` imajı
4. `h2-roles.png`: IAM'de `plan` ve `apply` rolleri
