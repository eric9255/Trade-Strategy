import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import math

# ==========================================
# 1. 網頁基本設定 & 注入您的專屬 CSS 樣式
# ==========================================
st.set_page_config(page_title="台股 AI 量化分析系統", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

/* 覆寫 Streamlit 全局背景與字體 */
.stApp {
    background-color: #0a0c10;
    color: #e8e4dc;
    font-family: 'Noto Serif TC', serif;
}
/* 隱藏預設的頂部裝飾 */
header {visibility: hidden;}

/* 您專屬的 CSS 變數與樣式 */
:root {
    --gold: #c9a84c;
    --red: #e05c5c;
    --green: #4caf82;
    --amber: #e8a24a;
    --surface: #111318;
    --surface2: #181c24;
    --border: #1e2433;
    --text-dim: #7a8090;
}

.custom-header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px; margin-bottom: 30px; position: relative;
}
.custom-header::after {
    content: ''; position: absolute; bottom: -1px; left: 0;
    width: 120px; height: 2px; background: linear-gradient(90deg, var(--gold), transparent);
}
.header-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--gold); letter-spacing: 0.2em; }
.custom-header h1 { font-size: 38px; font-weight: 900; color: #fff; margin: 10px 0;}
.custom-header h1 span { color: var(--gold); }

.theory-block { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 20px; margin-bottom: 16px; }
.theory-block-title { font-size: 14px; font-family: 'JetBrains Mono', monospace; color: var(--gold); letter-spacing: 0.12em; margin-bottom: 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px;}
.theory-text { font-size: 15px; color: #e8e4dc; line-height: 1.8; }
.theory-text strong { color: var(--amber); }

.pullback-hero { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 32px; margin-bottom: 32px; position: relative; overflow: hidden; }
.pullback-hero::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--red) 0%, var(--amber) 50%, var(--green) 100%); }
.verdict-text { font-size: 26px; font-weight: 900; color: var(--amber); line-height: 1.2; }
.signal-bar-badge { font-size: 10px; font-family: 'JetBrains Mono', monospace; padding: 2px 8px; border-radius: 2px; font-weight: 700; color: var(--red); border: 1px solid rgba(224,92,92,0.3); background: rgba(224,92,92,0.15);}
.signal-bar-badge.bull { color: var(--green); border: 1px solid rgba(76,175,130,0.3); background: rgba(76,175,130,0.15);}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ==========================================
# 2. 側邊欄與資料抓取
# ==========================================
st.sidebar.markdown("<h3 style='color:#c9a84c; font-family: Noto Serif TC;'>💼 投資組合設定</h3>", unsafe_allow_html=True)
user_input = st.sidebar.text_area("請輸入持股代號 (用逗號分隔)", "2330.TW, 2317.TW, 2603.TW")

if 'auto_run' not in st.session_state:
    st.session_state.auto_run = True

