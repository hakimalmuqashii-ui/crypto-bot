import os
import time
import threading
import requests
import pandas as pd
import http.server
import socketserver
from google import genai

# ==================== الإعدادات والمفاتيح ====================
TELEGRAM_BOT_TOKEN = "8937828285:AAEaGxVmUo3xCtliBjr2wi2cBnHSQifRavs"
TELEGRAM_CHAT_ID = "-1004315599153"
GEMINI_API_KEY = "AQ.Ab8RN6KN-O_ceA7cVEf7QsQvMjaYAj1Xvr2LZWqLjG_IOekLAA"

# تهيئة عميل Gemini الرسمي الجديد
client = genai.Client(api_key=GEMINI_API_KEY)

# العملات المستهدفة بالتحليل
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

# خادم ويب مدمج لتلبية متطلبات منصة Render
PORT = int(os.environ.get("PORT", 8080))

class WebServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("البوت يعمل بنجاح 24/7!".encode("utf-8"))

def start_background_web_server():
    with socketserver.TCPServer(("0.0.0.0", PORT), WebServerHandler) as httpd:
        httpd.serve_forever()

def send_telegram_message(message: str):
    """إرسال التحليل إلى تليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في إرسال التليجرام: {e}")

def get_binance_klines(symbol: str, interval: str = "15m", limit: int = 100):
    """جلب بيانات الشموع من بينانس"""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def calculate_indicators(df: pd.DataFrame):
    """حساب المؤشرات الفنية الأساسية"""
    df["MA7"] = df["close"].rolling(window=7).mean()
    df["MA25"] = df["close"].rolling(window=25).mean()
    df["MA99"] = df["close"].rolling(window=99).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
    rs = gain / loss
    df["RSI6"] = 100 - (100 / (1 + rs))
    latest = df.iloc[-1]
    return {
        "current_price": latest["close"],
        "MA7": round(latest["MA7"], 4),
        "MA25": round(latest["MA25"], 4),
        "MA99": round(latest["MA99"], 4),
        "RSI6": round(latest["RSI6"], 2),
        "high_24": round(df["high"].max(), 4),
        "low_24": round(df["low"].min(), 4)
    }

def analyze_market_with_ai(market_data: dict):
    """صياغة التحليل الفني عبر Interactions API الرسمية الجديدة"""
    prompt = f"""
    أنت محلل فني خبير في التداول الفوري (Spot) على بينانس مع التركيز على إدارة المخاطر الصارمة.
    البيانات اللحظية المحدثة للعملات:
    {market_data}
    
    المطلوب منك تقرير مرتب ومباشر باللغة العربية مع الالتزام بالشروط التالية:
    1. ممنوع منعاً باتاً استخدام أي جداول نهائياً. استخدم الأسطر والقوائم النقطية فقط.
    2. وضّح هل السوق مناسب للشراء حالياً أم الأفضل الانتظار.
    3. إذا وجدت فرصة شراء مناسبة، اذكر الأرقام الدقيقة:
       - سعر الشراء المعلق (Limit Buy).
       - أرقام أمر OCO بالتفصيل: سعر جني الربح (Price)، سعر التنبيه (Stop)، وسعر الوقف (Limit).
    4. إذا كان هناك تشبع شرائي أو خطورة، انصح بعدم الشراء واذكر السبب الفني بإيجاز.
    """
    try:
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt
        )
        return interaction.output_text
    except Exception as e:
        return f"حدث خطأ أثناء تحليل الذكاء الاصطناعي: {e}"

def run_scanner():
    """تنفيذ فحص العملات وإرسال النتيجة"""
    all_data = {}
    for symbol in SYMBOLS:
        try:
            df = get_binance_klines(symbol, interval="15m")
            all_data[symbol] = calculate_indicators(df)
        except Exception as e:
            print(f"تعذر جلب بيانات {symbol}: {e}")
            
    analysis_report = analyze_market_with_ai(all_data)
    send_telegram_message(analysis_report)

if __name__ == "__main__":
    web_thread = threading.Thread(target=start_background_web_server, daemon=True)
    web_thread.start()
    
    # فحص أولي فوري
    run_scanner()
    
    # تكرار الفحص كل 30 دقيقة
    while True:
        time.sleep(1800)
        run_scanner()
        
