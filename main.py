import os
import requests
import numpy as np

# --- GİRDİLER VE PARAMETRELER ---
TELEGRAM_TOKEN = "8804198622:AAG0OasCmjkqKDTuics9XHXhFCh9Hn48Arc"
CHAT_ID = "5919163268"

WHALE_Z = 2.0         # Balina Hacim Eşiği (Z-Score)
FUND_MAX = 0.05       # Maks. Funding % (AL için)
FUND_MIN = -0.05      # Min. Funding % (SAT için)
VOL_LEN = 50          # Hacim Ortalaması Periyodu

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram hatasi: {e}")

def get_futures_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    res = requests.get(url).json()
    symbols = [s['symbol'] for s in res['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
    return symbols

def analyze_symbol(symbol):
    try:
        # Kapanış ve Hacim Verilerini Çek (4 saatlik / 240m mumlar)
        klines_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=4h&limit={VOL_LEN + 1}"
        kres = requests.get(klines_url, timeout=5).json()
        if len(kres) < VOL_LEN:
            return

        closes = np.array([float(k[4]) for k in kres])
        volumes = np.array([float(k[5]) for k in kres])

        # Z-Score Hesabı
        avg_v = np.mean(volumes[-VOL_LEN:-1])
        std_v = np.std(volumes[-VOL_LEN:-1])
        current_vol = volumes[-1]
        z_score = (current_vol - avg_v) / std_v if std_v > 0 else 0

        # Z-Skor Eşiği Geçilmediyse Taramayı Hızlıca Geç (Performans için)
        if z_score < WHALE_Z:
            return

        # Open Interest (OI) Değişimi Çek
        oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
        oi_res = requests.get(oi_url, timeout=5).json()
        current_oi = float(oi_res['openInterest'])
        
        # Funding Rate Çek
        fund_url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
        fund_res = requests.get(fund_url, timeout=5).json()
        fund_rate = float(fund_res['lastFundingRate']) * 100

        # Sinyal Koşul Kontrolleri
        price_up = closes[-1] > closes[-2]
        
        # Basitleştirilmiş Balina Mantığı: Z > 2.0 ve Pozitif Hacim + Uygun Funding
        if price_up and fund_rate < FUND_MAX:
            msg = (
                f"🚀 *WHALEFLOWPRO - BALİNA SİNYALİ (AL)*\n\n"
                f"🪙 *Coin:* `{symbol}`\n"
                f"📊 *Z-Skor (Hacim):* `{z_score:.2f}` *(Balina Eşiği > {WHALE_Z} Aşıldı)*\n"
                f"💸 *Funding Rate:* `%{fund_rate:.4f}`\n"
                f"📈 *Fiyat:* `{closes[-1]}`\n\n"
                f"🔗 [TradingView Grafiği Aç](https://www.tradingview.com/chart/?symbol=BINANCE:{symbol})"
            )
            send_telegram(msg)

        elif not price_up and fund_rate > FUND_MIN:
            msg = (
                f"🔻 *WHALEFLOWPRO - BALİNA SİNYALİ (SAT)*\n\n"
                f"🪙 *Coin:* `{symbol}`\n"
                f"📊 *Z-Skor (Hacim):* `{z_score:.2f}` *(Balina Eşiği > {WHALE_Z} Aşıldı)*\n"
                f"💸 *Funding Rate:* `%{fund_rate:.4f}`\n"
                f"📉 *Fiyat:* `{closes[-1]}`\n\n"
                f"🔗 [TradingView Grafiği Aç](https://www.tradingview.com/chart/?symbol=BINANCE:{symbol})"
            )
            send_telegram(msg)

    except Exception as e:
        pass

def main():
    symbols = get_futures_symbols()
    print(f"Toplam {len(symbols)} adet vadeli coin taranıyor...")
    for sym in symbols:
        analyze_symbol(sym)

if __name__ == "__main__":
    main()