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

# 2. 製作 K 線與均線圖
fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='5日均線', line=dict(color='orange')))
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20日均線(月線)', line=dict(color='purple')))
fig.update_layout(title="台股加權指數日線圖", template="plotly_dark", height=500)
chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

# 3. 呼叫 Google Gemini AI (專業長篇分析版)
api_key = os.environ.get("GEMINI_API_KEY")
ai_analysis_html = ""

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # 👑 【旗艦級 Prompt】給 AI 的嚴格寫作藍圖
        prompt = f"""
        你是一位擁有 20 年經驗的頂級台股量化與技術分析師。
        今日台股加權指數客觀數據如下：
        - 收盤價：{latest['Close']:.0f} 點
        - 5日均線 (5MA)：{latest['SMA_5']:.0f} 點
        - 20日均線 (月線/20MA)：{latest['SMA_20']:.0f} 點
        - 14日 RSI：{latest['RSI_14']:.1f}

        請撰寫一份「極度專業、詳細且結構清晰」的明日台股行情預測與交易策略報表（請寫約 600-800 字）。
        必須嚴格按照以下架構，並使用對應的 HTML 標籤進行排版（請直接輸出純 HTML，不要包含 ```html 標記）：

        <h3>一、 價格行為與客觀指標解析</h3>
        <p>(請根據收盤價與均線的乖離率、RSI 是否超買超賣，進行深度點評。語氣要客觀且犀利)</p>

        <h3>二、 深度技術理論探討</h3>
        <ul>
            <li><strong>🌊 波浪理論：</strong> (評估目前台股處於哪個波段？主升段、末升段還是修正波？潛在的轉折點在哪？)</li>
            <li><strong>🧩 纏論結構解析：</strong> (從日線與次級別角度分析，目前是處於中樞震盪、延伸還是背馳狀態？有沒有潛在的買賣點跡象？)</li>
            <li><strong>📐 葛蘭威爾八大法則：</strong> (目前符合八大法則的哪一條？是買進訊號、賣出訊號還是觀望？為什麼？)</li>
        </ul>

        <h3>三、 明早拉回機率評估與劇本推演</h3>
        <p>(請綜合上述理論，給出明早開盤走勢的具體推演，例如高機率拉回測試支撐，或繼續噴出，並詳細說明背後的市場心理與邏輯)</p>

        <h3>四、 日線級別交易策略與具體進出點位</h3>
        <ul>
            <li><strong>🎯 多單防守點 / 第一支撐位：</strong> (給出具體數字點位，並說明原因)</li>
            <li><strong>🛑 停利停損建議：</strong> (跌破哪個數字必須無條件停損出場？)</li>
            <li><strong>💡 資金控管與實戰提醒：</strong> (對於「空手者」與「已持有波段多單者」分別給出具體的行動指引)</li>
        </ul>

        <hr style="border-top: 1px dashed #555;">
        <p style="color: #ff9800; font-size: 0.85em;"><em>⚠️ 專業免責風險提示：本分析報表由 AI 模型自動生成，技術指標與理論分析僅供參考，不構成任何買賣建議。投資人應獨立思考，並自負盈虧。</em></p>
        """
        
        success = False
        error_msgs = []
        available_models =[m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        models_to_try =['models/gemini-2.5-flash', 'models/gemini-1.5-flash', 'models/gemini-1.5-pro']
        for m in available_models:
            if m not in models_to_try:
                models_to_try.append(m)

        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                ai_analysis_html = response.text.replace("```html", "").replace("```", "")
                
                # 隱藏除錯訊息，讓版面更乾淨專業
                # ai_analysis_html = f"<p style='color:#00bcd4; font-size:0.9em;'>✅ 模型：{model_name}</p>" + ai_analysis_html
                
                success = True
                break
                
            except Exception as e:
                error_msgs.append(f"[{model_name}] 失敗")
                continue
                
        if not success:
            ai_analysis_html = f"<p style='color:red;'>🤖 嘗試了所有模型皆失敗。<br>詳細紀錄：<br>" + "<br>".join(error_msgs) + "</p>"
            
    except Exception as main_e:
        ai_analysis_html = f"<p style='color:red;'>🤖 API 核心連線錯誤：{main_e}</p>"
else:
    ai_analysis_html = "<p style='color:orange;'>🤖 尚未設定 GEMINI_API_KEY，無法呼叫 AI。</p>"

# 4. 組合 HTML
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>台股每日自動分析報表</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; padding: 20px; line-height: 1.8; max-width: 1200px; margin: auto; }} 
        h1 {{ color: #ffffff; border-bottom: 2px solid #00bcd4; padding-bottom: 10px; margin-bottom: 5px; }}
        h2 {{ color: #ffffff; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 40px; }} 
        h3 {{ color: #00bcd4; margin-top: 30px; margin-bottom: 15px; font-size: 1.3em; }}
        p {{ margin-bottom: 15px; font-size: 1.05em; }}
        ul {{ background: #1e1e1e; padding: 25px 40px; border-radius: 8px; border-left: 5px solid #00bcd4; margin-bottom: 20px; }}
        li {{ margin-bottom: 15px; font-size: 1.05em; }}
        li strong {{ color: #ffeb3b; font-size: 1.1em; }}
        .ai-box {{ padding: 10px 0; }}
    </style>
</head>
<body>
    <h1>🌟 台股加權指數 每日分析與策略報表</h1>
    <p style="color: #888; font-size: 0.9em;">數據更新與 AI 生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} (UTC)</p>
    
    {chart_html}
    
    <h2>🤖 AI 深度技術與策略分析</h2>
    <div class="ai-box">
        {ai_analysis_html}
    </div>
</body>
</html>
"""

# 5. 存檔
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
