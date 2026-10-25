# FinOps Guard: Proje Dokümantasyonu

**Yapay Zekâ Destekli Bulut Maliyeti Optimizasyonu ve Yönetim Platformu (AWS)**

Bu klasör, projenin haftalık geliştirme notlarını içerir. Notlar, final raporuna doğrudan aktarılabilecek biçimde yazılmıştır: her hafta için amaç, yapılanlar, alınan kararların gerekçesi, karşılaşılan hatalar ve çözümleri, kanıtlar (ekran görüntüleri ve log çıktıları) ve bilinen sınırlamalar yer alır.

## Proje ne yapıyor?

Bulut maliyetleri genellikle para harcandıktan sonra, fatura geldiğinde fark edilir. FinOps Guard bu sırayı tersine çevirir: bir altyapı değişikliği (pull request) henüz **birleştirilmeden önce** aylık maliyete etkisini hesaplar, kurallara (bütçe, zorunlu etiket, yasaklı kaynak türleri, güvenlik taramaları) göre otomatik karar verir ve sonucu PR'ın üzerine yazar. Kurallara uymayan değişiklik `main` dalına giremez.

Projenin ilerleyen aşamalarında bu karar mekanizmasına yapay zekâ eklenecektir: bir değişikliğin gerçekçi maliyet üst sınırını tahmin eden bir model (P90 tahmini), günlük maliyet verisinde anormal artışı yakalayan bir anomali tespit modeli ve kural tabanlı sisteme geri dönüş (fallback) mekanizması.

Bu yaklaşıma **Shift-Left FinOps** denir: maliyet kontrolünü yazılım yaşam döngüsünün sonundan (fatura) başına (kod incelemesi) çekmek.

## Genel mimari

```
Geliştirici ── PR açar ──► GitHub Actions
                              │
                              ├─ app        : ruff (lint), pytest, docker build
                              ├─ terraform  : fmt, init, validate, plan
                              │                  └─ plan.json ─► Conftest kuralları
                              │                       (etiket, yasaklı kaynak, boyut)
                              ├─ infracost  : fiyat farkı ─► PR yorumu
                              │                  └─ Conftest bütçe kuralı
                              └─ security   : Checkov (Terraform), Trivy (Docker imajı)

   4 kontrolün hepsi yeşil olmadan main dalına birleştirme yapılamaz.

main dalına birleşince (Hafta 5):
   imaj derle ─► ECR ─► terraform apply ─► sağlık kontrolü ─► başarısızsa geri al ─► bildirim

Yapay zekâ katmanı (Hafta 6-8):
   maliyet tahmini (P90) + anomali tespiti + karar katmanı + kural tabanlı geri dönüş
```

## Haftalar

| Hafta | Konu | Durum | Not |
|---|---|---|---|
| 1 | AWS hesap güvenliği, bütçe alarmı, Flask uygulaması, Docker | Tamam | [hafta-1.md](hafta-1.md) |
| 2 | Terraform, uzak state, GitHub OIDC rolleri, dev ortamı (VPC, ECR, ECS Fargate) | Tamam | [hafta-2.md](hafta-2.md) |
| 3 | Pull request iş akışı, Infracost maliyet yorumu, koruma kuralı | Tamam | [hafta-3.md](hafta-3.md) |
| 4 | Politika kuralları (Conftest/OPA), Checkov, Trivy, demo PR'lar | Tamam | [hafta-4.md](hafta-4.md) |
| 5 | Otomatik dağıtım, sağlık kontrolü, otomatik geri alma, bildirim | Planlandı | |
| 6-8 | Yapay zekâ: maliyet tahmini, anomali tespiti, karar katmanı | Planlandı | |
| 9-10 | Rapor, sunum, tampon süre | Planlandı | |

## Kullanılan araçlar ve sürümler

| Araç | Sürüm | Nerede |
|---|---|---|
| Terraform | 1.10.5 (CI), en az 1.10 | altyapı kodu |
| AWS provider | `~> 6.0` | Terraform |
| Python, Flask, Gunicorn | 3.12, 3.0.3, 22.0.0 | örnek uygulama |
| Docker taban imajı | `python:3.12-slim` | uygulama imajı |
| GitHub Actions | `checkout@v4`, `setup-python@v5`, `setup-terraform@v3`, `configure-aws-credentials@v4` | CI |
| Infracost | `infracost/actions/setup@v3` | maliyet hesabı |
| Conftest (OPA) | v0.56.0 | politika kuralları |
| Checkov | `bridgecrewio/checkov-action@v12` | Terraform güvenlik taraması |
| Trivy | `aquasecurity/trivy-action@v0.36.0` | imaj taraması |

## Temel kavramlar sözlüğü

| Kavram | Açıklama |
|---|---|
| **FinOps** | Bulut harcamalarını mühendislik, finans ve iş tarafının birlikte yönettiği disiplin |
| **IaC (Infrastructure as Code)** | Altyapıyı elle değil kodla tarif etmek (burada Terraform) |
| **CI/CD** | Kod değişince testlerin ve dağıtımın otomatik çalışması |
| **PR (Pull Request)** | Değişikliğin ana dala birleştirilmeden önce gözden geçirilmesini isteyen talep |
| **OIDC** | GitHub'ın AWS'e kalıcı anahtar olmadan "ben bu depodan geliyorum" diye kanıt göstermesi |
| **State (durum dosyası)** | Terraform'un "AWS'te ne oluşturdum" defteri |
| **Policy as Code** | Kuralları belgede değil, çalıştırılabilir kodda yazmak |
| **Shift-Left** | Kontrolü sürecin sonundan başına çekmek |

## Bu notlar nasıl kullanılır?

- Her hafta dosyasında önce **özet**, sonra ayrıntılar vardır. Rapora aktarırken "Özet", "Kararlar" ve "Karşılaşılan hatalar" bölümleri doğrudan kullanılabilir.
- Ekran görüntüleri `docs/img/` klasörüne konur. Her hafta dosyasının sonunda hangi görüntülerin gerektiği listelenmiştir.
- Rakamlar (bütçe tutarı, eşikler vb.) rehberdeki ve repodaki gerçek değerlerdir. Farklı yaptığın bir ayar varsa ilgili satırı kendi değerine göre düzelt.
- Dosyalarda hesap numarası, IP adresi ve anahtar gibi hassas bilgi **yoktur**. Örnek yerlerde `<HESAP_NO>`, `<KULLANICI>` gibi yer tutucular kullanılmıştır. Bu bilgileri depoya yazmayın.
