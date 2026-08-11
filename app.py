import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import warnings
import sqlite3
from contextlib import contextmanager
import hashlib
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

def check_password():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    
    st.markdown("""
    <style>
        .login-box { max-width: 400px; margin: 100px auto; padding: 40px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 20px; text-align: center; }
        .login-box h1 { color: #FFD700; font-size: 2em; }
        .login-box input { width: 100%; padding: 15px; margin: 10px 0; border: 2px solid #333; border-radius: 10px; background: #0f0f1a; color: white; font-size: 16px; text-align: center; }
        .login-box button { width: 100%; padding: 15px; margin-top: 20px; background: linear-gradient(45deg, #FFD700, #FFA500); color: #000; border: none; border-radius: 10px; font-size: 18px; font-weight: bold; cursor: pointer; }
    </style>
    <div class="login-box"><h1>🔒 دستیار هوشمند بورس</h1>""", unsafe_allow_html=True)
    
    username = st.text_input("👤 نام کاربری", key="user_input")
    password = st.text_input("🔑 رمز عبور", type="password", key="pass_input")
    
    if st.button("🚀 ورود", use_container_width=True):
        VALID_USERNAME = "admin"
        VALID_PASSWORD = "MyTrading@2024!#"
        if username == VALID_USERNAME and hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(VALID_PASSWORD.encode()).hexdigest():
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ اشتباه است!")
    st.markdown('</div>', unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()

st.set_page_config(page_title="دستیار بورس", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .stButton>button { background: linear-gradient(45deg, #FF4B2B, #FF416C); color: white; font-weight: bold; border-radius: 10px; padding: 10px 20px; border: none; }
    .buy-card { background: linear-gradient(135deg, #11998e, #38ef7d); padding: 12px; border-radius: 8px; color: white; margin: 3px 0; }
    .sell-card { background: linear-gradient(135deg, #cb2d3e, #ef473a); padding: 12px; border-radius: 8px; color: white; margin: 3px 0; }
    .gold-card { background: linear-gradient(135deg, #f7971e, #ffd200); padding: 15px; border-radius: 10px; color: #000; margin: 5px 0; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@contextmanager
def get_db():
    conn = sqlite3.connect('trading.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, symbol TEXT, price REAL, signal TEXT, score INTEGER)''')
        conn.commit()
init_db()

class SmartTradingSystem:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        self.session.verify = False
        self.cache = {}
        self.gold_keywords = ['طلا', 'نقره', 'زر', 'گوهر', 'کهربا', 'تابان', 'لوتوس', 'آلتون', 'عیار', 'جواهر', 'شمش', 'مثقال', 'سکه', 'گنج', 'داریک', 'کیان']
        self.gold_platforms = {
            "فراز گلد": {"url": "https://farazgold.com", "features": ["طلای آبشده", "سکه", "شمش"], "min": "۱ میلیون تومان", "delivery": "فیزیکی و خزانه"},
            "گلدیکا": {"url": "https://goldika.ir", "features": ["طلای آبشده", "مثقال", "گرم طلا"], "min": "۵۰۰ هزار تومان", "delivery": "فیزیکی"},
            "کیان طلا": {"url": "https://kianegold.com", "features": ["طلای آبشده", "شمش", "سکه"], "min": "۱ میلیون تومان", "delivery": "فیزیکی و خزانه"},
            "طلاسی": {"url": "https://talasi.ir", "features": ["طلای آبشده", "سکه", "شمش نقره"], "min": "۱۰۰ هزار تومان", "delivery": "فیزیکی"},
            "مثقال": {"url": "https://mesghal.com", "features": ["طلای آبشده", "سکه", "نقره"], "min": "۵۰۰ هزار تومان", "delivery": "فیزیکی و خزانه"},
            "زرین گلد": {"url": "https://zaringold.com", "features": ["طلای آبشده", "شمش", "سکه"], "min": "۱ میلیون تومان", "delivery": "فیزیکی"}
        }
    
    def get_all_symbols(self):
        urls = [
            "https://members.tsetmc.com/api/Instrument/GetInstrumentList",
            "http://cdn.tsetmc.com/api/Instrument/GetInstrumentList"
        ]
        for url in urls:
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if data and 'instrumentList' in data:
                        symbols = []
                        for item in data['instrumentList']:
                            code = item.get('insCode', '')
                            symbol = item.get('lVal30', '')
                            name = item.get('lVal18AFC', '')
                            if code and symbol:
                                symbols.append({'code': code, 'symbol': symbol.strip(), 'name': name.strip() if name else symbol.strip()})
                        if symbols:
                            return symbols
            except:
                continue
        return []
    
    def get_stock_data(self, code, days=300):
        cache_key = f"{code}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key].copy()
        
        urls = [
            f"https://members.tsetmc.com/api/ClosingPrice/GetClosingPriceHistory/{code}",
            f"http://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceHistory/{code}"
        ]
        for url in urls:
            try:
                r = self.session.get(url, timeout=10)
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
                        result = df[['date','open','high','low','close','volume']].tail(days).copy()
                        self.cache[cache_key] = result.copy()
                        return result
            except:
                continue
        return None
    
    def calculate_indicators(self, df):
        if df is None or len(df) < 50:
            return None
        df = df.copy()
        
        for p in [5, 10, 20, 50]:
            df[f'MA{p}'] = df['close'].rolling(p).mean()
        
        df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        for p in [7, 14]:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(p).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(p).mean()
            rs = gain / loss
            df[f'RSI{p}'] = 100 - (100 / (1 + rs))
        
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['Stoch_K'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        df['BB_Mid'] = df['close'].rolling(20).mean()
        df['BB_Std'] = df['close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
        df['BB_Pos'] = (df['close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        hl = df['high'] - df['low']
        hc = abs(df['high'] - df['close'].shift())
        lc = abs(df['low'] - df['close'].shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['ATR_Pct'] = df['ATR'] / df['close'] * 100
        
        df['DM_plus'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), np.maximum(df['high'] - df['high'].shift(), 0), 0)
        df['DM_minus'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), np.maximum(df['low'].shift() - df['low'], 0), 0)
        df['TR_14'] = tr.rolling(14).sum()
        df['DI_plus'] = 100 * df['DM_plus'].rolling(14).sum() / df['TR_14']
        df['DI_minus'] = 100 * df['DM_minus'].rolling(14).sum() / df['TR_14']
        df['DX'] = 100 * abs(df['DI_plus'] - df['DI_minus']) / (df['DI_plus'] + df['DI_minus'])
        df['ADX'] = df['DX'].rolling(14).mean()
        
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['CCI'] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
        
        df['Vol_MA20'] = df['volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['volume'] / df['Vol_MA20']
        
        df['Body'] = df['close'] - df['open']
        df['Body_Abs'] = abs(df['Body'])
        df['Lower_Shadow'] = df[['open','close']].min(axis=1) - df['low']
        df['Upper_Shadow'] = df['high'] - df[['open','close']].max(axis=1)
        df['Total_Range'] = df['high'] - df['low']
        df['Hammer'] = ((df['Lower_Shadow'] > 2*df['Body_Abs']) & (df['Upper_Shadow'] < df['Body_Abs']*0.5)).astype(int)
        df['Engulfing_Bull'] = ((df['Body'] > 0) & (df['Body'].shift(1) < 0) & (df['Body_Abs'] > abs(df['Body'].shift(1))*1.2)).astype(int)
        df['Engulfing_Bear'] = ((df['Body'] < 0) & (df['Body'].shift(1) > 0) & (df['Body_Abs'] > abs(df['Body'].shift(1))*1.2)).astype(int)
        
        for p in [20, 50]:
            df[f'Support_{p}'] = df['low'].rolling(p).min()
            df[f'Resistance_{p}'] = df['high'].rolling(p).max()
        
        for p in [1, 5, 20, 60]:
            df[f'Ret_{p}d'] = df['close'].pct_change(p) * 100
        
        for p in [5, 20]:
            df[f'ROC_{p}'] = df['close'].pct_change(p) * 100
        
        ret = df['close'].pct_change()
        df['Sharpe_20'] = ret.rolling(20).mean() / (ret.rolling(20).std() + 0.0001) * np.sqrt(252)
        
        return df
    
    def generate_signal(self, df):
        if df is None or len(df) < 80:
            return None, "داده ناکافی", [], 0
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        signals = []
        score = 0
        
        rsi14 = latest['RSI14']
        if rsi14 < 25:
            signals.append(f"RSI اشباع فروش ({rsi14:.1f})"); score += 4
        elif rsi14 < 35:
            signals.append(f"RSI نزدیک اشباع فروش ({rsi14:.1f})"); score += 2
        elif rsi14 > 80:
            signals.append(f"RSI اشباع خرید ({rsi14:.1f})"); score -= 4
        elif rsi14 > 70:
            signals.append(f"RSI نزدیک اشباع خرید ({rsi14:.1f})"); score -= 2
        
        if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
            signals.append("تقاطع طلایی MACD"); score += 3
        elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
            signals.append("تقاطع مرگ MACD"); score -= 3
        
        if latest['BB_Pos'] < 0.05:
            signals.append("کف بولینگر"); score += 3
        elif latest['BB_Pos'] > 0.95:
            signals.append("سقف بولینگر"); score -= 3
        
        if latest['MA5'] > latest['MA20'] and prev['MA5'] <= prev['MA20']:
            signals.append("تقاطع MA5/MA20"); score += 2
        if latest['MA20'] > latest['MA50'] and prev['MA20'] <= prev['MA50']:
            signals.append("تقاطع MA20/MA50"); score += 3
        elif latest['MA20'] < latest['MA50'] and prev['MA20'] >= prev['MA50']:
            signals.append("تقاطع مرگ MA20/MA50"); score -= 3
        
        if latest['Vol_Ratio'] > 2:
            signals.append(f"حجم بالا ({latest['Vol_Ratio']:.1f}x)"); score += 1 if score > 0 else -1
        
        if latest['Stoch_K'] < 20:
            signals.append("استوکاستیک اشباع فروش"); score += 3
        elif latest['Stoch_K'] > 80:
            signals.append("استوکاستیک اشباع خرید"); score -= 3
        
        if latest['ADX'] > 25:
            if latest['DI_plus'] > latest['DI_minus']:
                signals.append(f"روند صعودی (ADX:{latest['ADX']:.1f})"); score += 2
            else:
                signals.append(f"روند نزولی (ADX:{latest['ADX']:.1f})"); score -= 2
        
        if latest['CCI'] < -200:
            signals.append("CCI اشباع فروش"); score += 3
        elif latest['CCI'] > 200:
            signals.append("CCI اشباع خرید"); score -= 3
        
        if latest['Hammer']:
            signals.append("چکش صعودی"); score += 3
        if latest['Engulfing_Bull']:
            signals.append("انگالفینگ صعودی"); score += 4
        if latest['Engulfing_Bear']:
            signals.append("انگالفینگ نزولی"); score -= 4
        
        if latest['ROC_5'] > 15:
            signals.append(f"رشد سریع ({latest['ROC_5']:.1f}%)"); score -= 2
        elif latest['ROC_5'] < -15:
            signals.append(f"افت سریع ({latest['ROC_5']:.1f}%)"); score += 2
        
        price_trend = stats.linregress(range(15), df['close'].tail(15))[0]
        rsi_trend = stats.linregress(range(15), df['RSI14'].tail(15))[0]
        macd_trend = stats.linregress(range(15), df['MACD'].tail(15))[0]
        
        if price_trend < 0 and rsi_trend > 0.2:
            signals.append("واگرایی مثبت RSI"); score += 4
        elif price_trend > 0 and rsi_trend < -0.2:
            signals.append("واگرایی منفی RSI"); score -= 4
        if price_trend < 0 and macd_trend > 0:
            signals.append("واگرایی مثبت MACD"); score += 3
        
        if latest['close'] <= latest['Support_20'] * 1.01:
            signals.append("روی حمایت ۲۰ روزه"); score += 2
        if latest['close'] >= latest['Resistance_20'] * 0.99:
            signals.append("روی مقاومت ۲۰ روزه"); score -= 2
        
        score = max(-15, min(15, score))
        
        if score >= 10:
            action = "🟢 خرید قوی"
        elif score >= 5:
            action = "🟢 خرید"
        elif score >= 2:
            action = "🟡 متمایل به خرید"
        elif score <= -10:
            action = "🔴 فروش قوی"
        elif score <= -5:
            action = "🔴 فروش"
        elif score <= -2:
            action = "🟠 متمایل به فروش"
        else:
            action = "⚪ خنثی"
        
        return df, action, signals, score
    
    def get_targets(self, df, buy_price=None):
        if df is None or len(df) < 50:
            return {}
        latest = df.iloc[-1]
        cp = buy_price if buy_price else latest['close']
        atr_pct = latest['ATR_Pct']
        return {
            'target_1': cp * (1 + atr_pct/100 * 2),
            'target_2': cp * (1 + atr_pct/100 * 3),
            'stop_tight': cp * (1 - atr_pct/100 * 2),
            'stop_normal': cp * (1 - atr_pct/100 * 3),
        }

@st.cache_resource
def get_system():
    return SmartTradingSystem()

system = get_system()
# ============================================
# UI
# ============================================
st.title("📈 دستیار بورس ایران")

with st.sidebar:
    mode = st.radio("بخش:", ["تحلیل سهم", "اسکن بازار", "سبد من", "طلا و نقره", "خرید طلا", "تاریخچه"])
    st.divider()
    st.caption(datetime.now().strftime('%H:%M:%S'))

if mode == "تحلیل سهم":
    st.subheader("تحلیل تکنیکال")
    
    with st.spinner("دریافت لیست نمادها..."):
        all_symbols = system.get_all_symbols()
    
    if all_symbols:
        st.success(f"{len(all_symbols)} نماد دریافت شد")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            search = st.text_input("جستجو:", placeholder="نام یا نماد...")
            if search:
                filtered = [s for s in all_symbols if search.upper() in s['symbol'].upper() or search in s['name']]
            else:
                popular = ["فولاد","فملی","شپنا","خودرو","وبملت","شتران","رمپنا","طلا","نقره","زر"]
                filtered = [s for s in all_symbols if s['symbol'] in popular] or all_symbols[:50]
            
            if filtered:
                opts = [f"{s['symbol']} - {s['name'][:40]}" for s in filtered[:100]]
                sel = st.selectbox("نماد:", opts)
                if sel:
                    sym = sel.split(" - ")[0]
                    data = next((s for s in filtered if s['symbol'] == sym), None)
                    if data:
                        bp = st.number_input("قیمت خرید (اختیاری):", value=0, step=1000)
                        if st.button("تحلیل", type="primary", use_container_width=True):
                            with st.spinner(f"تحلیل {sym}..."):
                                df = system.get_stock_data(data['code'], 300)
                                if df is not None and len(df) >= 80:
                                    df = system.calculate_indicators(df)
                                    df, action, signals, score = system.generate_signal(df)
                                    targets = system.get_targets(df, bp if bp > 0 else None)
                                    
                                    with get_db() as conn:
                                        conn.execute('INSERT INTO signals (symbol, price, signal, score) VALUES (?,?,?,?)',
                                                   (sym, df['close'].iloc[-1], action, score))
                                        conn.commit()
                                    
                                    with c2:
                                        cc1, cc2, cc3, cc4 = st.columns(4)
                                        with cc1:
                                            st.metric("قیمت", f"{df['close'].iloc[-1]:,.0f}", f"{df['Ret_1d'].iloc[-1]:+.2f}%")
                                        with cc2:
                                            st.metric("RSI", f"{df['RSI14'].iloc[-1]:.1f}")
                                        with cc3:
                                            st.metric("ADX", f"{df['ADX'].iloc[-1]:.1f}")
                                        with cc4:
                                            st.metric("امتیاز", f"{score}/15")
                                        
                                        if score >= 5:
                                            st.markdown(f"""<div class="buy-card"><h2>{action}</h2></div>""", unsafe_allow_html=True)
                                        elif score <= -5:
                                            st.markdown(f"""<div class="sell-card"><h2>{action}</h2></div>""", unsafe_allow_html=True)
                                        else:
                                            st.info(f"## {action}")
                                        
                                        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
                                        pd_ = min(90, len(df))
                                        fig.add_trace(go.Candlestick(x=df['date'].tail(pd_), open=df['open'].tail(pd_), high=df['high'].tail(pd_), low=df['low'].tail(pd_), close=df['close'].tail(pd_), name='قیمت'), row=1, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['MA20'].tail(pd_), name='MA20', line=dict(color='blue')), row=1, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['MA50'].tail(pd_), name='MA50', line=dict(color='orange')), row=1, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['BB_Upper'].tail(pd_), line=dict(color='gray', dash='dash'), showlegend=False), row=1, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['BB_Lower'].tail(pd_), line=dict(color='gray', dash='dash'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)', showlegend=False), row=1, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['RSI14'].tail(pd_), name='RSI', line=dict(color='purple')), row=2, col=1)
                                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['MACD'].tail(pd_), name='MACD', line=dict(color='blue')), row=3, col=1)
                                        fig.add_trace(go.Scatter(x=df['date'].tail(pd_), y=df['MACD_Signal'].tail(pd_), name='Signal', line=dict(color='orange')), row=3, col=1)
                                        fig.update_layout(height=700)
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        st.markdown("**دلایل:**")
                                        for s in signals:
                                            if 'خرید' in action:
                                                st.success(s)
                                            elif 'فروش' in action:
                                                st.error(s)
                                            else:
                                                st.info(s)
                                        
                                        if targets:
                                            t1, t2, t3 = st.columns(3)
                                            with t1:
                                                st.metric("🎯 هدف", f"{targets['target_1']:,.0f}")
                                            with t2:
                                                st.metric("🛑 ضرر", f"{targets['stop_normal']:,.0f}")
                                            with t3:
                                                st.metric("📊 ATR%", f"{df['ATR_Pct'].iloc[-1]:.2f}%")
                                        
                                        if bp > 0:
                                            cp = df['close'].iloc[-1]
                                            prof = cp - bp
                                            st.markdown(f"**💰 وضعیت شما:** خرید {bp:,.0f} | فعلی {cp:,.0f} | سود/ضرر {prof:+,.0f} ({prof/bp*100:+.2f}%)")
                                else:
                                    st.error("داده در دسترس نیست")
    else:
        st.error("خطا در دریافت اطلاعات")

elif mode == "اسکن بازار":
    st.subheader("اسکن بازار")
    
    c1, c2 = st.columns(2)
    with c1:
        scan_type = st.radio("نوع:", ["همه", "فقط طلا", "فقط سهام"])
    with c2:
        min_score = st.slider("حداقل امتیاز:", 1, 10, 3)
    
    if st.button("شروع اسکن", type="primary", use_container_width=True):
        with st.spinner("دریافت نمادها..."):
            all_symbols = system.get_all_symbols()
        
        if all_symbols:
            st.success(f"{len(all_symbols)} نماد")
            
            if scan_type == "فقط طلا":
                to_scan = [s for s in all_symbols if any(kw in s['name'] or kw in s['symbol'] for kw in system.gold_keywords)]
            elif scan_type == "فقط سهام":
                to_scan = [s for s in all_symbols if not any(kw in s['name'] or kw in s['symbol'] for kw in system.gold_keywords)]
            else:
                to_scan = all_symbols
            
            results = []
            prog = st.progress(0)
            stat = st.empty()
            
            for i, sym in enumerate(to_scan):
                if i % 20 == 0:
                    stat.text(f"{i+1}/{len(to_scan)} | {sym['symbol']}")
                    prog.progress((i+1)/len(to_scan))
                
                df = system.get_stock_data(sym['code'], 150)
                if df is not None and len(df) >= 60:
                    df = system.calculate_indicators(df)
                    df, action, signals, score = system.generate_signal(df)
                    
                    if abs(score) >= min_score:
                        is_gold = any(kw in sym['name'] or kw in sym['symbol'] for kw in system.gold_keywords)
                        results.append({
                            'نماد': sym['symbol'],
                            'نام': sym['name'][:35],
                            'نوع': '🥇' if is_gold else '📊',
                            'قیمت': f"{df['close'].iloc[-1]:,.0f}",
                            'RSI': f"{df['RSI14'].iloc[-1]:.1f}",
                            'سیگنال': action,
                            'امتیاز': score,
                        })
            
            prog.progress(1.0)
            stat.empty()
            
            if results:
                df_r = pd.DataFrame(results).sort_values('امتیاز', ascending=False)
                
                st.markdown(f"## {len(df_r)} سیگنال")
                
                gold_r = df_r[df_r['نوع'] == '🥇']
                if not gold_r.empty:
                    st.markdown("## 🥇 طلا و نقره")
                    for _, r in gold_r.iterrows():
                        cls = "gold-card" if r['امتیاز'] > 0 else "sell-card"
                        st.markdown(f"""<div class="{cls}"><b>{r['نماد']}</b> - {r['نام']} | {r['قیمت']} | ⭐{r['امتیاز']}/15 | {r['سیگنال']}</div>""", unsafe_allow_html=True)
                
                stock_r = df_r[df_r['نوع'] == '📊']
                
                st.markdown("## 🟢 خرید")
                for _, r in stock_r[stock_r['امتیاز'] > 0].head(20).iterrows():
                    st.markdown(f"""<div class="buy-card"><b>{r['نماد']}</b> - {r['نام']} | {r['قیمت']} | ⭐{r['امتیاز']}/15 | {r['سیگنال']}</div>""", unsafe_allow_html=True)
                
                st.markdown("## 🔴 فروش")
                for _, r in stock_r[stock_r['امتیاز'] < 0].head(20).iterrows():
                    st.markdown(f"""<div class="sell-card"><b>{r['نماد']}</b> - {r['نام']} | {r['قیمت']} | ⭐{r['امتیاز']}/15 | {r['سیگنال']}</div>""", unsafe_allow_html=True)
                
                top30 = df_r.head(30)
                colors = ['gold' if r['نوع'] == '🥇' else 'green' if r['امتیاز'] > 0 else 'red' for _, r in top30.iterrows()]
                fig = go.Figure()
                fig.add_trace(go.Bar(x=top30['نماد'], y=top30['امتیاز'], marker_color=colors, text=top30['امتیاز'], textposition='auto'))
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df_r, use_container_width=True)
            else:
                st.warning("سیگنالی یافت نشد")
        else:
            st.error("خطا در دریافت اطلاعات")

elif mode == "سبد من":
    st.subheader("سبد من")
    
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []
    
    with st.expander("➕ افزودن"):
        c1, c2, c3 = st.columns(3)
        with c1:
            ns = st.text_input("نماد:").upper()
        with c2:
            np_ = st.number_input("قیمت:", value=0, step=1000)
        with c3:
            nq = st.number_input("تعداد:", value=0, step=1)
        if st.button("افزودن") and ns and np_ > 0 and nq > 0:
            st.session_state.portfolio.append({'symbol': ns, 'buy_price': np_, 'quantity': nq})
            st.rerun()
    
    if st.session_state.portfolio:
        all_sym = system.get_all_symbols()
        total_inv = 0
        total_cur = 0
        
        for idx, item in enumerate(st.session_state.portfolio):
            sd = next((s for s in all_sym if s['symbol'] == item['symbol']), None)
            if sd:
                df = system.get_stock_data(sd['code'], 100)
                if df is not None and len(df) > 0:
                    cp = df['close'].iloc[-1]
                    inv = item['buy_price'] * item['quantity']
                    cur = cp * item['quantity']
                    prof = cur - inv
                    pct = (prof / inv) * 100 if inv > 0 else 0
                    total_inv += inv
                    total_cur += cur
                    
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"**{item['symbol']}** | تعداد: {item['quantity']} | خرید: {item['buy_price']:,.0f} | فعلی: {cp:,.0f}")
                    with c2:
                        color = "green" if prof >= 0 else "red"
                        st.markdown(f"<span style='color:{color};font-size:18px;'>{prof:+,.0f}</span>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<span style='color:{color};'>{pct:+.2f}%</span>", unsafe_allow_html=True)
        
        tp = total_cur - total_inv
        tpct = (tp / total_inv * 100) if total_inv > 0 else 0
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("کل سرمایه", f"{total_inv:,.0f}")
        with c2:
            st.metric("ارزش فعلی", f"{total_cur:,.0f}")
        with c3:
            st.metric("سود/ضرر", f"{tp:+,.0f}", f"{tpct:+.2f}%")
    else:
        st.info("سبد خالی است")
                      elif mode == "طلا و نقره":
    st.subheader("🥇 صندوق‌های طلا و نقره")
    
    funds = [
        {"name": "لوتوس", "search": "طلا"},
        {"name": "زر", "search": "زر"},
        {"name": "نقره", "search": "نقره"},
        {"name": "کهربا", "search": "کهربا"},
        {"name": "گوهر", "search": "گوهر"},
        {"name": "تابان", "search": "تابان"},
        {"name": "گنج", "search": "گنج"},
        {"name": "آلتون", "search": "آلتون"},
    ]
    
    all_sym = system.get_all_symbols()
    cols = st.columns(4)
    
    for i, fund in enumerate(funds):
        fd = next((s for s in all_sym if fund['search'] in s['name'] or fund['search'] in s['symbol']), None)
        with cols[i % 4]:
            if fd:
                df = system.get_stock_data(fd['code'], 200)
                if df is not None and len(df) >= 80:
                    df = system.calculate_indicators(df)
                    df, action, signals, score = system.generate_signal(df)
                    
                    st.markdown(f"**{fund['name']}** ({fd['symbol']})")
                    st.metric("قیمت", f"{df['close'].iloc[-1]:,.0f}", f"{df['Ret_1d'].iloc[-1]:+.2f}%")
                    
                    if score >= 5:
                        st.success(f"{action} ⭐{score}")
                    elif score <= -5:
                        st.error(f"{action} ⭐{score}")
                    else:
                        st.info(f"{action} ⭐{score}")
                    
                    st.caption(f"RSI: {df['RSI14'].iloc[-1]:.1f} | ADX: {df['ADX'].iloc[-1]:.1f}")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df['date'].tail(40), y=df['close'].tail(40), line=dict(color='gold', width=2)))
                    fig.add_trace(go.Scatter(x=df['date'].tail(40), y=df['MA20'].tail(40), line=dict(color='blue', width=1)))
                    fig.update_layout(height=150, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("داده نیست")
            else:
                st.warning(f"{fund['name']} نیست")

elif mode == "خرید طلا":
    st.subheader("🪙 خرید و فروش آنلاین طلا")
    
    st.markdown("### پلتفرم‌های معتبر")
    
    platforms = system.gold_platforms
    cols = st.columns(3)
    
    for i, (name, info) in enumerate(platforms.items()):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="gold-card">
                <h4>{name}</h4>
                <p>💰 حداقل: {info['min']}</p>
                <p>📦 تحویل: {info['delivery']}</p>
            """, unsafe_allow_html=True)
            for f in info['features']:
                st.markdown(f"• {f}")
            st.markdown(f"""<a href="{info['url']}" target="_blank">🌐 ورود</a></div>""", unsafe_allow_html=True)
    
    with st.expander("راهنما"):
        st.markdown("""
        **مراحل خرید:**
        1. ثبت‌نام و احراز هویت
        2. شارژ کیف پول
        3. انتخاب نوع طلا (آبشده، سکه، شمش)
        4. ثبت سفارش با قیمت لحظه‌ای
        5. نگهداری در خزانه یا تحویل فیزیکی
        
        **مزایا:** بدون اجرت | قیمت شفاف | خرید از ۱۰۰ هزار تومان | نقدشوندگی بالا
        """)

elif mode == "تاریخچه":
    st.subheader("تاریخچه سیگنال‌ها")
    
    with get_db() as conn:
        df_h = pd.read_sql('SELECT * FROM signals ORDER BY timestamp DESC LIMIT 100', conn)
    
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        if st.button("پاک کردن"):
            with get_db() as conn:
                conn.execute('DELETE FROM signals')
                conn.commit()
            st.rerun()
    else:
        st.info("سیگنالی ثبت نشده")

st.markdown("---")
st.caption("📊 تحلیل بر اساس داده‌های tsetmc.com | ۱۵+ اندیکاتور تکنیکال")
