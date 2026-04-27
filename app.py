import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import google.generativeai as genai
import pandas as pd

# 1. 網頁基本設定
st.set_page_config(page_title="台股 AI 專屬分析儀表板", layout="wide")
st.title("🌟 台股大盤與專屬持股 AI 分析系統")
st.markdown(f"**數據更新時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)")

# 2. 側邊欄：讓使用者可以在網頁上動態輸入股票
st.sidebar.header("💼 設定您的投資組合")
st.sidebar.write("請輸入台股代號 (上市加 .TW，上櫃加 .TWO)")
user_input = st.sidebar.text_area("持股清單 (請用逗號分隔)", "2330.TW, 2317.TW, 2603.TW")

# 按下按鈕才開始執行，避免浪費資源
if st.sidebar.button("🚀 開始抓取數據與 AI 診斷"):
    
    with st.spinner('📡 正在抓取大盤與個股最新數據...'):
        # --- 抓取大盤資料 ---
        df = yf.Ticker("^TWII").history(period="6mo")
        df.ta.sma(length=5, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.rsi(length=14, append=True)
        latest = df.iloc[-1]

        # --- 繪製大盤 K 線圖 ---
        st.subheader("📈 台股加權指數 日線圖")
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='5日均線', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20日均線(月線)', line=dict(color='purple')))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # --- 抓取動態輸入的個股資料 ---
        st.subheader("💼 您的專屬持股即時狀態")
        tickers = [t.strip() for t in user_input.split(",")]
        portfolio_data =[]
        portfolio_prompt_info = ""

        for ticker in tickers:
            if not ticker: continue
            stk_df = yf.Ticker(ticker).history(period="2mo")
            if not stk_df.empty and len(stk_df) >= 20:
                stk_df.ta.sma(length=5, append=True)
                stk_df.ta.sma(length=20, append=True)
                c, m5, m20 = stk_df.iloc[-1]['Close'], stk_df.iloc[-1]['SMA_5'], stk_df.iloc[-1]['SMA_20']
                
                status = "🚀 強勢多頭" if c > m5 and c > m20 else "⚠️ 弱勢空頭" if c < m5 and c < m20 else "⚖️ 震盪整理"
                portfolio_data.append({"股票代號": ticker, "今日收盤": round(c,2), "5日均線": round(m5,2), "月線": round(m20,2), "客觀狀態": status})
                portfolio_prompt_info += f"- {ticker}：收盤價 {c:.1f}，5MA為 {m5:.1f}，20MA為 {m20:.1f}。\n"

        # 顯示持股表格
        if portfolio_data:
            st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)

    # --- 呼叫 AI 進行分析 ---
    with st.spinner('🤖 AI 正在進行波浪與纏論深度演算中 (約需 10~15 秒)...'):
        # 在 Streamlit 中讀取安全金鑰的方法
        api_key = st.secrets.get("GEMINI_API_KEY") 
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                prompt = f"""
                你是一位擁有 20 年經驗的頂級台股量化與技術分析師。
                今日大盤客觀數據：收盤 {latest['Close']:.0f}，5MA {latest['SMA_5']:.0f}，20MA {latest['SMA_20']:.0f}，RSI {latest['RSI_14']:.1f}。
                
                除大盤外，我目前持有以下個股，這是最新數據：
                {portfolio_prompt_info}

                請以專業、犀利的語氣寫一份分析報告。必須使用 Markdown 格式排版 (使用 ##, ###, bullet points 等)。
                
                內容必須包含：
                ### 一、 大盤解析 (波浪與纏論視角)
                ### 二、 明早大盤拉回機率與實戰策略
                ### 三、 💼 我的專屬持股診斷
                (針對我提供的每一檔股票，給出明確的技術面點評與進出場/防守建議)
                """
                
                # 自動挑選模型邏輯
                target_model = 'gemini-1.5-flash' # 預設
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods and 'gemini-2.5-flash' in m.name:
                        target_model = m.name
                        break
                        
                model = genai.GenerativeModel(target_model)
                response = model.generate_content(prompt)
                
                st.success(f"✅ AI 分析完成！(使用模型：{target_model})")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"🤖 API 錯誤：{e}")
        else:
            st.warning("⚠️ 系統尚未設定 GEMINI_API_KEY，請在 Streamlit 後台設定 Secrets。")
