import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from fpdf import FPDF
from analysis.value_analysis import ValueAnalyzer
from analysis.technical_analysis import TechnicalAnalyzer
from data.fetchers.bist_fetcher import BistFetcher


class BorsaPDF(FPDF):
    """Ozel PDF sinifi."""

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Python Borsa Analiz Raporu", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, datetime.now().strftime("%d/%m/%Y %H:%M"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Sayfa {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(41, 128, 185)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def add_row(self, label, value, bold=False):
        self.set_font("Helvetica", "B" if bold else "", 10)
        self.cell(80, 6, label, new_x="RIGHT")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, str(value), new_x="LMARGIN", new_y="NEXT")

    def add_signal(self, signal, emoji):
        self.set_font("Helvetica", "B", 14)
        if "SAT" in signal:
            self.set_text_color(255, 0, 0)
        elif "AL" in signal:
            self.set_text_color(0, 128, 0)
        elif "Borclu" in signal:
            self.set_text_color(128, 128, 128)
        else:
            self.set_text_color(255, 165, 0)
        self.cell(0, 10, f"Sinyal: {emoji} {signal}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)


class PDFGenerator:
    """PDF rapor uretici."""

    def __init__(self):
        self.va = ValueAnalyzer()
        self.ta = TechnicalAnalyzer()
        self.bist = BistFetcher()

    def generate_stock_report(self, symbol: str, output_path: str = None) -> str:
        """Tekil hisse icin PDF rapor olusturur."""
        if output_path is None:
            output_path = f"reports/daily/{symbol}_rapor_{datetime.now().strftime('%Y%m%d')}.pdf"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Verileri cek
        value_data = self.va.analyze(symbol)
        tech_data = self.ta.analyze(symbol)

        pdf = BorsaPDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        # Deger Analizi
        if value_data:
            pdf.section_title("DEGER ANALIZI")
            pdf.add_row("Hisse Kodu", value_data["symbol"], bold=True)
            pdf.add_row("Sirket", value_data.get("description", ""))
            pdf.add_row("Son Fiyat", f"{value_data['current_price']:.2f} TL")
            pdf.add_row("Piyasa Degeri", f"{value_data['market_cap_mn']:,.1f} M TL")
            pdf.add_row("Net Borc", f"{value_data['net_debt_mn']:,.1f} M TL")
            pdf.add_row("Fiili Dolasim", f"%{value_data['float_rate']}")
            pdf.add_row("Toplam Hisse", f"{value_data['total_shares']:,.0f}")
            pdf.add_row("Fiili Dolasim Hisse", f"{value_data['floating_shares']:,.0f}")
            pdf.ln(3)
            pdf.add_row("Hesaplanan Deger", f"{value_data['calculated_value']:.2f} TL", bold=True)
            pdf.add_row("Oran (Fiyat/Deger)", f"{value_data['ratio']:.2f}", bold=True)
            pdf.add_row("Kar Beklentisi", f"%{value_data['expected_return']:.1f}")
            pdf.ln(3)
            pdf.add_signal(value_data["signal"], value_data["signal_emoji"])
        else:
            pdf.section_title("DEGER ANALIZI")
            pdf.cell(0, 8, "Veri bulunamadi", new_x="LMARGIN", new_y="NEXT")

        # Teknik Analiz
        if tech_data:
            pdf.add_page()
            pdf.section_title("TEKNIK ANALIZ")
            pdf.add_row("Son Fiyat", f"{tech_data['current_price']:.2f} TL")
            pdf.add_row("RSI (14)", f"{tech_data['rsi']:.1f}" if tech_data['rsi'] else "N/A")
            pdf.add_row("MACD", f"{tech_data['macd']:.4f}" if tech_data['macd'] else "N/A")
            pdf.add_row("MACD Signal", f"{tech_data['macd_signal']:.4f}" if tech_data['macd_signal'] else "N/A")
            pdf.ln(3)
            pdf.add_row("MA20", f"{tech_data['ma20']:.2f} TL" if tech_data['ma20'] else "N/A")
            pdf.add_row("MA50", f"{tech_data['ma50']:.2f} TL" if tech_data['ma50'] else "N/A")
            pdf.add_row("MA200", f"{tech_data['ma200']:.2f} TL" if tech_data['ma200'] else "N/A")
            pdf.ln(3)
            diff200 = tech_data.get("price_vs_ma200")
            diff50 = tech_data.get("price_vs_ma50")
            pdf.add_row("Fiyat/MA200", f"%{diff200:.1f}" if diff200 else "N/A")
            pdf.add_row("Fiyat/MA50", f"%{diff50:.1f}" if diff50 else "N/A")
            pdf.add_row("Hacim", f"{tech_data['volume']:,.0f}" if tech_data['volume'] else "N/A")
            pdf.add_row("Hacim Ort (20g)", f"{tech_data['volume_avg_20']:,.0f}" if tech_data['volume_avg_20'] else "N/A")

            # RSI Yorumu
            pdf.ln(3)
            if tech_data['rsi']:
                if tech_data['rsi'] < 30:
                    pdf.add_row("RSI Yorumu", "Asiri satim bolgesinde - ALIM firsati")
                elif tech_data['rsi'] > 70:
                    pdf.add_row("RSI Yorumu", "Asiri alim bolgesinde - SATIM sinyali")
                else:
                    pdf.add_row("RSI Yorumu", "Notr bolgede")

        # Sinyal Tablosu
        pdf.add_page()
        pdf.section_title("SINYAL TABLOSU")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, "Oran Araligi", border=1, align="C")
        pdf.cell(50, 7, "Sinyal", border=1, align="C")
        pdf.cell(50, 7, "Durum", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

        signals = [
            ("> 3,00", "Hemen SAT", "Kesinlikle satilmali"),
            ("> 1,50", "SAT", "Satismci olunmali"),
            ("> 0,99", "Kafana Gore", "Size kalmis"),
            ("> 0,70", "AL", "Alim firsati"),
            ("> 0,000001", "Evi Barki Sat", "Cok buyuk firsat"),
            ("< 0", "Borclu", "Dikkatli ol"),
        ]
        for range_str, signal_name, desc in signals:
            is_current = value_data and value_data["signal"] == signal_name
            if is_current:
                pdf.set_fill_color(200, 255, 200)
                pdf.cell(50, 7, range_str, border=1, align="C", fill=True)
                pdf.cell(50, 7, signal_name, border=1, align="C", fill=True)
                pdf.cell(50, 7, desc, border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
                pdf.set_fill_color(255, 255, 255)
            else:
                pdf.cell(50, 7, range_str, border=1, align="C")
                pdf.cell(50, 7, signal_name, border=1, align="C")
                pdf.cell(50, 7, desc, border=1, align="C", new_x="LMARGIN", new_y="NEXT")

        # Alt bilgi
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "Bu rapor otomatik olusturulmustur. Yatirim tavsiyesi degildir.",
                 align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.output(output_path)
        return output_path

    def generate_portfolio_report(self, user_id: int, positions: list, output_path: str = None) -> str:
        """Portfoy raporu olusturur."""
        if output_path is None:
            output_path = f"reports/daily/portfoy_{datetime.now().strftime('%Y%m%d')}.pdf"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        pdf = BorsaPDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.section_title("PORTFOY RAPORU")

        if not positions:
            pdf.cell(0, 8, "Portfoyde hisse bulunmuyor.", new_x="LMARGIN", new_y="NEXT")
        else:
            toplam_deger = 0
            toplam_kar = 0

            for pos in positions:
                symbol = pos["stock_code"]
                qty = pos["net_quantity"]
                avg_price = pos["avg_buy_price"]

                # Guncel fiyati cek
                current = self.bist.get_price(symbol)
                if current is None:
                    current = avg_price

                deger = current * qty
                kar = (current - avg_price) * qty
                kar_yuzde = ((current / avg_price) - 1) * 100 if avg_price > 0 else 0

                toplam_deger += deger
                toplam_kar += kar

                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 7, f"{symbol}", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                pdf.add_row("Miktar", f"{qty} adet")
                pdf.add_row("Ort. Alis", f"{avg_price:.2f} TL")
                pdf.add_row("Guncel Fiyat", f"{current:.2f} TL")
                pdf.add_row("Deger", f"{deger:,.2f} TL")
                pdf.add_row("Kar/Zarar", f"{kar:+,.2f} TL (%{kar_yuzde:+.1f})")
                pdf.ln(3)

            pdf.section_title("PORTFOY OZET")
            pdf.add_row("Toplam Deger", f"{toplam_deger:,.2f} TL", bold=True)
            pdf.add_row("Toplam Kar/Zarar", f"{toplam_kar:+,.2f} TL", bold=True)
            pdf.add_row("Hisse Sayisi", f"{len(positions)}")

        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "Bu rapor otomatik olusturulmustur. Yatirim tavsiyesi degildir.",
                 align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.output(output_path)
        return output_path

    def generate_daily_market_report(self, symbols: list = None) -> str:
        """Gunluk piyasa raporu olusturur."""
        if symbols is None:
            symbols = ["THYAO", "GARAN", "AKBNK", "SISE", "ASELS", "BIMAS", "KCHOL"]

        output_path = f"reports/daily/piyasa_{datetime.now().strftime('%Y%m%d')}.pdf"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        pdf = BorsaPDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.section_title("GUNLUK PIYASA RAPORU")

        for symbol in symbols:
            result = self.va.analyze(symbol)
            if result:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 7, f"{symbol} - {result.get('description', '')[:30]}",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                pdf.add_row("Fiyat", f"{result['current_price']:.2f} TL")
                pdf.add_row("Deger", f"{result['calculated_value']:.2f} TL")
                pdf.add_row("Sinyal", f"{result['signal']}")
                pdf.add_row("Kar Beklentisi", f"%{result['expected_return']:.1f}")
                pdf.ln(2)

        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "Bu rapor otomatik olusturulmustur. Yatirim tavsiyesi degildir.",
                 align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.output(output_path)
        return output_path


if __name__ == "__main__":
    gen = PDFGenerator()
    path = gen.generate_stock_report("A1CAP")
    print(f"PDF olusturuldu: {path}")
