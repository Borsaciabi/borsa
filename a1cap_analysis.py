import borsapy as bp
import yfinance as yf
import pandas as pd

print("=" * 60)
print("       A1CAP - DEFTER DEGERI VE GERCEK DEGER ANALIZI")
print("=" * 60)

ticker = bp.Ticker("A1CAP")
info = ticker.info
bs = ticker.balance_sheet

fiyat = info["last"]
piyasa_degeri = info["marketCap"]
toplam_hisse = info["sharesOutstanding"]
net_borc_borsapy = info["netDebt"]
float_oran = info["floatShares"]
pe = info["trailingPE"]
pb = info["priceToBook"]
ma200 = info["twoHundredDayAverage"]
ma50 = info["fiftyDayAverage"]
w52_high = info["fiftyTwoWeekHigh"]
w52_low = info["fiftyTwoWeekLow"]

col = "2025"
col_idx = bs.columns.get_loc(col)

# Indeks numaralarini kullanarak degerleri cek (encoding sorunu var)
def get_val(row_num):
    return float(bs.iloc[row_num, col_idx])

toplam_varlik = get_val(28)        # TOPLAM VARLIKLAR
nakit = get_val(1)                 # Nakit ve Nakit Benzerleri
kv_toplam = get_val(30)            # Kisa Vadeli Yukumlulukler
uv_toplam = get_val(44)            # Uzun Vadeli Yukumlulukler
oz_sermaye = get_val(57)           # Ozkaynaklar
odenmis_sermaye = get_val(59)      # Odenmis Sermaye
donem_kari = get_val(66)           # Donem Net Kar/Zarari

# Finansal borclari da cekelim (individually find them)
# KV Finansal Borclar idx=31
kv_finansal_borc = get_val(31)
uv_finansal_borc = get_val(45)
toplam_finansal_borc = kv_finansal_borc + uv_finansal_borc

print()
print("  Guncel Fiyat:            {:>12.2f} TL".format(fiyat))
print("  Onceki Kapanis:          {:>12.2f} TL".format(info["prev_close"]))
print("  Degisim:                 {:>+12.2f} TL ({:+.1f}%)".format(info["change"], info["change_percent"]))

print()
print("-" * 60)
print("  1. BILANCO VERILERI (2025)")
print("-" * 60)
print("  Toplam Varliklar:        {:>20,.0f} TL".format(toplam_varlik))
print("  Nakit ve Nakit Benzeri:  {:>20,.0f} TL".format(nakit))
print()
print("  --- Kisa Vadeli ---")
print("  Finansal Borclar:        {:>20,.0f} TL".format(kv_finansal_borc))
print("  KV Toplam:               {:>20,.0f} TL".format(kv_toplam))
print()
print("  --- Uzun Vadeli ---")
print("  Finansal Borclar:        {:>20,.0f} TL".format(uv_finansal_borc))
print("  UV Toplam:               {:>20,.0f} TL".format(uv_toplam))
print()
print("  Toplam Finansal Borc:    {:>20,.0f} TL".format(toplam_finansal_borc))
print("  Toplam Yukumlulukler:    {:>20,.0f} TL".format(kv_toplam + uv_toplam))
print("  Oz Sermaye:              {:>20,.0f} TL".format(oz_sermaye))
print("  Donem Kar/Zarar:         {:>20,.0f} TL".format(donem_kari))
print("  Odenmis Sermaye:         {:>20,.0f} TL".format(odenmis_sermaye))

print()
print("-" * 60)
print("  2. HISSE BILGILERI")
print("-" * 60)
fiili_dolasim_hisse = toplam_hisse * float_oran / 100
print("  Toplam Hisse Sayisi:     {:>20,.0f}".format(toplam_hisse))
print("  Fiili Dolasim Orani:     %{}".format(float_oran))
print("  Fiili Dolasim Hisse:     {:>20,.0f}".format(fiili_dolasim_hisse))

print()
print("-" * 60)
print("  3. BORC ve NAKIT KARSILASTIRMASI")
print("-" * 60)
net_borc_bilanco = toplam_finansal_borc - nakit

ticker_yf = yf.Ticker("A1CAP.IS")
info_yf = ticker_yf.info
toplam_borc_yf = info_yf.get("totalDebt", 0) or 0
toplam_nakit_yf = info_yf.get("totalCash", 0) or 0
kitap_degeri_yf = info_yf.get("bookValue", 0) or 0
net_borc_yf = toplam_borc_yf - toplam_nakit_yf

print("  [borsapy]  Net Borc:     {:>20,.0f} TL".format(net_borc_borsapy))
print("  [yfinance] Toplam Borc:  {:>20,.0f} TL".format(toplam_borc_yf))
print("  [yfinance] Toplam Nakit: {:>20,.0f} TL".format(toplam_nakit_yf))
print("  [yfinance] Net Borc:     {:>20,.0f} TL".format(net_borc_yf))
print("  [Bilanco]  Finansal Borc:{:>20,.0f} TL".format(toplam_finansal_borc))
print("  [Bilanco]  Net Borc:     {:>20,.0f} TL".format(net_borc_bilanco))

