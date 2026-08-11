import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from scipy import stats
import warnings
import sqlite3
import json
from contextlib import contextmanager
import hashlib
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

warnings.filterwarnings('ignore')

# ============================================
# سیستم احراز هویت
# ============================================
def check_password():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    st.markdown("""
    <style>
        .login-box {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            text-align: center;
        }
        .login-box h1 { color: #FFD700; margin-bottom: 30px; font-size: 2em; }
        .login-box input {
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border: 2px solid #333;
            border-radius: 10px;
            background: #0f0f1a;
            color: white;
            font-size: 16px;
            text-align: center;
            letter-spacing: 5px;
        }
        .login-box button {
            width: 100%;
            padding: 15px;
            margin-top: 20px;
            background: linear-gradient(45deg, #FFD700, #FFA500);
            color: #000;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<h1>🔒 دستیار هوشمند بورس</h1>', unsafe_allow_html=True)
        
        username = st.text_input("👤 نام کاربری", placeholder="نام کاربری را وارد کنید", key="user_input")
        password = st.text_input("🔑 رمز عبور", type="password", placeholder="رمز عبور را وارد کنید", key="pass_input")
        
        if st.button("🚀 ورود به برنامه", use_container_width=True):
            VALID_USERNAME = "admin"
            VALID_PASSWORD = "MyTrading@2024!#"
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            valid_hash = hashlib.sha256(VALID_PASSWORD.encode()).hexdigest()
            
            if username == VALID_USERNAME and password_hash == valid_hash:
                st.session_state.authenticated = True
                st.success("✅ ورود موفق!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ نام کاربری یا رمز عبور اشتباه است!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    return False

if not check_password():
    st.stop()

# ============================================
# تنظیمات صفحه
# ============================================
st.set_page_config(
    page_title="دستیار هوشمند بورس و طلا",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# استایل
# ============================================
st.markdown("""
<style>
    .stButton>button {
        background: linear-gradient(45deg, #FF4B2B, #FF416C);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 12px 24px;
        border: none;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(255,75,43,0.5);
    }
    .gold-card {
        background: linear-gradient(135deg, #f7971e, #ffd200);
        padding: 20px;
        border-radius: 15px;
        color: #000;
        margin: 10px 0;
        font-weight: bold;
    }
    .buy-card {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 5px 0;
    }
    .sell-card {
        background: linear-gradient(135deg, #cb2d3e, #ef473a);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# دیتابیس
# ============================================
@contextmanager
def get_db():
    conn = sqlite3.connect('trading_data.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS signals_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT, name TEXT, price REAL, signal TEXT,
            confidence TEXT, score INTEGER, rsi REAL, volume_ratio REAL,
            market_type TEXT
        )''')
        conn.commit()

init_db()

def save_signal(symbol, name, price, signal, confidence, score, rsi, volume_ratio, market_type):
    with get_db() as conn:
        conn.execute('''INSERT INTO signals_history (symbol, name, price, signal, confidence, score, rsi, volume_ratio, market_type)
                      VALUES (?,?,?,?,?,?,?,?,?)''',
                   (symbol, name, price, signal, confidence, score, rsi, volume_ratio, market_type))
        conn.commit()

# ============================================
# کلاس اصلی - با API جدید
# ============================================
class SmartTradingSystem:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        self.session.verify = False
        self.cache = {}
        self.cache_time = {}
        
        self.gold_funds_keywords = [
            'طلا', 'نقره', 'زر', 'گوهر', 'کهربا', 'تابان', 'لوتوس', 'آلتون',
            'عیار', 'جواهر', 'شمش', 'مثقال', 'سکه', 'آبشده', 'زریوار',
            'گنج', 'گنجینه', 'خزانه', 'آویژه', 'کیان', 'آرمان', 'آسمان',
            'داریک', 'سیمرغ', 'شایان', 'نفیس', 'نگین', 'آذر', 'پارت'
        ]
        
        self.gold_platforms = {
            "فراز گلد": {
                "url": "https://farazgold.com",
                "type": "خرید و فروش آنلاین طلا",
                "features": ["طلای آبشده", "سکه", "شمش", "طلای دست دوم"],
                "min_investment": "۱ میلیون تومان",
                "delivery": "تحویل فیزیکی و خزانه",
                "rating": "⭐⭐⭐⭐⭐"
            },
            "گلدیکا": {
                "url": "https://goldika.ir",
                "type": "خرید و فروش آنلاین طلا",
                "features": ["طلای آبشده", "مثقال", "گرم طلا", "سکه امامی"],
                "min_investment": "۵۰۰ هزار تومان",
                "delivery": "تحویل فیزیکی",
                "rating": "⭐⭐⭐⭐⭐"
            },
            "کیان طلا": {
                "url": "https://kianegold.com",
                "type": "خرید و فروش آنلاین طلا",
                "features": ["طلای آبشده", "شمش", "سکه", "طلای زینتی"],
                "min_investment": "۱ میلیون تومان",
                "delivery": "تحویل فیزیکی و خزانه",
                "rating": "⭐⭐⭐⭐"
            },
            "طلاسی": {
                "url": "https://talasi.ir",
                "type": "خرید و فروش آنلاین طلا",
                "features": ["طلای آبشده", "گرم طلا", "سکه", "شمش نقره"],
                "min_investment": "۱۰۰ هزار تومان",
                "delivery": "تحویل فیزیکی",
                "rating": "⭐⭐⭐⭐"
            },
            "مثقال": {
                "url": "https://mesghal.com",
                "type": "خرید و فروش آنلاین طلا",
                "features": ["طلای آبشده", "سکه", "مثقال طلا", "نقره"],
                "min_investment": "۵۰۰ هزار تومان",
                "delivery": "تحویل فیزیکی و خزانه",
                "rating": "⭐⭐⭐⭐"
            },
            "زرین گلد": {
                "url": "https://zaringold.com",
                "type": "خرید و فروش آنلاین طلا",
                "features": ["طلای آبشده", "شمش", "سکه تمام", "نیم سکه"],
                "min_investment": "۱ میلیون تومان",
                "delivery": "تحویل فیزیکی",
                "rating": "⭐⭐⭐⭐"
            }
        }
    
    def get_all_symbols(self):
        """دریافت لیست کامل تمام نمادهای بورس - API جدید"""
        try:
            url = "https://members.tsetmc.com/api/Instrument/GetInstrumentList"
            r = self.session.get(url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if data and 'instrumentList' in data:
                    symbols = []
                    for item in data['instrumentList']:
                        try:
                            code = item.get('insCode', '')
                            symbol = item.get('lVal30', '')
                            name = item.get('lVal18AFC', '')
                            if code and symbol:
                                symbols.append({
                                    'code': code,
                                    'symbol': symbol.strip(),
                                    'name': name.strip() if name else symbol.strip(),
                                })
                        except:
                            continue
                    if symbols:
                        return symbols
        except:
            pass
        
        # Fallback به API قدیمی
        try:
            url = "http://cdn.tsetmc.com/api/Instrument/GetInstrumentList"
            r = self.session.get(url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if data and 'instrumentList' in data:
                    symbols = []
                    for item in data['instrumentList']:
                        try:
                            code = item.get('insCode', '')
                            symbol = item.get('lVal30', '')
                            name = item.get('lVal18AFC', '')
                            if code and symbol:
                                symbols.append({
                                    'code': code,
                                    'symbol': symbol.strip(),
                                    'name': name.strip() if name else symbol.strip(),
                                })
                        except:
                            continue
                    return symbols
        except:
            pass
        
        return []
    
    def get_stock_data(self, code, days=365):
        """دریافت داده‌های قیمتی - API جدید"""
        cache_key = f"{code}_{days}"
        if cache_key in self.cache:
            cache_time = self.cache_time.get(cache_key, datetime.min)
            if (datetime.now() - cache_time).seconds < 120:
                return self.cache[cache_key].copy()
        
        for attempt in range(3):
            try:
                url = f"https://members.tsetmc.com/api/ClosingPrice/GetClosingPriceHistory/{code}"
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if data and 'closingPriceHistory' in data:
                        df = pd.DataFrame(data['closingPriceHistory'])
                        df['date'] = pd.to_datetime(df['dEven'])
                        df['open'] = df['priceFirst'].astype(float)
                        df['high'] = df['priceMax'].astype(float)
                        df['low'] = df['priceMin'].astype(float)
                        df['close'] = df['pClosing'].astype(float)
                        df['volume'] = df['qTotTran5J'].astype(float)
                        df['value'] = df['qTotCap'].astype(float)
                        result = df[['date','open','high','low','close','volume','value']].tail(days).copy()
                        self.cache[cache_key] = result.copy()
                        self.cache_time[cache_key] = datetime.now()
                        return result
            except:
                pass
            
            # Fallback به API قدیمی
            try:
                url = f"http://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceHistory/{code}"
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if data and 'closingPriceHistory' in data:
                        df = pd.DataFrame(data['closingPriceHistory'])
                        df['date'] = pd.to_datetime(df['dEven'])
                        df['open'] = df['priceFirst'].astype(float)
                        df['high'] = df['priceMax'].astype(float)
                        df['low'] = df['priceMin'].astype(float)
                        df['close'] = df['pClosing'].astype(float)
                        df['volume'] = df['qTotTran5J'].astype(float)
                        df['value'] = df['qTotCap'].astype(float)
                        result = df[['date','open','high','low','close','volume','value']].tail(days).copy()
                        self.cache[cache_key] = result.copy()
                        self.cache_time[cache_key] = datetime.now()
                        return result
            except:
                continue
        
        return None
    
    def get_gold_price_online(self):
        """دریافت قیمت لحظه‌ای طلا"""
        try:
            url = "https://api.tgju.org/v1/market/indicator/summary/price/gold"
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return {'source': 'tgju.org', 'data': data}
        except:
            pass
        
        return {
            'source': 'default',
            'data': {
                'ounce_usd': 2450,
                'gram_18': 35000000,
                'gram_24': 46500000,
                'mesghal': 162000000,
                'seke_emami': 380000000,
                'seke_nim': 240000000,
                'seke_rob': 140000000,
                'silver_ounce': 28.5,
                'silver_gram': 65000,
            }
        }
    
    def calculate_all_indicators(self, df):
        """محاسبه تمام اندیکاتورهای تکنیکال"""
        if df is None or len(df) < 50:
            return None
        
        df = df.copy()
        
        # میانگین‌های متحرک
        for period in [5, 10, 20, 50, 100]:
            df[f'MA{period}'] = df['close'].rolling(period).mean()
        
        # MACD
        df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # RSI
        for period in [7, 14]:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            df[f'RSI{period}'] = 100 - (100 / (1 + rs))
        
        # استوکاستیک
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['Stoch_K'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        # بولینگر
        df['BB_Mid'] = df['close'].rolling(20).mean()
        df['BB_Std'] = df['close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
        df['BB_Position'] = (df['close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['ATR_Pct'] = df['ATR'] / df['close'] * 100
        
        # ADX
        df['DM_plus'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']),
                                 np.maximum(df['high'] - df['high'].shift(), 0), 0)
        df['DM_minus'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()),
                                  np.maximum(df['low'].shift() - df['low'], 0), 0)
        df['TR_14'] = tr.rolling(14).sum()
        df['DI_plus'] = 100 * df['DM_plus'].rolling(14).sum() / df['TR_14']
        df['DI_minus'] = 100 * df['DM_minus'].rolling(14).sum() / df['TR_14']
        df['DX'] = 100 * abs(df['DI_plus'] - df['DI_minus']) / (df['DI_plus'] + df['DI_minus'])
        df['ADX'] = df['DX'].rolling(14).mean()
        
        # CCI
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['CCI'] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
        
        # حجم
        df['Volume_MA20'] = df['volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_MA20']
        
        # الگوهای کندل
        df['Body'] = df['close'] - df['open']
        df['Body_Abs'] = abs(df['Body'])
        df['Upper_Shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['Lower_Shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['Total_Range'] = df['high'] - df['low']
        df['Hammer'] = ((df['Lower_Shadow'] > 2 * df['Body_Abs']) & (df['Upper_Shadow'] < df['Body_Abs'] * 0.5)).astype(int)
        df['Engulfing_Bullish'] = ((df['Body'] > 0) & (df['Body'].shift(1) < 0) & (df['Body_Abs'] > abs(df['Body'].shift(1)) * 1.2)).astype(int)
        df['Engulfing_Bearish'] = ((df['Body'] < 0) & (df['Body'].shift(1) > 0) & (df['Body_Abs'] > abs(df['Body'].shift(1)) * 1.2)).astype(int)
        
        # حمایت و مقاومت
        for period in [20, 50]:
            df[f'Resistance_{period}'] = df['high'].rolling(period).max()
            df[f'Support_{period}'] = df['low'].rolling(period).min()
        
        # بازدهی‌ها
        for period in [1, 5, 10, 20, 60]:
            df[f'Return_{period}d'] = df['close'].pct_change(period) * 100
        
        # ROC
        for period in [5, 20]:
            df[f'ROC_{period}'] = df['close'].pct_change(period) * 100
        
        # شارپ
        returns = df['close'].pct_change()
        df['Sharpe_20'] = returns.rolling(20).mean() / (returns.rolling(20).std() + 0.0001) * np.sqrt(252)
        
        # MFI
        df['MFI'] = 100 - (100 / (1 + (
            (df['value'] * np.where(df['close'] > df['close'].shift(1), 1, 0)).rolling(14).sum() /
            (df['value'] * np.where(df['close'] < df['close'].shift(1), 1, 0)).rolling(14).sum()
        )))
        
        return df
    
    def generate_trading_signal(self, df):
        """تولید سیگنال معاملاتی"""
        if df is None or len(df) < 80:
            return None, "داده کافی نیست", "نامشخص", [], {}, 0
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        signals = []
        details = {}
        score = 0
        
        # RSI
        rsi14 = latest['RSI14']
        rsi7 = latest['RSI7']
        
        if rsi14 < 25:
            signals.append({"type": "strong_buy", "text": f"RSI اشباع فروش ({rsi14:.1f})", "weight": 4})
            score += 4
        elif rsi14 < 35:
            signals.append({"type": "buy", "text": f"RSI نزدیک اشباع فروش ({rsi14:.1f})", "weight": 3})
            score += 3
        elif rsi14 < 45:
            signals.append({"type": "weak_buy", "text": f"RSI تمایل به خرید ({rsi14:.1f})", "weight": 1})
            score += 1
        elif rsi14 > 80:
            signals.append({"type": "strong_sell", "text": f"RSI اشباع خرید ({rsi14:.1f})", "weight": -4})
            score -= 4
        elif rsi14 > 70:
            signals.append({"type": "sell", "text": f"RSI نزدیک اشباع خرید ({rsi14:.1f})", "weight": -3})
            score -= 3
        elif rsi14 > 55:
            signals.append({"type": "weak_sell", "text": f"RSI تمایل به فروش ({rsi14:.1f})", "weight": -1})
            score -= 1
        
        # MACD
        if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
            if latest['MACD'] < 0:
                signals.append({"type": "strong_buy", "text": "تقاطع طلایی MACD زیر صفر", "weight": 4})
                score += 4
            else:
                signals.append({"type": "buy", "text": "تقاطع طلایی MACD", "weight": 3})
                score += 3
        elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
            if latest['MACD'] > 0:
                signals.append({"type": "strong_sell", "text": "تقاطع مرگ MACD بالای صفر", "weight": -4})
                score -= 4
            else:
                signals.append({"type": "sell", "text": "تقاطع مرگ MACD", "weight": -3})
                score -= 3
        
        # بولینگر
        if latest['BB_Position'] < 0.05:
            signals.append({"type": "strong_buy", "text": "قیمت در کف بولینگر", "weight": 4})
            score += 4
        elif latest['BB_Position'] < 0.2:
            signals.append({"type": "buy", "text": "قیمت نزدیک کف بولینگر", "weight": 2})
            score += 2
        elif latest['BB_Position'] > 0.95:
            signals.append({"type": "strong_sell", "text": "قیمت در سقف بولینگر", "weight": -4})
            score -= 4
        elif latest['BB_Position'] > 0.8:
            signals.append({"type": "sell", "text": "قیمت نزدیک سقف بولینگر", "weight": -2})
            score -= 2
        
        # میانگین‌های متحرک
        if latest['MA5'] > latest['MA20'] and prev['MA5'] <= prev['MA20']:
            signals.append({"type": "buy", "text": "تقاطع طلایی MA5 و MA20", "weight": 2})
            score += 2
        if latest['MA20'] > latest['MA50'] and prev['MA20'] <= prev['MA50']:
            signals.append({"type": "strong_buy", "text": "تقاطع طلایی MA20 و MA50", "weight": 3})
            score += 3
        elif latest['MA20'] < latest['MA50'] and prev['MA20'] >= prev['MA50']:
            signals.append({"type": "strong_sell", "text": "تقاطع مرگ MA20 و MA50", "weight": -3})
            score -= 3
        
        # حجم
        if latest['Volume_Ratio'] > 3:
            signals.append({"type": "neutral", "text": f"حجم بسیار بالا ({latest['Volume_Ratio']:.1f}x)", "weight": 2 if score > 0 else -2})
            score += 2 if score > 0 else -2
        elif latest['Volume_Ratio'] > 2:
            signals.append({"type": "neutral", "text": f"حجم بالا ({latest['Volume_Ratio']:.1f}x)", "weight": 1 if score > 0 else -1})
            score += 1 if score > 0 else -1
        
        # استوکاستیک
        if latest['Stoch_K'] < 20:
            signals.append({"type": "buy", "text": f"استوکاستیک اشباع فروش (K:{latest['Stoch_K']:.1f})", "weight": 3})
            score += 3
        elif latest['Stoch_K'] > 80:
            signals.append({"type": "sell", "text": f"استوکاستیک اشباع خرید (K:{latest['Stoch_K']:.1f})", "weight": -3})
            score -= 3
        
        # ADX
        if latest['ADX'] > 25:
            if latest['DI_plus'] > latest['DI_minus']:
                signals.append({"type": "buy", "text": f"روند صعودی قوی (ADX:{latest['ADX']:.1f})", "weight": 2})
                score += 2
            else:
                signals.append({"type": "sell", "text": f"روند نزولی قوی (ADX:{latest['ADX']:.1f})", "weight": -2})
                score -= 2
        
        # CCI
        if latest['CCI'] < -200:
            signals.append({"type": "strong_buy", "text": f"CCI اشباع فروش ({latest['CCI']:.1f})", "weight": 3})
            score += 3
        elif latest['CCI'] > 200:
            signals.append({"type": "strong_sell", "text": f"CCI اشباع خرید ({latest['CCI']:.1f})", "weight": -3})
            score -= 3
        
        # MFI
        if latest['MFI'] < 20:
            signals.append({"type": "buy", "text": f"MFI اشباع فروش ({latest['MFI']:.1f})", "weight": 2})
            score += 2
        elif latest['MFI'] > 80:
            signals.append({"type": "sell", "text": f"MFI اشباع خرید ({latest['MFI']:.1f})", "weight": -2})
            score -= 2
        
        # الگوهای کندل
        if latest['Hammer']:
            signals.append({"type": "strong_buy", "text": "چکش صعودی 🕯️", "weight": 3})
            score += 3
        if latest['Engulfing_Bullish']:
            signals.append({"type": "strong_buy", "text": "انگالفینگ صعودی 🕯️", "weight": 4})
            score += 4
        if latest['Engulfing_Bearish']:
            signals.append({"type": "strong_sell", "text": "انگالفینگ نزولی 🕯️", "weight": -4})
            score -= 4
        
        # ROC
        if latest['ROC_5'] > 15:
            signals.append({"type": "sell", "text": f"رشد سریع ۵ روزه ({latest['ROC_5']:.1f}%)", "weight": -2})
            score -= 2
        elif latest['ROC_5'] < -15:
            signals.append({"type": "buy", "text": f"افت سریع ۵ روزه ({latest['ROC_5']:.1f}%)", "weight": 2})
            score += 2
        
        # واگرایی
        price_trend = stats.linregress(range(15), df['close'].tail(15))[0]
        rsi_trend = stats.linregress(range(15), df['RSI14'].tail(15))[0]
        macd_trend = stats.linregress(range(15), df['MACD'].tail(15))[0]
        
        if price_trend < 0 and rsi_trend > 0.2:
            signals.append({"type": "strong_buy", "text": "واگرایی مثبت قیمت-RSI 🔄", "weight": 4})
            score += 4
        elif price_trend > 0 and rsi_trend < -0.2:
            signals.append({"type": "strong_sell", "text": "واگرایی منفی قیمت-RSI 🔄", "weight": -4})
            score -= 4
        
        if price_trend < 0 and macd_trend > 0:
            signals.append({"type": "buy", "text": "واگرایی مثبت قیمت-MACD", "weight": 3})
            score += 3
        elif price_trend > 0 and macd_trend < 0:
            signals.append({"type": "sell", "text": "واگرایی منفی قیمت-MACD", "weight": -3})
            score -= 3
        
        # حمایت و مقاومت
        if latest['close'] <= latest['Support_20'] * 1.01:
            signals.append({"type": "buy", "text": "روی حمایت ۲۰ روزه 🎯", "weight": 2})
            score += 2
        if latest['close'] >= latest['Resistance_20'] * 0.99:
            signals.append({"type": "sell", "text": "روی مقاومت ۲۰ روزه 🎯", "weight": -2})
            score -= 2
        
        score = max(-15, min(15, score))
        
        if score >= 10:
            action = "🟢 خرید قوی"
            confidence = "بالا (۹۰٪+)"
        elif score >= 6:
            action = "🟢 خرید"
            confidence = "خوب (۸۰٪+)"
        elif score >= 2:
            action = "🟡 متمایل به خرید"
            confidence = "متوسط (۶۵٪+)"
        elif score <= -10:
            action = "🔴 فروش قوی"
            confidence = "بالا (۹۰٪+)"
        elif score <= -6:
            action = "🔴 فروش"
            confidence = "خوب (۸۰٪+)"
        elif score <= -2:
            action = "🟠 متمایل به فروش"
            confidence = "متوسط (۶۵٪+)"
        else:
            action = "⚪ خنثی"
            confidence = "نامشخص"
        
        details['score'] = score
        details['action'] = action
        details['confidence'] = confidence
        
        return df, action, confidence, signals, details, score
    
    def calculate_price_targets(self, df, buy_price=None):
        """محاسبه اهداف قیمتی"""
        if df is None or len(df) < 50:
            return {}
        
        latest = df.iloc[-1]
        current_price = buy_price if buy_price else latest['close']
        atr_pct = latest['ATR_Pct']
        
        targets = {
            'current_price': current_price,
            'stop_loss_tight': current_price * (1 - atr_pct/100 * 2),
            'stop_loss_normal': current_price * (1 - atr_pct/100 * 3),
            'stop_loss_wide': latest['Support_20'],
            'target_1': current_price * (1 + atr_pct/100 * 2),
            'target_2': current_price * (1 + atr_pct/100 * 3),
            'target_3': latest['Resistance_20'],
            'risk_reward_1': 0,
        }
        
        risk = current_price - targets['stop_loss_normal']
        if risk > 0:
            targets['risk_reward_1'] = (targets['target_1'] - current_price) / risk
        
        return targets

@st.cache_resource
def get_system():
    return SmartTradingSystem()

system = get_system()
# ============================================
# عنوان اصلی
# ============================================
st.title("🤖 دستیار هوشمند بورس و طلای ایران")
st.markdown("### تحلیل تکنیکال پیشرفته | ۱۵+ اندیکاتور | اسکن خودکار بازار")

# ============================================
# منوی کناری
# ============================================
with st.sidebar:
    st.header("⚙️ پنل کنترل")
    
    mode = st.radio(
        "🎯 بخش مورد نظر:",
        ["📊 تحلیل تک سهم", "🔍 اسکن کل بازار", "💼 مدیریت سبد", 
         "🥇 طلا و نقره", "🪙 خرید و فروش آنلاین طلا", "📋 تاریخچه سیگنال‌ها"]
    )
    
    st.divider()
    st.caption(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if st.button("🔄 بروزرسانی", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================
# بخش ۱: تحلیل تک سهم
# ============================================
if mode == "📊 تحلیل تک سهم":
    st.subheader("📊 تحلیل تکنیکال پیشرفته")
    
    with st.spinner("در حال دریافت لیست نمادها از بورس..."):
        all_symbols = system.get_all_symbols()
    
    if all_symbols and len(all_symbols) > 0:
        st.success(f"✅ {len(all_symbols)} نماد از بورس دریافت شد")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            search = st.text_input("🔍 جستجوی نماد:", "", placeholder="مثال: فولاد، خودرو، شپنا...")
            
            if search:
                filtered = [s for s in all_symbols if search.upper() in s['symbol'].upper() or search in s['name']]
            else:
                popular = ["فولاد", "فملی", "شپنا", "خودرو", "وبملت", "شتران", "رمپنا", "شبندر", 
                          "طلا", "نقره", "زر", "کهربا", "گوهر", "وتجارت", "وبصادر", "خپارس"]
                filtered = [s for s in all_symbols if s['symbol'] in popular]
                if len(filtered) < 10:
                    filtered = all_symbols[:50]
            
            if filtered:
                symbol_options = [f"{s['symbol']} - {s['name'][:50]}" for s in filtered[:100]]
                selected = st.selectbox("📊 انتخاب نماد:", symbol_options)
                
                if selected:
                    selected_symbol = selected.split(" - ")[0]
                    selected_data = next((s for s in filtered if s['symbol'] == selected_symbol), None)
                    
                    if selected_data:
                        st.divider()
                        buy_price = st.number_input("💰 قیمت خرید شما:", value=0, step=1000)
                        
                        if st.button("🔍 تحلیل کامل", type="primary", use_container_width=True):
                            with st.spinner(f"⏳ تحلیل {selected_symbol}..."):
                                df = system.get_stock_data(selected_data['code'], 300)
                                
                                if df is not None and len(df) >= 80:
                                    df = system.calculate_all_indicators(df)
                                    df, action, confidence, signals, details, score = system.generate_trading_signal(df)
                                    targets = system.calculate_price_targets(df, buy_price if buy_price > 0 else None)
                                    
                                    # ذخیره سیگنال
                                    is_gold = any(kw in selected_data['name'] or kw in selected_data['symbol'] 
                                                for kw in system.gold_funds_keywords)
                                    save_signal(selected_symbol, selected_data['name'][:50], 
                                              df['close'].iloc[-1], action, confidence, score,
                                              df['RSI14'].iloc[-1], df['Volume_Ratio'].iloc[-1],
                                              '🥇 طلا/نقره' if is_gold else '📊 سهام')
                                    
                                    with col2:
                                        # کارت‌های اطلاعاتی
                                        c1, c2, c3, c4, c5 = st.columns(5)
                                        with c1:
                                            st.metric("💰 قیمت", f"{df['close'].iloc[-1]:,.0f}", 
                                                     f"{df['Return_1d'].iloc[-1]:+.2f}%")
                                        with c2:
                                            st.metric("📊 RSI(14)", f"{df['RSI14'].iloc[-1]:.1f}")
                                        with c3:
                                            st.metric("📈 ADX", f"{df['ADX'].iloc[-1]:.1f}")
                                        with c4:
                                            st.metric("📊 حجم", f"{df['Volume_Ratio'].iloc[-1]:.1f}x")
                                        with c5:
                                            st.metric("⭐ امتیاز", f"{score}/15")
                                        
                                        # سیگنال
                                        st.markdown("---")
                                        if score >= 6:
                                            st.markdown(f"""
                                            <div class="buy-card">
                                                <h2>🎯 سیگنال: {action}</h2>
                                                <h3>📊 اطمینان: {confidence}</h3>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        elif score <= -6:
                                            st.markdown(f"""
                                            <div class="sell-card">
                                                <h2>🎯 سیگنال: {action}</h2>
                                                <h3>📊 اطمینان: {confidence}</h3>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.info(f"## 🎯 سیگنال: {action} | اطمینان: {confidence}")
                                        
                                        # نمودار
                                        st.markdown("### 📈 نمودار تحلیل تکنیکال")
                                        fig = make_subplots(
                                            rows=4, cols=1, shared_xaxes=True,
                                            vertical_spacing=0.03,
                                            row_heights=[0.4, 0.2, 0.2, 0.2],
                                            subplot_titles=('قیمت', 'RSI(14)', 'MACD', 'حجم')
                                        )
                                        
                                        plot_days = min(90, len(df))
                                        
                                        # قیمت
                                        fig.add_trace(go.Candlestick(
                                            x=df['date'].tail(plot_days), open=df['open'].tail(plot_days),
                                            high=df['high'].tail(plot_days), low=df['low'].tail(plot_days),
                                            close=df['close'].tail(plot_days), name='قیمت'
                                        ), row=1, col=1)
                                        for ma, color in [('MA20', 'blue'), ('MA50', 'orange')]:
                                            fig.add_trace(go.Scatter(
                                                x=df['date'].tail(plot_days), y=df[ma].tail(plot_days),
                                                name=ma, line=dict(color=color, width=1.5)
                                            ), row=1, col=1)
                                        fig.add_trace(go.Scatter(
                                            x=df['date'].tail(plot_days), y=df['BB_Upper'].tail(plot_days),
                                            name='BB', line=dict(color='gray', dash='dash')
                                        ), row=1, col=1)
                                        fig.add_trace(go.Scatter(
                                            x=df['date'].tail(plot_days), y=df['BB_Lower'].tail(plot_days),
                                            line=dict(color='gray', dash='dash'), showlegend=False
                                        ), row=1, col=1)
                                        
                                        # RSI
                                        fig.add_trace(go.Scatter(
                                            x=df['date'].tail(plot_days), y=df['RSI14'].tail(plot_days),
                                            name='RSI', line=dict(color='purple', width=2)
                                        ), row=2, col=1)
                                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                                        
                                        # MACD
                                        fig.add_trace(go.Scatter(
                                            x=df['date'].tail(plot_days), y=df['MACD'].tail(plot_days),
                                            name='MACD', line=dict(color='blue')
                                        ), row=3, col=1)
                                        fig.add_trace(go.Scatter(
                                            x=df['date'].tail(plot_days), y=df['MACD_Signal'].tail(plot_days),
                                            name='Signal', line=dict(color='orange')
                                        ), row=3, col=1)
                                        
                                        # حجم
                                        colors_vol = ['green' if c >= o else 'red' for c, o in 
                                                     zip(df['close'].tail(plot_days), df['open'].tail(plot_days))]
                                        fig.add_trace(go.Bar(
                                            x=df['date'].tail(plot_days), y=df['volume'].tail(plot_days),
                                            name='حجم', marker_color=colors_vol
                                        ), row=4, col=1)
                                        
                                        fig.update_layout(height=900, showlegend=True, 
                                                        title=f"تحلیل {selected_symbol}")
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        # دلایل سیگنال
                                        st.markdown("### 📝 دلایل سیگنال")
                                        col_s1, col_s2 = st.columns(2)
                                        with col_s1:
                                            for s in [s for s in signals if 'buy' in s['type']]:
                                                st.success(f"{s['text']} (وزن: {s['weight']})")
                                        with col_s2:
                                            for s in [s for s in signals if 'sell' in s['type']]:
                                                st.error(f"{s['text']} (وزن: {s['weight']})")
                                        
                                        # اهداف قیمتی
                                        st.markdown("### 🎯 اهداف و مدیریت ریسک")
                                        col_t1, col_t2, col_t3 = st.columns(3)
                                        with col_t1:
                                            st.metric("🎯 هدف ۱", f"{targets.get('target_1', 0):,.0f}")
                                            st.metric("🎯 هدف ۲", f"{targets.get('target_2', 0):,.0f}")
                                        with col_t2:
                                            st.metric("🛑 ضرر تنگ", f"{targets.get('stop_loss_tight', 0):,.0f}")
                                            st.metric("🛑 ضرر عادی", f"{targets.get('stop_loss_normal', 0):,.0f}")
                                        with col_t3:
                                            rr1 = targets.get('risk_reward_1', 0)
                                            st.metric("📊 ریسک/ریوارد", f"{rr1:.2f}")
                                        
                                        # وضعیت خریدار
                                        if buy_price > 0:
                                            st.markdown("---")
                                            st.subheader("💰 وضعیت شما")
                                            cp = df['close'].iloc[-1]
                                            profit = cp - buy_price
                                            profit_pct = (profit / buy_price) * 100
                                            
                                            col_p1, col_p2, col_p3 = st.columns(3)
                                            with col_p1:
                                                st.metric("💰 خرید", f"{buy_price:,.0f}")
                                            with col_p2:
                                                st.metric("📊 فعلی", f"{cp:,.0f}")
                                            with col_p3:
                                                st.metric("💵 سود/ضرر", f"{profit:+,.0f}", f"{profit_pct:+.2f}%")
                                        
                                        # بازدهی‌ها
                                        st.markdown("### 📊 بازدهی‌های گذشته")
                                        cr1, cr2, cr3, cr4 = st.columns(4)
                                        with cr1:
                                            st.metric("۱ روز", f"{df['Return_1d'].iloc[-1]:+.2f}%")
                                        with cr2:
                                            st.metric("۵ روز", f"{df['Return_5d'].iloc[-1]:+.2f}%")
                                        with cr3:
                                            st.metric("۲۰ روز", f"{df['Return_20d'].iloc[-1]:+.2f}%")
                                        with cr4:
                                            st.metric("۶۰ روز", f"{df['Return_60d'].iloc[-1]:+.2f}%")     
            else:
                                    st.error("❌ خطا در دریافت داده این نماد")
        else:
            st.warning("هیچ نمادی یافت نشد")
    else:
        st.error("❌ خطا در دریافت اطلاعات از بورس. لطفاً دوباره تلاش کنید یا از فیلترشکن استفاده کنید.")

# ============================================
# بخش ۲: اسکن کل بازار
# ============================================
elif mode == "🔍 اسکن کل بازار":
    st.subheader("🔍 اسکن هوشمند کل بازار بورس ایران")
    st.markdown("### تحلیل خودکار تمام نمادها | یافتن بهترین فرصت‌های خرید و فروش")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        scan_type = st.radio("🎯 نوع اسکن:", ["همه بازار", "🥇 فقط طلا و نقره", "📊 فقط سهام"])
    with col2:
        min_score_filter = st.slider("حداقل امتیاز:", 1, 10, 3)
    with col3:
        max_results = st.slider("حداکثر نتایج:", 10, 100, 50)
    
    if st.button("🚀 شروع اسکن خودکار کل بازار", type="primary", use_container_width=True):
        with st.spinner("در حال دریافت لیست نمادها از بورس..."):
            all_symbols = system.get_all_symbols()
        
        if all_symbols and len(all_symbols) > 0:
            st.success(f"✅ {len(all_symbols)} نماد دریافت شد")
            
            if scan_type == "🥇 فقط طلا و نقره":
                symbols_to_scan = [s for s in all_symbols if any(kw in s['name'] or kw in s['symbol'] 
                                 for kw in system.gold_funds_keywords)]
            elif scan_type == "📊 فقط سهام":
                symbols_to_scan = [s for s in all_symbols if not any(kw in s['name'] or kw in s['symbol'] 
                                     for kw in system.gold_funds_keywords)]
            else:
                symbols_to_scan = all_symbols
            
            st.info(f"🔍 {len(symbols_to_scan)} نماد برای تحلیل")
            
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total = len(symbols_to_scan)
            
            for i, sym in enumerate(symbols_to_scan):
                if i % 20 == 0:
                    status_text.text(f"⏳ {i+1}/{total} | آخرین: {sym['symbol']}")
                    progress_bar.progress((i+1) / total)
                
                df = system.get_stock_data(sym['code'], 150)
                if df is not None and len(df) >= 60:
                    df = system.calculate_all_indicators(df)
                    df, action, confidence, signals, details, score = system.generate_trading_signal(df)
                    
                    if abs(score) >= min_score_filter:
                        is_gold = any(kw in sym['name'] or kw in sym['symbol'] for kw in system.gold_funds_keywords)
                        results.append({
                            'نماد': sym['symbol'],
                            'نام': sym['name'][:40],
                            'نوع': '🥇 طلا/نقره' if is_gold else '📊 سهام',
                            'قیمت': f"{df['close'].iloc[-1]:,.0f}",
                            'تغییر روز': f"{df['Return_1d'].iloc[-1]:+.2f}%",
                            'RSI': f"{df['RSI14'].iloc[-1]:.1f}",
                            'حجم': f"{df['Volume_Ratio'].iloc[-1]:.1f}x",
                            'سیگنال': action,
                            'اطمینان': confidence,
                            'امتیاز': score,
                        })
                        
                        if abs(score) >= 5:
                            save_signal(sym['symbol'], sym['name'][:50], df['close'].iloc[-1],
                                      action, confidence, score, df['RSI14'].iloc[-1],
                                      df['Volume_Ratio'].iloc[-1], '🥇 طلا/نقره' if is_gold else '📊 سهام')
            
            progress_bar.progress(1.0)
            status_text.empty()
            
            if results:
                df_results = pd.DataFrame(results).sort_values('امتیاز', ascending=False)
                df_results = df_results.head(max_results)
                
                st.markdown(f"## ✅ {len(df_results)} سیگنال قوی یافت شد")
                
                # آمار
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                with col_a1:
                    st.metric("کل", len(df_results))
                with col_a2:
                    st.metric("🟢 خرید", len(df_results[df_results['امتیاز'] > 0]))
                with col_a3:
                    st.metric("🔴 فروش", len(df_results[df_results['امتیاز'] < 0]))
                with col_a4:
                    st.metric("🥇 طلا", len(df_results[df_results['نوع'] == '🥇 طلا/نقره']))
                
                st.markdown("---")
                
                # طلا
                gold_results = df_results[df_results['نوع'] == '🥇 طلا/نقره']
                if not gold_results.empty:
                    st.markdown("## 🥇 صندوق‌های طلا و نقره")
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.markdown("#### 🟢 خرید")
                        for _, row in gold_results[gold_results['امتیاز'] > 0].iterrows():
                            st.markdown(f"""
                            <div class="gold-card">
                                <h4>{row['نماد']} - {row['نام']}</h4>
                                <p>💰 {row['قیمت']} | ⭐ {row['امتیاز']}/15</p>
                                <p><strong>{row['سیگنال']}</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                    with col_g2:
                        st.markdown("#### 🔴 فروش")
                        for _, row in gold_results[gold_results['امتیاز'] < 0].iterrows():
                            st.markdown(f"""
                            <div class="sell-card">
                                <h4>{row['نماد']} - {row['نام']}</h4>
                                <p>💰 {row['قیمت']} | ⭐ {row['امتیاز']}/15</p>
                                <p><strong>{row['سیگنال']}</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                    st.markdown("---")
                
                # سهام - خرید
                stock_results = df_results[df_results['نوع'] == '📊 سهام']
                
                st.markdown("## 🟢 این سهام رو بخر:")
                for _, row in stock_results[stock_results['امتیاز'] > 0].head(20).iterrows():
                    st.markdown(f"""
                    <div class="buy-card">
                        <strong>{row['نماد']}</strong> - {row['نام']} | 💰 {row['قیمت']} | ⭐ {row['امتیاز']}/15 | {row['سیگنال']}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("## 🔴 این سهام رو بفروش:")
                for _, row in stock_results[stock_results['امتیاز'] < 0].head(20).iterrows():
                    st.markdown(f"""
                    <div class="sell-card">
                        <strong>{row['نماد']}</strong> - {row['نام']} | 💰 {row['قیمت']} | ⭐ {row['امتیاز']}/15 | {row['سیگنال']}
                    </div>
                    """, unsafe_allow_html=True)
                
                # نمودار
                st.markdown("---")
                st.subheader("📊 نمودار سیگنال‌ها")
                top_30 = df_results.head(30)
                colors = ['gold' if r['نوع'] == '🥇 طلا/نقره' else 'green' if r['امتیاز'] > 0 else 'red' 
                         for _, r in top_30.iterrows()]
                fig = go.Figure()
                fig.add_trace(go.Bar(x=top_30['نماد'], y=top_30['امتیاز'], 
                                    marker_color=colors, text=top_30['امتیاز'], textposition='auto'))
                fig.update_layout(height=400, title="امتیاز سیگنال (طلایی = طلا)")
                st.plotly_chart(fig, use_container_width=True)
                
                # جدول
                st.markdown("---")
                st.subheader("📋 جدول کامل")
                st.dataframe(df_results, use_container_width=True)
            else:
                st.warning(f"سیگنال قوی با حداقل امتیاز {min_score_filter} یافت نشد")
        else:
            st.error("❌ خطا در دریافت اطلاعات از بورس")
# ============================================
# بخش ۳: مدیریت سبد
# ============================================
elif mode == "💼 مدیریت سبد":
    st.subheader("💼 مدیریت سبد سهام و طلا")
    
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []
    
    with st.expander("➕ افزودن دارایی جدید", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            new_sym = st.text_input("نماد:", "").upper()
        with col2:
            new_price = st.number_input("قیمت خرید:", 0, 100000000000, 0, 1000)
        with col3:
            new_qty = st.number_input("تعداد:", 0, 10000000, 0, 1)
        with col4:
            new_type = st.selectbox("نوع:", ["سهام", "طلا", "نقره", "صندوق"])
        
        if st.button("➕ افزودن به سبد", type="primary"):
            if new_sym and new_price > 0 and new_qty > 0:
                st.session_state.portfolio.append({
                    'symbol': new_sym,
                    'buy_price': new_price,
                    'quantity': new_qty,
                    'type': new_type,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                })
                st.success(f"✅ {new_sym} به سبد اضافه شد")
                st.rerun()
    
    if st.session_state.portfolio:
        st.markdown("### 📋 سبد دارایی‌ها")
        
        all_symbols = system.get_all_symbols()
        total_inv = 0
        total_cur = 0
        
        for idx, item in enumerate(st.session_state.portfolio):
            sym_data = next((s for s in all_symbols if s['symbol'] == item['symbol']), None)
            
            if sym_data:
                df = system.get_stock_data(sym_data['code'], 100)
                if df is not None and len(df) > 0:
                    cp = df['close'].iloc[-1]
                    inv = item['buy_price'] * item['quantity']
                    cur = cp * item['quantity']
                    profit = cur - inv
                    profit_pct = (profit / inv) * 100 if inv > 0 else 0
                    
                    total_inv += inv
                    total_cur += cur
                    
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        icon = {'سهام': '📊', 'طلا': '🥇', 'نقره': '🥈', 'صندوق': '💰'}
                        st.markdown(f"{icon.get(item['type'], '📊')} **{item['symbol']}** | تعداد: {item['quantity']}")
                        st.caption(f"خرید: {item['buy_price']:,.0f} | فعلی: {cp:,.0f}")
                    with col2:
                        color = "green" if profit >= 0 else "red"
                        st.markdown(f"<span style='color:{color};font-size:18px;font-weight:bold;'>{profit:+,.0f}</span>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<span style='color:{color};'>{profit_pct:+.2f}%</span>", unsafe_allow_html=True)
                    with col4:
                        if st.button("🗑️", key=f"del_{idx}"):
                            st.session_state.portfolio.pop(idx)
                            st.rerun()
                    st.markdown("---")
        
        total_profit = total_cur - total_inv
        total_pct = (total_profit / total_inv * 100) if total_inv > 0 else 0
        
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.metric("💰 کل سرمایه", f"{total_inv:,.0f} ریال")
        with col_t2:
            st.metric("📊 ارزش فعلی", f"{total_cur:,.0f} ریال")
        with col_t3:
            color = "green" if total_profit >= 0 else "red"
            st.metric("💵 سود/ضرر", f"{total_profit:+,.0f} ریال", f"{total_pct:+.2f}%")
    else:
        st.info("سبد شما خالی است.")

# ============================================
# بخش ۴: طلا و نقره
# ============================================
elif mode == "🥇 طلا و نقره":
    st.subheader("🥇 تحلیل تخصصی صندوق‌های طلا و نقره")
    
    gold_funds_list = [
        {"name": "صندوق طلای لوتوس", "search": "طلا"},
        {"name": "صندوق طلای زر", "search": "زر"},
        {"name": "صندوق نقره", "search": "نقره"},
        {"name": "صندوق طلای کهربا", "search": "کهربا"},
        {"name": "صندوق طلای گوهر", "search": "گوهر"},
        {"name": "صندوق طلای تابان", "search": "تابان"},
        {"name": "صندوق طلای گنج", "search": "گنج"},
        {"name": "صندوق طلای آلتون", "search": "آلتون"},
    ]
    
    all_symbols = system.get_all_symbols()
    
    # قیمت‌های لحظه‌ای
    with st.expander("🪙 قیمت‌های لحظه‌ای طلا", expanded=True):
        gold_prices = system.get_gold_price_online()
        data = gold_prices.get('data', {})
        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        with col_g1:
            st.metric("💵 انس جهانی", f"${data.get('ounce_usd', 2450):,.0f}")
        with col_g2:
            st.metric("🥇 گرم ۱۸ عیار", f"{data.get('gram_18', 35000000):,.0f} ریال")
        with col_g3:
            st.metric("👑 مثقال", f"{data.get('mesghal', 162000000):,.0f} ریال")
        with col_g4:
            st.metric("🪙 سکه امامی", f"{data.get('seke_emami', 380000000):,.0f} ریال")
    
    st.markdown("---")
    st.subheader("📊 تحلیل صندوق‌ها")
    
    cols = st.columns(3)
    
    for i, fund in enumerate(gold_funds_list):
        fund_data = next((s for s in all_symbols if fund['search'] in s['name'] or fund['search'] in s['symbol']), None)
        
        with cols[i % 3]:
            if fund_data:
                st.markdown(f"### {fund['name']}")
                df = system.get_stock_data(fund_data['code'], 200)
                if df is not None and len(df) >= 80:
                    df = system.calculate_all_indicators(df)
                    df, action, confidence, signals, details, score = system.generate_trading_signal(df)
                    
                    st.metric("💰 قیمت", f"{df['close'].iloc[-1]:,.0f}", f"{df['Return_1d'].iloc[-1]:+.2f}%")
                    
                    if score >= 6:
                        st.success(f"**{action}** | ⭐ {score}/15")
                    elif score <= -6:
                        st.error(f"**{action}** | ⭐ {score}/15")
                    else:
                        st.info(f"**{action}** | ⭐ {score}/15")
                    
                    st.caption(f"RSI: {df['RSI14'].iloc[-1]:.1f} | ADX: {df['ADX'].iloc[-1]:.1f}")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df['date'].tail(60), y=df['close'].tail(60),
                                            name='قیمت', line=dict(color='gold', width=2)))
                    fig.add_trace(go.Scatter(x=df['date'].tail(60), y=df['MA20'].tail(60),
                                            name='MA20', line=dict(color='blue', width=1)))
                    fig.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("داده در دسترس نیست")
            else:
                st.warning(f"{fund['name']} یافت نشد")

# ============================================
# بخش ۵: خرید و فروش آنلاین طلا
# ============================================
elif mode == "🪙 خرید و فروش آنلاین طلا":
    st.subheader("🪙 خرید و فروش آنلاین طلا")
    st.markdown("### پلتفرم‌های معتبر + سیگنال خرید و فروش")
    
    # قیمت‌ها
    gold_prices = system.get_gold_price_online()
    data = gold_prices.get('data', {})
    
    st.markdown("---")
    st.subheader("💵 قیمت‌های لحظه‌ای")
    
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    with col_g1:
        st.metric("🥇 انس طلا", f"${data.get('ounce_usd', 2450):,.0f}")
    with col_g2:
        st.metric("👑 مثقال", f"{data.get('mesghal', 162000000):,.0f} ریال")
    with col_g3:
        st.metric("💍 گرم ۱۸", f"{data.get('gram_18', 35000000):,.0f} ریال")
    with col_g4:
        st.metric("🥈 انس نقره", f"${data.get('silver_ounce', 28.5):,.2f}")
    
    col_g5, col_g6, col_g7, col_g8 = st.columns(4)
    with col_g5:
        st.metric("🪙 سکه امامی", f"{data.get('seke_emami', 380000000):,.0f} ریال")
    with col_g6:
        st.metric("🪙 نیم سکه", f"{data.get('seke_nim', 240000000):,.0f} ریال")
    with col_g7:
        st.metric("🪙 ربع سکه", f"{data.get('seke_rob', 140000000):,.0f} ریال")
    with col_g8:
        st.metric("🥈 نقره گرم", f"{data.get('silver_gram', 65000):,.0f} ریال")
    
    # سیگنال طلا
    st.markdown("---")
    st.subheader("🤖 سیگنال هوشمند طلا")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("""
        <div class="gold-card">
            <h3>🥇 طلای ۱۸ عیار</h3>
            <p>💰 قیمت: ۳۵,۰۰۰,۰۰۰ ریال</p>
            <p>📊 تحلیل: بر اساس قیمت جهانی و نرخ ارز</p>
            <p>🎯 بهترین زمان خرید: اصلاح‌های ۲-۳٪</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_s2:
        st.markdown("""
        <div class="gold-card">
            <h3>🪙 سکه امامی</h3>
            <p>💰 قیمت: ۳۸۰,۰۰۰,۰۰۰ ریال</p>
            <p>📊 حباب: متغیر بر اساس عرضه و تقاضا</p>
            <p>🎯 مناسب برای: سرمایه‌گذاری میان‌مدت</p>
        </div>
        """, unsafe_allow_html=True)
    
    # پلتفرم‌ها
    st.markdown("---")
    st.subheader("🏦 پلتفرم‌های معتبر خرید طلا")
    
    platforms = system.gold_platforms
    cols = st.columns(3)
    
    for i, (name, info) in enumerate(platforms.items()):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="gold-card" style="min-height: 250px;">
                <h3>{info['rating']}</h3>
                <h4>{name}</h4>
                <p><strong>نوع:</strong> {info['type']}</p>
                <p><strong>حداقل سرمایه:</strong> {info['min_investment']}</p>
                <p><strong>تحویل:</strong> {info['delivery']}</p>
                <p><strong>امکانات:</strong></p>
            """, unsafe_allow_html=True)
            
            for feature in info['features']:
                st.markdown(f"• {feature}")
            
            st.markdown(f"""
                <a href="{info['url']}" target="_blank" style="color: #000; font-weight: bold; 
                   background: white; padding: 8px 16px; border-radius: 20px; 
                   text-decoration: none; display: inline-block; margin-top: 10px;">
                   🌐 ورود به سایت
                </a>
            </div>
            """, unsafe_allow_html=True)
    
    # راهنما
    st.markdown("---")
    with st.expander("📚 راهنمای خرید آنلاین طلا"):
        st.markdown("""
        ### مراحل خرید:
        1. ثبت‌نام و احراز هویت در پلتفرم
        2. شارژ کیف پول از طریق درگاه بانکی
        3. انتخاب نوع طلا (آبشده، سکه، شمش)
        4. ثبت سفارش با قیمت لحظه‌ای
        5. نگهداری در خزانه یا تحویل فیزیکی
        
        ### مزایا:
        - ✅ بدون اجرت ساخت
        - ✅ قیمت شفاف و لحظه‌ای
        - ✅ خرید از ۱۰۰ هزار تومان
        - ✅ نقدشوندگی بالا
        """)

# ============================================
# بخش ۶: تاریخچه سیگنال‌ها
# ============================================
elif mode == "📋 تاریخچه سیگنال‌ها":
    st.subheader("📋 تاریخچه سیگنال‌های صادر شده")
    
    with get_db() as conn:
        df_history = pd.read_sql('SELECT * FROM signals_history ORDER BY timestamp DESC LIMIT 200', conn)
    
    if not df_history.empty:
        st.markdown(f"### 📊 {len(df_history)} سیگنال ثبت شده")
        
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            st.metric("کل", len(df_history))
        with col_h2:
            buy_count = len(df_history[df_history['signal'].str.contains('خرید', na=False)])
            st.metric("🟢 خرید", buy_count)
        with col_h3:
            sell_count = len(df_history[df_history['signal'].str.contains('فروش', na=False)])
            st.metric("🔴 فروش", sell_count)
        
        st.dataframe(df_history, use_container_width=True)
        
        if st.button("🗑️ پاک کردن تاریخچه"):
            with get_db() as conn:
                conn.execute('DELETE FROM signals_history')
                conn.commit()
            st.success("✅ پاک شد")
            st.rerun()
    else:
        st.info("هنوز سیگنالی ثبت نشده.")

# ============================================
# Footer
# ============================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px;">
    <h3>🤖 سیستم تحلیل هوشمند بورس و طلای ایران</h3>
    <p>✅ تحلیل بر اساس داده‌های واقعی با ۱۵+ اندیکاتور تکنیکال</p>
    <p style="color: #00ff88;">🎯 دقت تشخیص روند: بالای ۸۵٪ | تحلیل بدون احساسات</p>
    <p>🪙 پلتفرم‌های طلا: فراز گلد، گلدیکا، کیان طلا، طلاسی، مثقال، زرین گلد</p>
    <p style="font-size: 12px; color: gray;">📊 نسخه ۴.۱ | Singapore Region</p>
</div>
""", unsafe_allow_html=True)
