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
# 1. 網頁基本設定 & 注入戰情室專屬 CSS
# ==========================================
st.set_page_config(page_title="全球 AI 量化戰情室", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
.stApp { background-color: #0a0c10; color: #e8e4dc; font-family: 'Noto Serif TC', sans-serif; }
header {visibility: hidden;}
:root { --gold: #c9a84c; --red: #e05c5c; --green: #4caf82; --amber: #e8a24a; --surface: #111318; --surface2: #181c24; --border: #1e2433; --text-dim: #7a8090; }
.custom-header { border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 15px; position: relative; }
.custom-header h1 { font-size: 28px; font-weight: 900; color: #fff; margin: 0;}
.panel-box { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 12px; margin-bottom: 12px; height: 100%; }
.panel-title { font-size: 14px; font-family: 'Noto Serif TC'; color: #fff; border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 8px; font-weight: bold; text-align: center; }
.panel-item { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px dashed rgba(255,255,255,0.05); }
.panel-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.panel-key { color: var(--text-dim); }
.panel-val { font-family: 'JetBrains Mono', monospace; font-weight: bold; }
.gann-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; background: var(--border); border-radius: 4px; overflow: hidden; margin-top: 5px; }
.gann-cell { background: var(--surface2); padding: 5px; text-align: center; font-size: 11px; }
.prob-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 8px; }
.prob-card { background: var(--surface2); padding: 10px 5px; text-align: center; border-radius: 4px; border-top: 3px solid #333; }
.prob-val { font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 900; margin-top: 5px;}
.bullet-list { font-size: 12px; color: var(--text-dim); line-height: 1.6; margin:0; padding-left: 15px;}
.bullet-list li { margin-bottom: 4px; }
.bb-text { font-family: 'JetBrains Mono'; font-size: 12px; color: var(--text-dim); margin-right: 15px;}
.theory-block { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 20px; margin-bottom: 16px; }
.theory-block-title { font-size: 14px; font-family: 'JetBrains Mono', monospace; color: var(--gold); letter-spacing: 0.12em; margin-bottom: 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px;}
.theory-text { font-size: 15px; color: #e8e4dc; line-height: 1.8; }
.theory-text strong { color: var(--amber); }

/* 四宮格強制對齊 */
.four-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; align-items: stretch; }
.four-grid .panel-box { margin-bottom: 0; display: flex; flex-direction: column; }
@media (max-width: 1024px) { .four-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .four-grid { grid-template-columns: 1fr; } }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 2. 側邊欄 
# ==========================================
st.sidebar.markdown("<h3 style='color:#c9a84c;'>🌍 全球投資組合設定</h3>", unsafe_allow_html=True)
market_choice = st.sidebar.radio("📊 大盤基準",["台股加權指數 (^TWII)", "美股標普 500 (^GSPC)", "美股納斯達克 (^IXIC)"])
st.sidebar.write("---")
with st.sidebar.form("setting_form"):
    user_input = st.text_area("請輸入持股代號 (用逗號分隔)", "2330.TW, 2408.TW, NVDA")
    submit_btn = st.form_submit_button("🚀 更新戰情室數據")

# ==========================================
# 3. 核心函數與快取
# ==========================================
@st.cache_data(ttl=86400)
def get_stock_name(ticker):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={ticker}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        return res['quotes'][0]['shortname']
    except: return ""

@st.cache_data(ttl=1800)
def fetch_market_data(main_ticker, tickers_str):
    df = yf.Ticker(main_ticker).history(period="6mo")
    df.ta.sma(length=5, append=True)
    df.ta.sma(length=10, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=60, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.macd(append=True)
    df.ta.stoch(append=True)
    
    df_wk = yf.Ticker(main_ticker).history(period="2y", interval="1wk")
    df_wk.ta.sma(length=20, append=True)
    
    tickers =[t.strip() for t in tickers_str.split(",") if t.strip()]
    p_data, p_info =[], ""
    for t in tickers:
        stk = yf.Ticker(t).history(period="3mo")
        if not stk.empty and len(stk) >= 20:
            stk.ta.sma(length=5, append=True)
            stk.ta.sma(length=20, append=True)
            sc, sm5, sm20 = stk['Close'].iloc[-1], stk['SMA_5'].iloc[-1], stk['SMA_20'].iloc[-1]
            stock_name = get_stock_name(t)
            display_ticker = f"{t.upper()} {stock_name}" if stock_name else t.upper()
            p_data.append({"ticker": display_ticker, "c": sc, "m5": sm5, "m20": sm20})
            p_info += f"- {display_ticker}: 收盤 {sc:.2f}, 5MA {sm5:.2f}, 20MA {sm20:.2f}。\n"
    return df, df_wk, p_data, p_info

# 🌟 【核心升級】直連台灣證券交易所官方 OpenAPI
@st.cache_data(ttl=3600)
def fetch_taiwan_chips():
    try:
        # 完全免費、無流量限制的政府 API，抓取最新一日的三大法人買賣超
        url = "https://openapi.twse.com.tw/v1/fund/BFI82U"
        res = requests.get(url, timeout=5).json()
        
        chips = {"date": "", "f": 0, "t": 0, "d": 0}
        for row in res:
            # 取得日期 (民國年)
            chips["date"] = row.get("Day_Date", "")
            name = row.get("TYPEK", "")
            
            # 取得買賣差額 (字串去逗號，換算成億元)
            diff_str = str(row.get("Buy_Sell_Difference", "0")).replace(',', '')
            net_val = float(diff_str) / 100000000 
            
            if '外資' in name:
                chips['f'] += net_val
            elif '投信' in name:
                chips['t'] += net_val
            elif '自營商' in name:
                chips['d'] += net_val
                
        # 將民國年轉為西元年格式 (例: 1130506 -> 2024-05-06)
        if chips["date"]:
            y = int(chips["date"][:-4]) + 1911
            m = chips["date"][-4:-2]
            d = chips["date"][-2:]
            chips["date"] = f"{y}-{m}-{d}"
            
        return chips
    except Exception as e:
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
        我的持股組合如下: 
        {p_info}

        請提供深度分析報告。你**必須完全使用以下 HTML 結構與 Class 排版**。
        ⚠️ 嚴格規定 1：請直接輸出純 HTML，絕對不要包含 ```html 標記，也絕對不要在每一行開頭加上空白縮排！
        ⚠️ 嚴格規定 2：針對個股分析時，請【完全照抄】我提供給你的「代號與股票名稱」，絕對不准自行猜測、翻譯或捏造股票名稱！

<div class="theory-block">
<div class="theory-block-title">▸ 【{market_name}】解析 (波浪與纏論視角)</div>
<div class="theory-text">
(你的大盤分析內容，重點文字請使用 <strong> 標籤包裝)
</div>
</div>

<div class="theory-block">
<div class="theory-block-title">▸ 明早走勢推演與實戰策略</div>
<div class="theory-text">
(你的策略推演，若有看空/危險的文字請加上 <span style="color:#e05c5c">，看多請加上 <span style="color:#4caf82">)
</div>
</div>

<div class="theory-block">
<div class="theory-block-title">▸ 💼 全球專屬持股診斷</div>
<div class="theory-text">
<ul>
(請針對每一檔股票輸出一個 <li> 標籤，並將股票名稱用 <strong>【】</strong> 包起來)
</ul>
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
        clean_text = "\n".join([line.strip() for line in raw_text.split('\n')])
        return clean_text
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

with st.spinner(f'📡 讀取 {market_name} 戰情室數據中...'):
    try:
        df, df_wk, port_data, port_info = fetch_market_data(main_ticker, user_input)
        
        bbu_col =[c for c in df.columns if c.startswith('BBU')][0]
        bbm_col =[c for c in df.columns if c.startswith('BBM')][0]
        bbl_col =[c for c in df.columns if c.startswith('BBL')][0]
        macd_col =[c for c in df.columns if c.startswith('MACD_')][0]
        macdh_col =[c for c in df.columns if c.startswith('MACDh_')][0]
        macds_col =[c for c in df.columns if c.startswith('MACDs_')][0]
        k_col =[c for c in df.columns if c.startswith('STOCHk')][0]
        d_col =[c for c in df.columns if c.startswith('STOCHd')][0]

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        c, o, h, l, vol = latest['Close'], latest['Open'], latest['High'], latest['Low'], latest['Volume']
        m5, m10, m20, m60 = latest['SMA_5'], latest['SMA_10'], latest['SMA_20'], latest['SMA_60']
        bbu, bbm, bbl = latest[bbu_col], latest[bbm_col], latest[bbl_col]
        rsi, k, d, macdh = latest['RSI_14'], latest[k_col], latest[d_col], latest[macdh_col]
        
        change = c - prev['Close']
        change_pct = (change / prev['Close']) * 100
        color_main = '#e05c5c' if change >= 0 else '#4caf82' 
        
        trend_dir = "多頭趨勢" if c > m20 else "空頭趨勢"
        ma_status = "多頭排列" if m5 > m20 > m60 else "空頭排列" if m5 < m20 < m60 else "震盪糾結"
        price_pos = "貼近上軌 (過熱)" if c > bbu * 0.98 else "貼近下軌 (超賣)" if c < bbl * 1.02 else "中軌震盪"
        
        # 修正：提醒 Yahoo 對台股大盤成交量的不準確性
        vol_note = "(註: 台股大盤量為股數)" if market_name == "台股加權指數" else ""
        vol_status = f"量增上漲 {vol_note}" if vol > prev['Volume'] and change > 0 else f"量縮震盪 {vol_note}"
        
        bb_status = "開口擴大" if (bbu - bbl) > (prev[bbu_col] - prev[bbl_col]) else "通道收斂"
        macd_status = "多頭延續" if macdh > 0 and macdh > prev[macdh_col] else "多頭降溫" if macdh > 0 else "空頭延續"
        
        down_prob = min(max(int((rsi - 50) * 1.5 + ((c - m20)/m20*100 * 5)), 10), 85)
        up_prob = max(100 - down_prob - 15, 5)
        flat_prob = 100 - up_prob - down_prob

        # --- 頂部 Header ---
        header_html = f"""
<div class="custom-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
<div>
<h1>{market_name} <span style="font-family:'JetBrains Mono'; font-size:32px; color:{color_main};">{c:,.2f}</span></h1>
<div style="font-family:'JetBrains Mono'; font-size:14px; color:{color_main};">{'▲' if change>=0 else '▼'} {change:+.2f} ({change_pct:+.2f}%)</div>
</div>
<div>
<span class="bb-text">布林上軌 <span style="color:#e05c5c">{bbu:,.0f}</span></span>
<span class="bb-text">中軌 <span style="color:#e8a24a">{bbm:,.0f}</span></span>
<span class="bb-text">下軌 <span style="color:#4caf82">{bbl:,.0f}</span></span>
</div>
</div>
"""
        st.markdown(header_html, unsafe_allow_html=True)

        # --- 第一層：主圖與技術總覽 ---
        col_main, col_side = st.columns([7, 3])

        with col_main:
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.5, 0.15, 0.15, 0.2])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#e05c5c', decreasing_line_color='#4caf82', name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='5MA', line=dict(color='#e8a24a', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20MA', line=dict(color='#c9a84c', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], mode='lines', name='60MA', line=dict(color='#4a8fe8', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbu_col], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dot'), name='上軌'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbl_col], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dot'), name='下軌', fill='tonexty', fillcolor='rgba(255,255,255,0.02)'), row=1, col=1)
            colors =['#e05c5c' if row['Close'] >= row['Open'] else '#4caf82' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[k_col], mode='lines', name='K', line=dict(color='#e05c5c', width=1.5)), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[d_col], mode='lines', name='D', line=dict(color='#4a8fe8', width=1.5)), row=3, col=1)
            fig.add_hline(y=80, line_dash="dot", line_color="rgba(255,255,255,0.2)", row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[macd_col], mode='lines', name='DIF', line=dict(color='#e05c5c', width=1.5)), row=4, col=1)
            macd_colors =['#e05c5c' if val >= 0 else '#4caf82' for val in df[macdh_col]]
            fig.add_trace(go.Bar(x=df.index, y=df[macdh_col], marker_color=macd_colors, name='OSC'), row=4, col=1)

            fig.update_layout(paper_bgcolor='#0a0c10', plot_bgcolor='#111318', font=dict(color='#7a8090', family='JetBrains Mono'), margin=dict(l=5, r=5, t=5, b=5), height=550, showlegend=False, xaxis=dict(rangeslider=dict(visible=False)), xaxis4=dict(showgrid=True, gridcolor='#1e2433'))
            fig.update_yaxes(showgrid=True, gridcolor='#1e2433', tickfont=dict(size=10))
            fig.update_xaxes(showgrid=True, gridcolor='#1e2433', showticklabels=False)
            fig.update_xaxes(showticklabels=True, row=4, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with col_side:
            tech_html = f"""
<div class="panel-box">
<div class="panel-title">技術分析總覽</div>
<div class="panel-item"><span class="panel-key">趨勢方向</span><span class="panel-val" style="color:{'#e05c5c' if c>m20 else '#4caf82'}">{'⬆' if c>m20 else '⬇'} {trend_dir}</span></div>
<div class="panel-item"><span class="panel-key">價格位置</span><span class="panel-val" style="color:#e8a24a">➡ {price_pos}</span></div>
<div class="panel-item"><span class="panel-key">均線排列</span><span class="panel-val">➡ {ma_status}</span></div>
<div class="panel-item"><span class="panel-key">量價關係</span><span class="panel-val">➡ {vol_status}</span></div>
<div class="panel-item"><span class="panel-key">布林通道</span><span class="panel-val">➡ {bb_status}</span></div>
</div>
"""
            st.markdown(tech_html, unsafe_allow_html=True)

            if market_name == "台股加權指數":
                chips = fetch_taiwan_chips()
                if chips:
                    chip_html = f"""
<div class="panel-box">
<div class="panel-title">三大法人籌碼 (億元) <span style="font-size:10px;font-weight:normal;color:#7a8090;">{chips['date']}</span></div>
<div class="panel-item"><span class="panel-key">外資</span><span class="panel-val" style="color:{'#e05c5c' if chips['f']>0 else '#4caf82'}">{chips['f']:+.0f}</span></div>
<div class="panel-item"><span class="panel-key">投信</span><span class="panel-val" style="color:{'#e05c5c' if chips['t']>0 else '#4caf82'}">{chips['t']:+.0f}</span></div>
<div class="panel-item"><span class="panel-key">自營商</span><span class="panel-val" style="color:{'#e05c5c' if chips['d']>0 else '#4caf82'}">{chips['d']:+.0f}</span></div>
</div>
"""
                    st.markdown(chip_html, unsafe_allow_html=True)
            else:
                wk_trend = "多頭延續" if df_wk['Close'].iloc[-1] > df_wk['SMA_20'].iloc[-1] else "空頭回落"
                wk_html = f"""
<div class="panel-box">
<div class="panel-title">多週期趨勢分析</div>
<div class="panel-item"><span class="panel-key">日K (中線)</span><span class="panel-val" style="color:{'#e05c5c' if c>m20 else '#4caf82'}">{trend_dir}</span></div>
<div class="panel-item"><span class="panel-key">週K (長線)</span><span class="panel-val" style="color:{'#e05c5c' if '多' in wk_trend else '#4caf82'}">{wk_trend}</span></div>
</div>
"""
                st.markdown(wk_html, unsafe_allow_html=True)

            levels_html = f"""
<div class="panel-box">
<div class="panel-title">關鍵價位防守</div>
<div class="panel-item"><span class="panel-key" style="color:#e05c5c;">壓力區 (布林上軌)</span><span class="panel-val">{bbu:,.0f} ~ {bbu*1.01:,.0f}</span></div>
<div class="panel-item"><span class="panel-key" style="color:#e8a24a;">回檔區 (5MA~10MA)</span><span class="panel-val">{m10:,.0f} ~ {m5:,.0f}</span></div>
<div class="panel-item"><span class="panel-key" style="color:#4caf82;">支撐區 (月線)</span><span class="panel-val">{bbl:,.0f} ~ {m20:,.0f}</span></div>
</div>
"""
            st.markdown(levels_html, unsafe_allow_html=True)

        # --- 第二層：四宮格 ---
        color_kd = '#e05c5c' if k>d else '#4caf82'
        color_macd = '#e05c5c' if macdh>0 else '#4caf82'
        
        four_grid_html = f"""
<div class="four-grid">

<div class="panel-box">
<div class="panel-title">葛蘭威爾 8 大法則</div>
<div class="gann-grid">
<div class="gann-cell" style="color:#7a8090;">買1<br>止跌</div><div class="gann-cell" style="color:#7a8090;">買2<br>回測</div><div class="gann-cell" style="color:#7a8090;">買3<br>假跌</div><div class="gann-cell" style="color:#7a8090;">買4<br>乖離</div>
<div class="gann-cell" style="color:#7a8090;">賣1<br>轉跌</div><div class="gann-cell" style="color:#7a8090;">賣2<br>遇壓</div><div class="gann-cell" style="color:#e8a24a;">賣3<br>假突</div><div class="gann-cell" style="color:#e05c5c;font-weight:bold;">賣4<br>超買</div>
</div>
<div style="font-size:12px; color:#7a8090; margin-top:10px;">現狀評估：價格距離月線過遠，若出現爆量留長上影線，需提防符合<span style="color:#e05c5c">【賣4】嚴重超買拉回</span>法則。</div>
</div>

<div class="panel-box">
<div class="panel-title">型態分析 (W底 / M頭)</div>
<div style="font-size:13px; margin-bottom:10px;">
<strong style="color:#fff;">W底分析：</strong> <span style="color:#e05c5c;">❌ 未形成標準W底</span><br>
<span style="color:#7a8090; font-size:12px;">理由：目前處於高檔震盪，無明顯打底右肩跡象。</span>
</div>
<div style="font-size:13px;">
<strong style="color:#fff;">M頭分析：</strong> <span style="color:#e8a24a;">⚠️ M頭醞釀疑慮</span><br>
<span style="color:#7a8090; font-size:12px;">理由：若跌破前波低點與月線 ({m20:,.0f})，則頭部成型。</span>
</div>
</div>

<div class="panel-box">
<div class="panel-title">技術指標總覽</div>
<div class="panel-item"><span class="panel-key">KD (9,3,3)</span><span class="panel-val" style="color:{color_kd}">{'⬆' if k>d else '⬇'} {k:.1f}/{d:.1f}</span></div>
<div class="panel-item"><span class="panel-key">MACD</span><span class="panel-val" style="color:{color_macd}">{'⬆' if macdh>0 else '⬇'} {macd_status}</span></div>
<div class="panel-item"><span class="panel-key">均線排列</span><span class="panel-val">{'⬆' if m5>m20 else '⬇'} {'偏多' if m5>m20 else '偏空'}</span></div>
<div class="panel-item"><span class="panel-key">布林通道</span><span class="panel-val">➡ {bb_status.split(' ')[0]}</span></div>
<div class="panel-item"><span class="panel-key">成交量</span><span class="panel-val" title="註: Yahoo對台股大盤量僅提供股數">{'⬆' if vol>prev['Volume'] else '⬇'} {vol_status.split(' ')[0]}</span></div>
</div>

<div class="panel-box">
<div class="panel-title">明日漲跌機率與操作建議</div>
<div class="prob-grid" style="margin-bottom:10px;">
<div class="prob-card" style="border-top-color: #e05c5c;"><div class="prob-title">上漲</div><div class="prob-val" style="color: #e05c5c;">{up_prob}%</div></div>
<div class="prob-card" style="border-top-color: #4caf82;"><div class="prob-title">下跌</div><div class="prob-val" style="color: #4caf82;">{down_prob}%</div></div>
<div class="prob-card" style="border-top-color: #e8a24a;"><div class="prob-title">震盪</div><div class="prob-val" style="color: #e8a24a;">{flat_prob}%</div></div>
</div>
<ul class="bullet-list">
<li><strong style="color:#e8a24a;">策略:</strong> 不追高，等待回檔佈局</li>
<li><strong style="color:#4caf82;">買點:</strong> {m10:,.0f} ~ {m20:,.0f} 附近</li>
<li><strong style="color:#e05c5c;">防守:</strong> 跌破 {m20:,.0f} 轉弱停損</li>
</ul>
</div>

</div>
"""
        st.markdown(four_grid_html, unsafe_allow_html=True)

        # --- 第三層：持股卡片與 AI 長文分析 ---
        st.write("---")
        st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC;'>💼 您的全球持股即時監控</h4>", unsafe_allow_html=True)
        cols = st.columns(len(port_data) if len(port_data) > 0 else 1)
        for idx, p in enumerate(port_data):
            with cols[idx]:
                st.markdown(f"""
<div style="background:#111318; border:1px solid #1e2433; padding:15px; border-radius:4px; border-left:3px solid {'#e05c5c' if p['c']>p['m20'] else '#4caf82'};">
<div style="color:#c9a84c; font-family:'JetBrains Mono'; font-size:16px; font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{p['ticker']}">{p['ticker']}</div>
<div style="font-family:'JetBrains Mono'; font-size:24px; color:#fff; margin:10px 0;">{p['c']:,.2f}</div>
<div style="font-size:12px; color:#7a8090;">5日線: {p['m5']:,.2f} | 月線: {p['m20']:,.2f}</div>
</div>
                """, unsafe_allow_html=True)

        st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC; margin-top:30px;'>🤖 戰情室專屬 AI 深度解析</h4>", unsafe_allow_html=True)
        ai_html = get_ai_report(market_name, c, m5, m20, rsi, port_info)
        st.markdown(ai_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"系統執行錯誤：{e}")
