import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 抓取台股資料
df = yf.Ticker("^TWII").history(period="3mo")

# 2. 製作 K 線圖 (Plotly)
fig = go.Figure(data=[go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'])])
fig.update_layout(title="台股加權指數日線圖", template="plotly_dark")

# 把圖表轉成 HTML 語法
chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

# 3. 這裡可以加入呼叫 AI API 的程式碼，產生波浪/纏論分析文字
ai_analysis_text = "<p>今日台股強勢突破，符合葛蘭威爾法則第四條，留意乖離過大拉回風險...</p>"

# 4. 把所有內容組合合成一個網頁 (index.html)
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>台股每日自動分析報表</title>
    <meta charset="utf-8">
    <style>body {{ font-family: Arial; background-color: #1e1e1e; color: white; padding: 20px; }}</style>
</head>
<body>
    <h1>🌟 台股加權指數 每日分析報表</h1>
    <p>更新時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    {chart_html}
    <h2>🤖 AI 技術深度分析 (波浪/纏論)</h2>
    {ai_analysis_text}
</body>
</html>
"""

# 5. 存檔！這就是你要展示的網頁
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
