import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
# 1. 頁面配置與 CSS 風格
# ══════════════════════════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="台股戰情儀表板")

st.markdown("""
    <style>
    .main { background-color: #050A14; }
    .stMetric { background-color: #0A1221; border: 1px solid #1E3A5F; padding: 10px; border-radius: 5px; }
    div[data-testid="stExpander"] { background-color: #0A1221; border: 1px solid #1E3A5F; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    h1, h2, h3 { color: #00F2FF !important; }
    </style>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# 2. 數據處理函式
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_data(ticker):
    if "." not in ticker: ticker += ".TW"
    try:
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True, progress=False)
        if df.empty: return None
        df = df.reset_index()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        # 技術指標
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        return df
    except:
        return None

def get_indicators(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    diff = last['Close'] - prev['Close']
    pct = (diff / prev['Close']) * 100
    return last, diff, pct

# ══════════════════════════════════════════════════════════════════
# 3. 側邊欄控制
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("🔍 參數設定")
    ticker_input = st.text_input("股票代號", value="3583", help="台股輸入代號即可，美股請輸全名如 TSLA")
    days_to_show = st.slider("顯示天數", 30, 180, 90)
    show_bb = st.checkbox("顯示布林通道", value=False)
    st.info("💡 參考圖 image_f3bc69.jpg 風格設計")

# ══════════════════════════════════════════════════════════════════
# 4. 主介面佈局
# ══════════════════════════════════════════════════════════════════
df = fetch_data(ticker_input)

if df is not None:
    last, diff, pct = get_indicators(df)
    
    # --- 頂部標頭 ---
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.title(f"📈 {ticker_input}")
    with col2:
        st.metric("當前股價", f"{last['Close']:.2f}", f"{pct:.2f}%")
    with col3:
        st.metric("成交量", f"{int(last['Volume']):,}")
    with col4:
        st.metric("5日均價", f"{last['MA5']:.2f}")

    st.divider()

    # --- 中間：主圖表與技術分析 ---
    left_col, right_col = st.columns([7, 3])

    with left_col:
        # K線圖
        plot_df = df.tail(days_to_show)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(
            x=plot_df["Date"], open=plot_df["Open"], high=plot_df["High"],
            low=plot_df["Low"], close=plot_df["Close"], name="K線"
        ), row=1, col=1)
        
        for ma, color in [('MA5', '#FFD700'), ('MA20', '#00F2FF'), ('MA60', '#FF00FF')]:
            fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df[ma], name=ma, line=dict(width=1.5, color=color)), row=1, col=1)

        # 成交量
        vol_colors = ['#FF3131' if c >= o else '#00FF87' for c, o in zip(plot_df["Close"], plot_df["Open"])]
        fig.add_trace(go.Bar(x=plot_df["Date"], y=plot_df["Volume"], marker_color=vol_colors, name="成交量"), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, margin=dict(t=0, b=0, l=0, r=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with right_col:
        st.subheader("📊 技術分析總覽")
        # 模擬圖中的小面板
        st.info(f"**趨勢方向：** {'多頭排列' if last['MA5'] > last['MA20'] else '整理格局'}")
        
        # 關鍵價位
        high_20 = plot_df['High'].max()
        low_20 = plot_df['Low'].min()
        st.error(f"短期壓力：{high_20:.2f}")
        st.success(f"短期支撐：{low_20:.2f}")

        # 勝率儀表板 (模擬圖中圓形圖)
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number", value=62,
            gauge={'bar': {'color': "#00F2FF"}, 'bgcolor': "#0A1221", 'axis': {'range': [0, 100]}},
            title={'text': "短線勝率 (%)", 'font': {'size': 16}}
        ))
        gauge_fig.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=40, b=0, l=20, r=20))
        st.plotly_chart(gauge_fig, use_container_width=True)

    # --- 底部：操作劇本與型態 ---
    st.subheader("🎯 隔日操作劇本預測")
    s_col1, s_col2, s_col3 = st.columns(3)
    
    price = last['Close']
    with s_col1:
        st.markdown(f"""<div style="background:#162133;padding:15px;border-radius:5px;border-left:5px solid #FF3131">
        <b>① 開高走高</b><br>進場價：{price*1.01:.1f}<br>目標價：{price*1.05:.1f}<br>停損價：{price*0.98:.1f}</div>""", unsafe_allow_html=True)
    with s_col2:
        st.markdown(f"""<div style="background:#162133;padding:15px;border-radius:5px;border-left:5px solid #FFD700">
        <b>② 震盪整理</b><br>進場價：{price*0.99:.1f}<br>目標價：{price*1.03:.1f}<br>停損價：{price*0.96:.1f}</div>""", unsafe_allow_html=True)
    with s_col3:
        st.markdown(f"""<div style="background:#162133;padding:15px;border-radius:5px;border-left:5px solid #00FF87">
        <b>③ 開低回測</b><br>進場價：{price*0.97:.1f}<br>目標價：{price*1.01:.1f}<br>停損價：{price*0.94:.1f}</div>""", unsafe_allow_html=True)

else:
    st.error("無法取得數據，請檢查股票代號是否正確。")
