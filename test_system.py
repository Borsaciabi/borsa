import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database.models import init_db
from analysis.value_analysis import ValueAnalyzer
from analysis.technical_analysis import TechnicalAnalyzer

print("="*60)
print("  PYTHON BORSA - SISTEM TESTI")
print("="*60)

# 1. Veritabani
print("\n[1] Veritabani olusturuluyor...")
init_db()
print("    OK - data/borsa.db olusturuldu")

# 2. Deger Analizi
print("\n[2] Deger analizi testi (A1CAP)...")
va = ValueAnalyzer()
r = va.analyze("A1CAP")
if r:
    print(f"    Fiyat: {r['current_price']:.2f} TL")
    print(f"    Deger: {r['calculated_value']:.2f} TL")
    print(f"    Oran:  {r['ratio']:.2f}")
    print(f"    Sinyal: {r['signal_emoji']} {r['signal']}")
    print(f"    Kar:   %{r['expected_return']:.1f}")
    print("    OK")
else:
    print("    FAIL - Veri cekilemedi")

# 3. THYAO Test
print("\n[3] Deger analizi testi (THYAO)...")
r2 = va.analyze("THYAO")
if r2:
    print(f"    Fiyat: {r2['current_price']:.2f} TL")
    print(f"    Deger: {r2['calculated_value']:.2f} TL")
    print(f"    Oran:  {r2['ratio']:.2f}")
    print(f"    Sinyal: {r2['signal_emoji']} {r2['signal']}")
    print(f"    Kar:   %{r2['expected_return']:.1f}")
    print("    OK")
else:
    print("    FAIL")

# 4. Teknik Analiz
print("\n[4] Teknik analiz testi (A1CAP)...")
ta = TechnicalAnalyzer()
t = ta.analyze("A1CAP")
if t:
    print(f"    Fiyat: {t['current_price']:.2f}")
    print(f"    RSI:   {t['rsi']:.1f}" if t['rsi'] else "    RSI: N/A")
    print(f"    MA200: {t['ma200']:.2f}" if t['ma200'] else "    MA200: N/A")
    print("    OK")
else:
    print("    FAIL")

print("\n" + "="*60)
print("  TEST TAMAMLANDI")
print("="*60)