if st.sidebar.button("🚀 啟動量化分析引擎") or st.session_state.auto_run:
    st.session_state.auto_run = False
    
    with st.spinner('📡 抓取最新市場數據中...'):
        # 抓大盤資料
        df = yf.Ticker("^TWII").history(period="6mo")
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.rsi(length=14, append=True)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        c, m5, m20, rsi = latest['Close'], latest['SMA_5'], latest['SMA_20'], latest['RSI_14']
        change = c - prev['Close']
        change_pct = (change / prev['Close']) * 100
        
        bias_pct = ((c - m20) / m20) * 100
        pullback_prob = min(max(int((rsi - 50) * 2 + (bias_pct * 5)), 10), 95) # 模擬計算拉回機率
        
        # --- 渲染絕美頂部 Header ---
        st.markdown(f"""
        <div class="custom-header">
            <div class="header-meta">台灣證券交易所 · 加權指數 · 日線技術分析 · {datetime.now().strftime('%Y.%m.%d')}</div>
            <h1>台股加權指數<br><span>拉回機率綜合評估報告</span></h1>
            <div style="font-family: 'JetBrains Mono'; font-size: 22px; font-weight: 700; color: {'#e05c5c' if change<0 else '#4caf82'}; margin-top: 15px;">
                {c:,.2f} {'▼' if change<0 else '▲'} {change:+.2f} ({change_pct:+.2f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- 渲染您設計的儀表板 ---
        st.markdown(f"""
        <div class="pullback-hero">
            <h4 style="color:#c9a84c; font-family:'JetBrains Mono'; font-size:14px; margin-bottom:20px;">▸ 明日拉回機率綜合儀表</h4>
            <div style="display: flex; gap: 40px; align-items: center;">
                <div>
                    <div style="font-family:'JetBrains Mono'; font-size:50px; color:{'#e05c5c' if pullback_prob>60 else '#4caf82'}; font-weight:900;">{pullback_prob}%</div>
                    <div style="color:#7a8090; font-size:12px;">量化估算拉回機率</div>
                </div>
                <div>
                    <div class="verdict-text">{'高度拉回風險 ⚠' if pullback_prob>70 else '中度震盪整理' if pullback_prob>40 else '強勢多頭延續 🚀'}</div>
                    <div style="color:#7a8090; font-size:14px; margin-top:10px;">
                        目前 RSI(14) 數值為 <strong>{rsi:.1f}</strong>，月線乖離率達 <strong>{bias_pct:+.2f}%</strong>。<br>
                        大數據模型顯示，當前客觀狀態下，市場產生短期修正或震盪洗盤的機率顯著。
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- 繪製暗黑奢華版 Plotly K 線圖 ---
        st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC; margin-top:20px;'>01. 日線走勢與均線 (Interactive Chart)</h4>", unsafe_allow_html=True)
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
                                             increasing_line_color='#4caf82', decreasing_line_color='#e05c5c', name='K線')])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='5日均線', line=dict(color='#c9a84c', width=1.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20日均線(月線)', line=dict(color='#4a8fe8', width=1.5)))
        
        # 配合您的背景色
        fig.update_layout(
            paper_bgcolor='#111318', plot_bgcolor='#111318',
            font=dict(color='#7a8090', family='JetBrains Mono'),
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(showgrid=True, gridcolor='#1e2433', rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor='#1e2433')
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 個股清單抓取 ---
        tickers =[t.strip() for t in user_input.split(",")]
        portfolio_prompt_info = ""
        st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC; margin-top:20px;'>02. 您的專屬持股即時狀態</h4>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        cols = [col1, col2, col3, col4]
        
        for idx, ticker in enumerate(tickers):
            if not ticker: continue
            stk_df = yf.Ticker(ticker).history(period="1mo")
            if not stk_df.empty and len(stk_df) >= 20:
                stk_df.ta.sma(length=5, append=True)
                stk_df.ta.sma(length=20, append=True)
                sc, sm5, sm20 = stk_df.iloc[-1]['Close'], stk_df.iloc[-1]['SMA_5'], stk_df.iloc[-1]['SMA_20']
                portfolio_prompt_info += f"- {ticker}: 收盤 {sc:.1f}, 5MA {sm5:.1f}, 20MA {sm20:.1f}。\n"
                
                # 繪製精美個股卡片
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div style="background:#111318; border:1px solid #1e2433; padding:15px; border-radius:4px; border-left:3px solid {'#4caf82' if sc>sm20 else '#e05c5c'};">
                        <div style="color:#c9a84c; font-family:'JetBrains Mono'; font-size:16px; font-weight:bold;">{ticker}</div>
                        <div style="font-family:'JetBrains Mono'; font-size:24px; color:#fff; margin:10px 0;">{sc:.1f}</div>
                        <div style="font-size:12px; color:#7a8090;">5日線: {sm5:.1f} | 月線: {sm20:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)


    # ==========================================
    # 3. 呼叫 AI 並嚴格指定輸出 HTML 格式
    # ==========================================
    with st.spinner('🤖 AI 量化大腦演算中 (請稍候 10~15 秒)...'):
        api_key = st.secrets.get("GEMINI_API_KEY") 
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # 強制 AI 使用您的 HTML 版型輸出！
                prompt = f"""
                你是頂級量化分析師。大盤收盤 {c:.0f}，5MA {m5:.0f}，20MA {m20:.0f}，RSI {rsi:.1f}。
                我的持股: {portfolio_prompt_info}

                請提供深度分析報告。你**必須完全使用以下 HTML 結構與 Class 進行排版**（請直接輸出純 HTML，不要包含 ```html 標記）：

                <div class="theory-block">
                    <div class="theory-block-title">▸ 大盤解析 (波浪與纏論視角)</div>
                    <div class="theory-text">
                        (你的分析內容，重點文字請使用 <strong> 標籤包裝)
                    </div>
                </div>

                <div class="theory-block">
                    <div class="theory-block-title">▸ 明早拉回機率與實戰策略</div>
                    <div class="theory-text">
                        (你的策略推演，若有看空/危險的文字請加上 <span style="color:#e05c5c">，看多請加上 <span style="color:#4caf82">)
                    </div>
                </div>

                <div class="theory-block">
                    <div class="theory-block-title">▸ 💼 我的專屬持股診斷</div>
                    <div class="theory-text">
                        (針對我提供的個股逐一分析，請使用 <ul> <li> 排版)
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
                
                st.markdown("<h4 style='color:#c9a84c; font-family:Noto Serif TC; margin-top:30px;'>03. AI 深度技術分析 (波浪/纏論/葛蘭威爾)</h4>", unsafe_allow_html=True)
                st.markdown(response.text.replace("```html", "").replace("```", ""), unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"🤖 API 錯誤：{e}")
        else:
            st.warning("⚠️ 系統尚未設定 GEMINI_API_KEY。")
