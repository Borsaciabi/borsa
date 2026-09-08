# PythonAnywhere Kurulum Kilavuzu (Free Plan)

## Onemli Not
Bu kurulum **Free plan** icindir. Free plan'da:
- Always-on task **YOK** (15 dk otomatik guncelleme calismaz)
- Fiyat guncellemesi **manuel** yapilir (Dashboard'daki buton)
- 512 MB disk, 100 CPU saniye/gun
- 36 gun/ay uptime

## Adim 1: Hesap Olustur
1. https://www.pythonanywhere.com/ adresine git
2. "Create a Beginner account" sec (ucretsiz)
3. Kayit ol

## Adim 2: Konsol Ac
1. Dashboard > Consoles > "Start a new console: Bash" tikla

## Adim 3: Zip Dosyasini Ac
```bash
cd ~
ls
```
Zip dosyasini bul (orn: `Python_Borsa.zip` veya `borsa.zip`). Sonra:
```bash
unzip "DOSYA_ADI.zip" -d borsa
cd borsa
ls
```
`app.py`, `wsgi.py`, `requirements.txt` dosyalarini gorunmeli.

## Adim 4: Virtual Environment Olustur
```bash
python3.10 -m venv venv
source venv/bin/activate
```

## Adim 5: Kutuphaneleri Yukle
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
2-5 dakika surebilir, bekleyin.

## Adim 6: .env Olustur
```bash
cp .env.example .env
nano .env
```
Icindekileri boyle degistirin (Ctrl+X ile kaydedin):

```
JWT_SECRET_KEY=buraya-rastgele-bir-sifre
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
TELEGRAM_BOT_TOKEN=
DATABASE_URL=sqlite:///home/hayatadair/borsa/data/borsa.db
CACHE_TTL_SECONDS=300
RATE_LIMIT_PER_MINUTE=60
PRICE_UPDATE_MINUTES=15
BACKUP_ENABLED=true
```

> **ONEMLI:** `hayatadair` yerine kendi PythonAnywhere kullanici adinizi yazin.
> `whoami` komutu ile ogrenebilirsiniz.

Rastgele sifre uretmek icin:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Adim 7: Veritabanini Baslat
```bash
mkdir -p data/cache
python3 -c "from data.database.models import init_db; init_db()"
```

## Adim 8: WSGI Dosyasini Olustur
```bash
nano wsgi.py
```
Asagidaki icerigi yapistirin (Ctrl+X ile kaydedin):

```python
import sys
import os

project_home = '/home/hayatadair/borsa'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
```

> **ONEMLI:** `hayatadair` yerine kendi kullanici adinizi yazin.

## Adim 9: Web Uygulamasini Ayarla (Web Arayuzu)
Bu adimlar **web arayuzunden** yapilir:

1. Dashboard > **Web** sekmesi > **Add a new web app** tikla
2. **Manual configuration** sec
3. **Python 3.10** sec
4. Asagidaki ayarlari yapin:

```
Source code:        /home/hayatadair/borsa
Working directory:  /home/hayatadair/borsa
WSGI config file:   /home/hayatadair/borsa/wsgi.py
```

5. **Virtualenv** bolumune yazin:
```
/home/hayatadair/borsa/venv
```

6. **Reload** butonuna basin

## Adim 10: Test Edin
Tarayicinda acin:
```
https://hayatadair.pythonanywhere.com
```

Kontrol edin:
- Ana sayfa acilmali
- /docs -> API docs acilmali
- /dashboard -> Dashboard acilmali

## Free Plan'da Fiyat Guncelleme
Free plan'da otomatik guncelleme yoktur. Manuel olarak:
1. Dashboard'a gidin
2. "Fiyat Guncelle" butonuna tiklayin
3. Fiyatlar guncellenir (~5-10 saniye)

Isterseniz kendi bilgisayarinizdan da guncelleme yapabilirsiniz:
```bash
# VPN'de veya terminalde
cd /path/to/borsa
python run_all.py
# Dashboard'daki "Fiyat Guncelle" butonu calisir
```

## Sorun Giderme

### "Import could not be resolved" hatasi
```bash
cd ~/borsa
source venv/bin/activate
pip install -r requirements.txt
```

### "Permission denied" hatasi
```bash
chmod -R 755 ~/borsa
```

### "Database locked" hatasi
```bash
pkill -f python
# Sonra Web > Reload
```

### 502 Bad Gateway hatasi
1. WSGI dosyasini kontrol edin (kullanici adi dogru mu?)
2. Web > ERRORS log kontrol edin
3. Reload butonuna basin

### Sayfa Acilmiyor
1. Web > Static files bolumunu kontrol edin
2. Source code dogru mu?
3. WSGI config dogru mu?

## Onemli Dosyalar
```
~/borsa/
├── app.py                    ← FastAPI + Streamlit (tek port)
├── wsgi.py                   ← WSGI yapilandirmasi
├── price_updater_task.py     ← Always-on task (Hacker plan)
├── .env                      ← Gizli ayarlar
├── requirements.txt          ← Kutuphaneler
├── data/
│   ├── borsa.db             ← Veritabani
│   └── cache/
│       ├── stock_data.json  ← Ana cache
│       ├── stock_data_backup.json ← Yedek
│       └── price_update_log.txt   ← Loglar
└── venv/                    ← Virtual environment
```

## Hacker Plan'a Gecis (Opsiyonel)
Eger 15 dakikada bir otomatik guncelleme istiyorsaniz:
1. Dashboard > Account > "Go mixed" veya "Merge" planina gecin ($5/ay)
2. Dashboard > Tasks > "Add new task" ekleyin:
   ```
   /home/hayatadair/borsa/venv/bin/python /home/hayatadair/borsa/price_updater_task.py
   ```
3. Schedule: "Always" secin
4. Task otomatik olarak surekli calisir
