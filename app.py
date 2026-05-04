import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import requests

# ==========================================
# 1. 網頁基本設定 & 注入專屬 CSS
# ==========================================
st.set_page_config(page_title="全球 AI 量化戰情室 (完全體)", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
.stApp { background-color: #0a0c10; color: #e8e4dc; font-family: 'Noto Serif TC', serif; }
header {visibility: hidden;}
:root { --gold: #c9a84c; --red: #e05c5c; --green: #4caf82; --amber: #e8a24a; --surface: #111318; --surface2: #181c24; --border: #1e2433; --text-dim: #7a8090; }
.custom-header { border-bottom: 1px solid var(--border); padding-bottom: 15px; margin-bottom: 20px; position: relative; }
.custom-header::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 120px; height: 2px; background: linear-gradient(90deg, var(--gold), transparent); }
.header-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--gold); letter-spacing: 0.2em; }
.custom-header h1 { font-size: 32px; font-weight: 900; color: #fff; margin: 5px 0;}
.custom-header h1 span { color: var(--gold); }
.panel-box { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 15px; margin-bottom: 15px; }
.panel-title { font-size: 13px; font-family: 'JetBrains Mono', monospace; color: #fff; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;}
.panel-item { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.panel-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.panel-key { color: var(--text-dim); }
.panel-val { font-family: 'JetBrains Mono', monospace; font-weight: bold; }
.prob-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 10px; }
.prob-card { background: var(--surface2); padding: 15px 10px; text-align: center; border-radius: 4px; border-top: 3px solid #333; }
.prob-title { font-size: 12px; color: var(--text-dim); margin-bottom: 5px; }
.prob-val { font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 900; }
.mtf-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 15px;}
.mtf-card { background: var(--surface2); border: 1px solid var(--border); padding: 10px; text-align: center; border-radius: 4px;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 2. 側邊欄
# ==========================================
st.sidebar.markdown("<h3 style='color:#c9a84c; font-family: Noto Serif TC;'>🌍 全球投資組合設定</h3>", unsafe_allow_html=True)
market_choice = st.sidebar.radio("📊 選擇大盤分析基準",["台股加權指數 (^TWII)", "美股標普 500 (^GSPC)", "美股納斯達克 (^IXIC)"])
st.sidebar.write("---")
with st.sidebar.form("setting_form"):
    user_input = st.text_area("請輸入持股代號 (用逗號分隔)", "2330.TW, NVDA, AAPL, 2603.TW")
    submit_btn = st.form_submit_button("🚀 更新戰情室數據")

# ==========================================
# 3. 核心函數與快取機制 (加入多週期、籌碼、基本面)
# ==========================================
@st.cache_data(ttl=1800)
def fetch_market_data(main_ticker, tickers_str):
    # 1. 抓取日線
    df_main = yf.Ticker(main_ticker).history(period="6mo")
    df_main.ta.sma(length=5, append=True)
    df_main.ta.sma(length=20, append=True)
    df_main.ta.sma(length=60, append=True)
    df_main.ta.rsi(length=14, append=True)
    df_main.ta.bbands(length=20, std=2, append=True)
    df_main.ta.macd(append=True)
    df_main.ta.stoch(append=True)
    
    # 2. 抓取多週期 (60分K, 週K)
    df_hr = yf.Ticker(main_ticker).history(period="1mo", interval="1h")
    df_wk = yf.Ticker(main_ticker).history(period="2y", interval="1wk")
    
    # 計算短中長趨勢
    mtf_status = {"short": "震盪", "mid": "震盪", "long": "震盪"}
    try:
        df_hr.ta.sma(length=20, append=True)
        df_wk.ta.sma(length=20, append=True)
        mtf_status["short"] = "多頭 🚀" if df_hr['Close'].iloc[-1] > df_hr['SMA_20'].iloc[-1] else "空頭 ⚠️"
        mtf_status["mid"] = "多頭 🚀" if df_main['Close'].iloc[-1] > df_main['SMA_20'].iloc[-1] else "空頭 ⚠️"
        mtf_status["long"] = "多頭 🚀" if df_wk['Close'].iloc[-1] > df_wk['SMA_20'].iloc[-1] else "空頭 ⚠️"
    except: pass

    # 3. 抓取個股與基本面
    tickers =[t.strip() for t in tickers_str.split(",") if t.strip()]
    p_data, p_info =[], ""
    for t in tickers:
        stk_obj = yf.Ticker(t)
        stk = stk_obj.history(period="1mo")
        if not stk.empty and len(stk) >= 20:
            stk.ta.sma(length=5, append=True)
            stk.ta.sma(length=20, append=True)
            sc, sm5, sm20 = stk.iloc[-1]['Close'], stk.iloc[-1]['SMA_5'], stk.iloc[-1]['SMA_20']
            
            # 抓基本面 (PE, 殖利率)
            try:
                info = stk_obj.info
                pe = round(info.get('trailingPE', 0), 1) if info.get('trailingPE') else "N/A"
                yield_pct = round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else "N/A"
            except:
                pe, yield_pct = "N/A", "N/A"
                
            p_data.append({"ticker": t.upper(), "c": sc, "m5": sm5, "m20": sm20, "pe": pe, "yield": yield_pct})
            p_info += f"- {t.upper()}: 收盤 {sc:.2f}, 20MA {sm20:.2f}, 本益比 {pe}, 殖利率 {yield_pct}%。\n"
            
    return df_main, mtf_status, p_data, p_info

@st.cache_data(ttl=3600)
def fetch_taiwan_chips():
    # 利用開源 FinMind 抓取台灣三大法人買賣超
    try:
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockTotalInstitutionalInvestors&start_date={start_date}"
        res = requests.get(url, timeout=5).json()
        if res['msg'] == 'success':
            df = pd.DataFrame(res['data'])
            df['net'] = (df['buy'] - df['sell']) / 100000000 # 轉換為億元
            latest_date = df['date'].max()
            latest_df = df[df['date'] == latest_date]
            
            chips = {"date": latest_date, "foreign": 0, "trust": 0, "dealer": 0}
            for _, r in latest_df.iterrows():
                if '外資' in r['name']: chips['foreign'] += r['net']
                elif '投信' in r['name']: chips['trust'] += r['net']
                elif '自營商' in r['name']: chips['dealer'] += r['net']
            return chips
    except:
        return None

@st.cache_data(ttl=3600)
def get_ai_report(market_name, c, m5, m20, rsi, p_info):
    api_key = st.secrets.get("GEMINI_API_KEY") 
    if not api_key: return "<p style='color:#e8a24a;'>⚠️ 系統尚未設定 GEMINI_API_KEY。</p>"
    try:
        genai.configure(api_key=api_key)
        prompt = f"""
        你是擁有 20 年經驗的華爾街頂級量化分析師。
        今日大盤基準為【{market_name}】，客觀數據：收盤 {c:.2f}，5MA {m5:.2f}，20MA {m20:.2f}，RSI {rsi:.1f}。
        我的持股組合如下 (包含基本面): {p_info}

        請提供深度分析報告。你**必須完全使用以下 HTML 結構與 Class 排版**。
        ⚠️ 絕對不要包含 ```html 標記，絕對不要在每一行開頭加上空白縮排！

        <div class="theory-block">
        <div class="theory-block-title">▸ 【{market_name}】解析 (波浪與纏論視角)</div>
        <div class="theory-text">
        (你的大盤分析內容，重點文字請使用 <strong> 標籤包裝)
        </div>
        </div>

        <div class="theory-block">
        <div class="theory-block-title">▸ 💼 全球專屬持股診斷 (技術面+基本面)</div>
        <div class="theory-text">
        (針對每一檔個股，綜合均線與本益比/殖利率給出具體操作建議，請使用 <ul> <li> 排版)
        </div>
        </div>
        """
        target_model = 'gemini-1.5-flash'
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini-2.5-flash' in m.name:
                target_model = m.name
                break
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```html", "").replace("```", "")
        return "\n".join([line.strip() for line in raw_text.split('\n')])
    except Exception as e:
        return f"<p style='color:#e05c5c;'>🤖 API 錯誤：{e}</p>"

# ==========================================
# 4. 戰情室版面渲染
# ==========================================
if "台股加權指數" in market_choice:
    main_ticker, market_name = "^TWII", "台股加權指數"
elif "標普 500" in market_choice:
    main_ticker, market_name = "^GSPC", "美股標普 500"
else:
    main_ticker, market_name = "^IXIC", "美股納斯達克"

with st.spinner(f'📡 讀取 {market_name} 究極戰情室數據中...'):
    try:
        df, mtf_status, port_data, port_info = fetch_market_data(main_ticker, user_input)
        latest, prev = df.iloc[-1], df.iloc[-2]
        
        # 動態抓取欄位
        bbu_col =[c for c in df.columns if c.startswith('BBU')][0]
        bbl_col =[c for c in df.columns if c.startswith('BBL')][0]
        macd_col =[c for c in df.columns if c.startswith('MACD_')][0]
        macdh_col =[c for c in df.columns if c.startswith('MACDh_')][0]
        macds_col =[c for c in df.columns if c.startswith('MACDs_')][0]
        k_col =[c for c in df.columns if c.startswith('STOCHk')][0]
        d_col =[c for c in df.columns if c.startswith('STOCHd')][0]

        c, m5, m20, m60 = latest['Close'], latest['SMA_5'], latest['SMA_20'], latest['SMA_60']
        rsi, macd, macdh = latest['RSI_14'], latest[macd_col], latest[macdh_col]
        bbu, bbl = latest[bbu_col], latest[bbl_col]
        
        change = c - prev['Close']
        change_pct = (change / prev['Close']) * 100
        
        down_prob = min(max(int((rsi - 50) * 1.5 + ((c - m20)/m20*100 * 5)), 10), 85)
        up_prob = max(100 - down_prob - 15, 5)
        flat_prob = 100 - up_prob - down_prob

        # --- 頂部 Header ---
        st.markdown(f"""
        <div class="custom-header">
            <div class="header-meta">ULTIMATE WAR ROOM · {market_name} · {datetime.now().strftime('%Y.%m.%d')}</div>
            <h1>{market_name} <span>究極量化戰情室</span></h1>
            <div style="font-family: 'JetBrains Mono'; font-size: 22px; font-weight: 700; color: {'#e05c5c' if change>=0 else '#4caf82'}; margin-top: 15px;">
                {c:,.2f} {'▲' if change>=0 else '▼'} {change:+.2f} ({change_pct:+.2f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_main, col_side = st.columns([7, 3])

        with col_main:
            st.markdown(f"<h4 style='color:#c9a84c; font-family:Noto Serif TC;'>📈 綜合指標主圖 (K線/量/KD/MACD)</h4>", unsafe_allow_html=True)
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.5, 0.15, 0.15, 0.2])
            
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#e05c5c', decreasing_line_color='#4caf82', name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='5MA', line=dict(color='#c9a84c', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20MA', line=dict(color='#4a8fe8', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbu_col], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dot'), name='上軌'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbl_col], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dot'), name='下軌', fill='tonexty', fillcolor='rgba(255,255,255,0.02)'), row=1, col=1)

            colors =['#e05c5c' if row['Close'] >= row['Open'] else '#4caf82' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df[k_col], mode='lines', name='K', line=dict(color='#e05c5c', width=1.5)), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[d_col], mode='lines', name='D', line=dict(color='#4a8fe8', width=1.5)), row=3, col=1)
            fig.add_hline(y=80, line_dash="dot", line_color="rgba(255,255,255,0.2)", row=3, col=1)
            fig.add_hline(y=20, line_dash="dot", line_color="rgba(255,255,255,0.2)", row=3, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df[macd_col], mode='lines', name='DIF', line=dict(color='#e05c5c', width=1.5)), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[macds_col], mode='lines', name='MACD', line=dict(color='#4a8fe8', width=1.5)), row=4, col=1)
            macd_colors =['#e05c5c' if val >= 0 else '#4caf82' for val in df[macdh_col]]
            fig.add_trace(go.Bar(x=df.index, y=df[macdh_col], marker_color=macd_colors, name='OSC'), row=4, col=1)

            fig.update_layout(paper_bgcolor='#0a0c10', plot_bgcolor='#111318', font=dict(color='#7a8090', family='JetBrains Mono'), margin=dict(l=10, r=40, t=10, b=10), height=700, showlegend=False, xaxis=dict(rangeslider=dict(visible=False)), xaxis4=dict(showgrid=True, gridcolor='#1e2433'))
            fig.update_yaxes(showgrid=True, gridcolor='#1e2433', tickfont=dict(size=10))
            fig.update_xaxes(showgrid=True, gridcolor='#1e2433', showticklabels=False)
            fig.update_xaxes(showticklabels=True, row=4, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with col_side:
            st.markdown(f"<h4 style='color:#c9a84c; font-family:Noto Serif TC;'>📊 多週期與籌碼總覽</h4>", unsafe_allow_html=True)
            
            # 【新增】多週期趨勢面板
            st.markdown(f"""
            <div class="mtf-grid">
                <div class="mtf-card"><div style="font-size:11px;color:#7a8090;">短線 (60分K)</div><div style="font-weight:bold;color:{'#e05c5c' if '多' in mtf_status['short'] else '#4caf82'};">{mtf_status['short']}</div></div>
                <div class="mtf-card"><div style="font-size:11px;color:#7a8090;">中線 (日K)</div><div style="font-weight:bold;color:{'#e05c5c' if '多' in mtf_status['mid'] else '#4caf82'};">{mtf_status['mid']}</div></div>
                <div class="mtf-card"><div style="font-size:11px;color:#7a8090;">長線 (週K)</div><div style="font-weight:bold;color:{'#e05c5c' if '多' in mtf_status['long'] else '#4caf82'};">{mtf_status['long']}</div></div>
            </div>
            """, unsafe_allow_html=True)
            
            # 【新增】台灣三大法人籌碼面 (僅在台股模式顯示)
            if market_name == "台股加權指數":
                chips = fetch_taiwan_chips()
                if chips:
                    st.markdown(f"""
                    <div class="panel-box">
                        <div class="panel-title">💰 三大法人買賣超 (億元) <span>- {chips['date']}</span></div>
                        <div class="panel-item"><span class="panel-key">外資及陸資</span><span class="panel-val" style="color:{'#e05c5c' if chips['foreign']>0 else '#4caf82'}">{chips['foreign']:+.1f}</span></div>
                        <div class="panel-item"><span class="panel-key">投信</span><span class="panel-val" style="color:{'#e05c5c' if chips['trust']>0 else '#4caf82'}">{chips['trust']:+.1f}</span></div>
                        <div class="panel-item"><span class="panel-key">自營商</span><span class="panel-val" style="color:{'#e05c5c' if chips['dealer']>0 else '#4caf82'}">{chips['dealer']:+.1f}</span></div>
                        <div class="panel-item"><span class="panel-key" style="color:#fff;">合計</span><span class="panel-val" style="color:{'#e05c5c' if sum([chips['foreign'],chips['trust'],chips['dealer']])>0 else '#4caf82'}">{sum([chips['foreign'],chips['trust'],chips['dealer']]):+.1f} 億</span></div>
                    </div>
                    """, unsafe_allow_html=True)

            # 原有的機率預測
            st.markdown(f"""
            <div class="panel-box">
                <div class="panel-title">🔥 明日走勢機率預測 (AI 模型)</div>
                <div class="prob-grid">
                    <div class="prob-card" style="border-top-color: #e05c5c;">
                        <div class="prob-title">上漲機率</div>
                        <div class="prob-val" style="color: #e05c5c;">{up_prob}%</div>
                    </div>
                    <div class="prob-card" style="border-top-color: #4caf82;">
                        <div class="prob-title">下跌機率</div>
                        <div class="prob-val" style="color: #4caf82;">{down_prob}%</div>
                    </div>
                    <div class="prob-card" style="border-top-color: #e8a24a;">
                        <div class="prob-title">震盪機率</div>
                        <div class="prob-val" style="color: #e8a24a;">{flat_prob}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- 下半部：持股卡片 (新增基本面) ---
        st.write("---")
        st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC;'>💼 您的全球持股即時監控 (技術+基本面)</h4>", unsafe_allow_html=True)
        cols = st.columns(len(port_data) if len(port_data) > 0 else 1)
        for idx, p in enumerate(port_data):
            with cols[idx]:
                st.markdown(f"""
                <div style="background:#111318; border:1px solid #1e2433; padding:15px; border-radius:4px; border-top:3px solid {'#e05c5c' if p['c']>p['m20'] else '#4caf82'};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#c9a84c; font-family:'JetBrains Mono'; font-size:16px; font-weight:bold;">{p['ticker']}</span>
                        <span style="font-size:10px; color:#7a8090; border:1px solid #333; padding:2px 5px; border-radius:2px;">PE: {p['pe']}</span>
                    </div>
                    <div style="font-family:'JetBrains Mono'; font-size:26px; font-weight:900; color:#fff; margin:8px 0;">{p['c']:.2f}</div>
                    <div style="font-size:12px; color:#7a8090; margin-bottom:5px;">月線: {p['m20']:.2f} | 殖利率: <span style="color:#e8a24a;">{p['yield']}%</span></div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC; margin-top:30px;'>🤖 戰情室專屬 AI 深度解析</h4>", unsafe_allow_html=True)
        ai_html = get_ai_report(market_name, c, m5, m20, rsi, port_info)
        st.markdown(ai_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"系統執行錯誤：{e}")
