# Hafta 1: Temel Hazırlık

**Konu:** AWS hesap güvenliği ve bütçe alarmı, geliştirme araçları, GitHub deposu, örnek uygulama ve Docker imajı.

## Özet

Bu hafta projenin üzerine inşa edileceği zemin hazırlandı. AWS hesabı güvenli hâle getirildi (MFA, günlük işler için kök kullanıcı yerine Identity Center kullanıcısı), beklenmedik harcamaya karşı bütçe alarmı kuruldu, geliştirme araçları kuruldu, GitHub deposu açıldı ve ileride AWS'e dağıtılacak küçük bir Flask uygulaması testleriyle birlikte yazıldı. Uygulama, root olmayan bir kullanıcıyla çalışan küçük bir Docker imajına paketlendi.

| Çıktı | Durum |
|---|---|
| Kök kullanıcıda MFA, günlük iş için ayrı kullanıcı | Tamam |
| Aylık bütçe alarmı (20 USD, üç eşik) | Tamam |
| AWS CLI ile SSO girişi | Tamam |
| GitHub deposu ve `main` koruması | Tamam |
| Flask uygulaması, 2 test, lint temiz | Tamam |
| Docker imajı, root olmayan kullanıcı | Tamam |

## Bu haftanın kavramları

| Kavram | Açıklama |
|---|---|
| **Kök (root) kullanıcı** | AWS hesabını açan e-posta kimliği. Sınırsız yetkisi vardır, bu yüzden günlük işte kullanılmaz, sadece MFA ile korunup saklanır. |
| **MFA** | Şifrenin yanında ikinci bir doğrulama (telefon uygulaması). |
| **IAM Identity Center** | AWS'te kullanıcıları ve izinlerini yöneten merkezi giriş sistemi (eski adı AWS SSO). |
| **Permission set** | Bir kullanıcının hesapta ne yapabileceğini tanımlayan izin paketi. |
| **AWS Budgets** | Harcama belirli bir eşiği geçerse e-posta gönderen bütçe alarmı. |
| **Cost Explorer** | Harcamaları grafik ve tabloyla inceleme aracı. |
| **Flask** | Python için küçük bir web uygulaması çatısı. |
| **Gunicorn** | Flask uygulamasını gerçek sunucuda çalıştıran sunucu yazılımı. |
| **Docker imajı** | Uygulamanın ve bağımlılıklarının taşınabilir paketi. |
| **Multi-stage build** | İmajı iki aşamada derleyip yalnızca gerekenleri son imaja almak (daha küçük ve güvenli imaj). |

## Yapılanlar

### Gün 1: AWS hesap güvenliği ve bütçe alarmı

1. Kök kullanıcıya **MFA** eklendi. Kök kullanıcı için erişim anahtarı (access key) **oluşturulmadı** ve günlük iş için kullanılmadı.
2. Faturalama ayarlarında "IAM kullanıcılarının faturalama bilgisine erişimi" açıldı.
3. **IAM Identity Center** etkinleştirildi. Bölge bilinçli olarak `eu-central-1` (Frankfurt) seçildi, çünkü bu seçim sonradan değiştirilemiyor.
4. Bir kullanıcı oluşturuldu, `AdministratorAccess` izin paketi atandı, MFA zorunlu kılındı ve **AWS access portal** adresi not alındı.
5. **AWS Budgets** ile aylık 20 USD'lik bütçe tanımlandı. Üç alarm var: gerçekleşen harcama %50, gerçekleşen harcama %80 ve **tahmini** harcama %100. Alarmlar e-postaya gelir.
6. **Cost Explorer** etkinleştirildi (veriler yaklaşık 24 saat sonra görünür).

> **Ekran görüntüsü:** Budgets sayfasında üç alarmlı bütçe.
> **Ekran görüntüsü:** Identity Center portalına MFA ile giriş.

### Gün 2: Araçlar ve AWS CLI

Şu araçlar kuruldu ve sürümleri doğrulandı: `git`, `docker`, `python3` (3.12), `aws` (CLI v2), `terraform` (1.10 veya üstü).

AWS CLI'a SSO oturumuyla bağlanıldı:

```
aws configure sso          # session name: finops, profile name: finops-dev
aws sso login --profile finops-dev
aws sts get-caller-identity
```

`Token has expired` hatası SSO oturumunun süresinin dolduğunu gösterir, çözüm yeniden `aws sso login`.

### Gün 3: GitHub deposu

