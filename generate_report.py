import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime
import os
import google.generativeai as genai

# 1. 抓取台股資料並計算指標
df = yf.Ticker("^TWII").history(period="6mo")
df.ta.sma(length=5, append=True)
df.ta.sma(length=20, append=True)
df.ta.rsi(length=14, append=True)
latest = df.iloc[-1]

# 2. 製作 K 線與均線圖 (Plotly)
fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='5日均線', line=dict(color='orange')))
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20日均線(月線)', line=dict(color='purple')))
fig.update_layout(title="台股加權指數日線圖", template="plotly_dark", height=500)
chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

# 3. 呼叫 Google Gemini AI 進行深度分析
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    try:
        genai.configure(api_key=api_key)
        # 使用 gemini-1.5-flash 模型，速度快且免費額度高
        model = genai.GenerativeModel('gemini-pro') 
        
        # 這是給 AI 的指令 (Prompt)
        prompt = f"""
        你是專業的台股分析師。今日台股加權指數收盤為 {latest['Close']:.0f} 點，
        5日均線為 {latest['SMA_5']:.0f}，20日均線為 {latest['SMA_20']:.0f}，RSI 為 {latest['RSI_14']:.1f}。
        請根據以上數據，結合「波浪理論」、「纏論」與「葛蘭威爾八大法則」，寫一份約 300 字的明日行情預測與交易策略。
        
        請直接輸出 HTML 格式（使用 <h3>, <p>, <ul>, <li> 等標籤），不要輸出 Markdown 的 ```html 標記，直接給純 HTML 內容就好。文字要有專業感，並帶有風險提示。
        """
        response = model.generate_content(prompt)
        # 清理多餘的 Markdown 標記
        ai_analysis_html = response.text.replace("```html", "").replace("```", "")
    except Exception as e:
        ai_analysis_html = f"<p style='color:red;'>🤖 AI 分析生成失敗，錯誤訊息：{e}</p>"
else:
    ai_analysis_html = "<p style='color:orange;'>🤖 尚未設定 GEMINI_API_KEY，無法呼叫 AI。</p>"

# 4. 組合最終 HTML 網頁
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>台股每日自動分析報表</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; padding: 20px; line-height: 1.6; max-width: 1200px; margin: auto; }} 
        h1, h2, h3 {{ color: #ffffff; border-bottom: 1px solid #333; padding-bottom: 10px; }} 
        .ai-box {{ background: #1e1e1e; padding: 20px 40px; border-radius: 8px; border-left: 5px solid #00bcd4; }}
    </style>
</head>
<body>
    <h1>🌟 台股加權指數 每日AI分析報表</h1>
    <p style="color: #888;">報表生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    {chart_html}
    
    <h2>🤖 AI 深度技術分析 (波浪理論 / 纏論 / 葛蘭威爾)</h2>
    <div class="ai-box">
        {ai_analysis_html}
    </div>
</body>
</html>
"""

# 5. 存檔
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