print()
print("-" * 60)
print("  4. DEFTER DEGERI HESABI")
print("-" * 60)

defter_degeri_toplam = oz_sermaye / toplam_hisse
defter_degeri_fiili = oz_sermaye / fiili_dolasim_hisse
pd_dd = fiyat / defter_degeri_toplam

print("  Oz Sermaye:              {:>20,.0f} TL".format(oz_sermaye))
print("  Toplam Hisse:            {:>20,.0f}".format(toplam_hisse))
print("  Fiili Dolasim Hisse:     {:>20,.0f}".format(fiili_dolasim_hisse))
print()
print("  Defter Degeri (Toplam):  {:>20.2f} TL/hisse".format(defter_degeri_toplam))
print("  Defter Degeri (Fiili):   {:>20.2f} TL/hisse".format(defter_degeri_fiili))
print("  Guncel Fiyat:            {:>20.2f} TL".format(fiyat))
print("  PD/DD (Fiyat/Kitap):     {:>20.2f}x".format(pd_dd))
print("  [yfinance P/B]:          {:>20}".format(pb))
print("  [yfinance Book Value]:   {:>20} TL/hisse".format(kitap_degeri_yf))

print()
print("-" * 60)
print("  5. GERCEK DEGER (ENTERPRISE VALUE - NET BORC)")
print("-" * 60)

net_borc = net_borc_yf
enterprise_value = piyasa_degeri + net_borc
gercek_deger_toplam = enterprise_value / toplam_hisse
gercek_deger_fiili = enterprise_value / fiili_dolasim_hisse

print("  Piyasa Degeri:           {:>20,.0f} TL".format(piyasa_degeri))
print("  Net Borc:                {:>20,.0f} TL".format(net_borc))
print("  Enterprise Value:        {:>20,.0f} TL".format(enterprise_value))
print()
print("  Hisse Basina Gercek Deger (Toplam Hisse):  {:>8.2f} TL".format(gercek_deger_toplam))
print("  Hisse Basina Gercek Deger (Fiili Dolasim): {:>8.2f} TL".format(gercek_deger_fiili))
print()

iskonto = (1 - fiyat / gercek_deger_toplam) * 100
print("  Guncel Fiyat:            {:>20.2f} TL".format(fiyat))
print("  Gercek Deger:            {:>20.2f} TL".format(gercek_deger_toplam))
print("  Fiyat/Gercek Deger:      {:>20.2f}".format(fiyat / gercek_deger_toplam))
if iskonto > 0:
    print("  ISKONTO:                 {:>20.1f}%".format(iskonto))
else:
    print("  PREMIUM:                 {:>20.1f}%".format(abs(iskonto)))

print()
print("-" * 60)
print("  6. 200 GUNLUK TEKNIK OZET")
print("-" * 60)
print("  200 Gunluk Ortalama:     {:>20.2f} TL".format(ma200))
ma200_fark = ((fiyat / ma200) - 1) * 100
print("  Fiyat vs MA200:          {:>+20.1f}%".format(ma200_fark))
print("  50 Gunluk Ortalama:      {:>20.2f} TL".format(ma50))
print("  52 Hafta En Dusuk:       {:>20.2f} TL".format(w52_low))
print("  52 Hafta En Yuksek:      {:>20.2f} TL".format(w52_high))

print()
print("-" * 60)
print("  7. TEMEL ORANLAR")
print("-" * 60)
print("  F/K (Fiyat/Kazanc):      {:>20.1f}x".format(pe))
print("  PD/DD (Fiyat/Kitap):     {:>20.2f}x".format(pd_dd))
eps = fiyat / pe
print("  Hisse B. Kazanc (EPS):   {:>20.2f} TL".format(eps))

print()
print("=" * 60)
print("  OZET TABLO")
print("=" * 60)
rows = [
    ("Guncel Fiyat", "{:.2f} TL".format(fiyat)),
    ("Piyasa Degeri", "{:.2f} M TL".format(piyasa_degeri / 1e6)),
    ("Oz Sermaye", "{:.2f} M TL".format(oz_sermaye / 1e6)),
    ("Defter Degeri (Toplam)", "{:.2f} TL".format(defter_degeri_toplam)),
    ("Defter Degeri (Fiili)", "{:.2f} TL".format(defter_degeri_fiili)),
    ("Gercek Deger (Toplam)", "{:.2f} TL".format(gercek_deger_toplam)),
    ("Gercek Deger (Fiili)", "{:.2f} TL".format(gercek_deger_fiili)),
    ("F/K Orani", "{:.1f}".format(pe)),
    ("PD/DD Orani", "{:.2f}".format(pd_dd)),
    ("Iskonto/Premium", "%{:.1f}".format(iskonto)),
]
for metrik, deger in rows:
    print("  |{:<30}|{:<20}|".format(metrik, deger))
print("=" * 60)