`cost-aware-cicd-aws` adıyla depo açıldı. `main` dalı için "birleştirmeden önce pull request zorunlu" kuralı eklendi (Hafta 3'te bu kural durum kontrolleriyle genişletildi). Çalışma biçimi:

- Her iş için ayrı dal (`feature/...`), PR ile birleştirme.
- Commit mesaj önekleri: `feat:`, `fix:`, `docs:`, `chore:`, `ci:`.

### Gün 4-5: Örnek uygulama

Uygulama bilinçli olarak küçük tutuldu, çünkü projenin odağı uygulama değil, onu dağıtan ve denetleyen hattır.

| Dosya | Görev |
|---|---|
| `app/main.py` | Flask uygulaması. `GET /` karşılama mesajı ve sürüm, `GET /health` sağlık kontrolü (`{"status":"ok"}`, HTTP 200) |
| `app/test_main.py` | 2 pytest testi (iki uç nokta) |
| `app/requirements.txt` | `flask==3.0.3`, `gunicorn==22.0.0` |
| `app/requirements-dev.txt` | geliştirme araçları: `pytest==8.3.3`, `ruff==0.6.9` |

Sürüm bilgisi `APP_VERSION` ortam değişkeninden okunur. Bu sayede ileride dağıtılan imajın hangi sürüm olduğu doğrudan uygulamanın yanıtından görülebilir. `/health` ucu ileride dağıtım sonrası sağlık kontrolünde ve otomatik geri almada kullanılacak.

Yerel doğrulama:

```
cd app
python3 -m venv .venv
pip install -r requirements-dev.txt
pytest          # 2 test geçmeli
ruff check .    # temiz çıkmalı
flask --app main run --port 8080
curl localhost:8080/health
```

### Gün 6: Docker

`app/Dockerfile` şu kararlarla yazıldı:

| Karar | Gerekçe |
|---|---|
| **Multi-stage build** | Derleme araçları son imaja girmez, imaj küçülür |
| **`python:3.12-slim` taban imaj** | Daha az paket, daha az zafiyet yüzeyi |
| **Root olmayan kullanıcı** (`appuser`, uid 10001) | Uygulama ele geçirilse bile yetkisi sınırlı kalır |
| **Gunicorn**, `--bind 0.0.0.0:8080 --workers 2` | Flask'ın geliştirme sunucusu üretimde kullanılmaz |
| **Sabit bağımlılık sürümleri** | Derlemenin tekrarlanabilir olması |

Doğrulama:

```
docker build -t finops-app:local ./app
docker run --rm -p 8080:8080 -e APP_VERSION=1.0.0 finops-app:local
curl localhost:8080/health
docker run --rm finops-app:local id      # uid=10001(appuser) görülmeli
```

> **Ekran görüntüsü:** `id` komutunun `appuser` çıktısı.

## Alınan kararlar ve gerekçeleri

| Karar | Gerekçe |
|---|---|
| Kök kullanıcı yerine Identity Center kullanıcısı | Kök kullanıcı çalınırsa tüm hesap gider. Günlük kullanıcıda izin ve oturum süresi kontrol edilebilir |
| Bölge `eu-central-1` | Türkiye'ye yakın, tüm servisler mevcut, tüm proje tek bölgede |
| 20 USD bütçe, üç alarm | Ücretsiz kredi içinde kalmayı ve sürprizleri erken görmeyi sağlar. Tahmini (forecast) alarm, harcama gerçekleşmeden uyarır |
| Küçük, sade uygulama | Proje uygulamayı değil, uygulamayı **dağıtan ve denetleyen** hattı geliştiriyor |
| `/health` ucu | Dağıtım sonrası otomatik sağlık kontrolü ve geri alma için |

## Karşılaşılabilecek sorunlar

| Belirti | Neden | Çözüm |
|---|---|---|
| `Token has expired` | SSO oturumu bitti | `aws sso login --profile finops-dev` |
| Cost Explorer boş | Veri henüz oluşmadı | 24 saat bekle |
| `docker: Cannot connect to the Docker daemon` | Docker Desktop kapalı | Docker Desktop'ı başlat |
| Port 8080 dolu | Başka bir süreç kullanıyor | Süreci kapat ya da `-p 8081:8080` kullan |

## Maliyet

AWS'te bu hafta hiçbir kaynak oluşturulmadı. Maliyet sıfırdır. Bütçe alarmı yalnızca koruma amaçlıdır.

## Sınırlamalar

- Uygulama bilerek basit. Veri tabanı, kimlik doğrulama gibi bileşenler kapsam dışı.
- Docker imajı bu aşamada yalnızca yerelde çalıştırıldı. AWS'e gönderimi Hafta 2'de yapıldı, otomatikleştirilmesi Hafta 5'te yapılacak.

## Kontrol listesi

- [x] Kök kullanıcıda MFA
- [x] Identity Center kullanıcısı ile portala MFA girişi
- [x] Budgets onay e-postası geldi
- [x] `aws sts get-caller-identity` hesap bilgisini döndürüyor
- [x] Depo ve `main` koruması
- [x] 2 test geçiyor, `ruff` temiz
- [x] İmaj `appuser` ile çalışıyor

## Rapora aktarım için

- "Güvenlik temeli" bölümü: MFA, en az yetki, bütçe alarmı.
- "Konteynerleştirme" bölümü: multi-stage, slim taban, root olmayan kullanıcı, sabit sürümler.

## Gereken ekran görüntüleri (`docs/img/`)

1. `h1-budgets.png`: Budgets sayfası, üç alarm
2. `h1-sso-login.png`: Identity Center portalı
3. `h1-docker-id.png`: `id` çıktısında `appuser`
