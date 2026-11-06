import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
import sqlite3

# Page config
st.set_page_config(
    page_title="US Stock Watchlist Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup for watchlist
DB_PATH = "watchlist.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist
                 (ticker TEXT PRIMARY KEY, notes TEXT, added_date TEXT)''')
    conn.commit()
    conn.close()

def get_watchlist():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ticker, notes FROM watchlist ORDER BY ticker")
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def add_to_watchlist(ticker, notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO watchlist (ticker, notes, added_date) VALUES (?, ?, ?)",
              (ticker.upper(), notes, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def remove_from_watchlist(ticker):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()

# Initialize
init_db()

# Cache data functions
@st.cache_data(ttl=300)  # 5 min cache
def get_stock_data(ticker, period="6mo"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        info = stock.info
        news = stock.news[:8] if stock.news else []
        return hist, info, news
    except Exception as e:
        st.error(f"Error fetching {ticker}: {e}")
        return None, None, []

@st.cache_data(ttl=300)
def get_market_overview():
    tickers = ["SPY", "QQQ", "DIA", "IWM", "^VIX"]
    data = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if not hist.empty:
                data[t] = {
                    "price": hist['Close'].iloc[-1],
                    "change_1d": ((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100 if len(hist) > 1 else 0,
                    "change_5d": ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
                }
        except:
            data[t] = {"price": 0, "change_1d": 0, "change_5d": 0}
    return data

def calculate_indicators(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=50, append=True)
    df.ta.sma(length=200, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    df.ta.bbands(append=True)
    return df

def get_trend(df):
    if df is None or df.empty or 'SMA_50' not in df.columns:
        return "Insufficient data"
    price = df['Close'].iloc[-1]
    sma50 = df['SMA_50'].iloc[-1]
    sma200 = df['SMA_200'].iloc[-1] if 'SMA_200' in df.columns and not pd.isna(df['SMA_200'].iloc[-1]) else None
    
    if sma200:
        if price > sma50 > sma200:
            return "🟢 Strong Uptrend"
        elif price > sma50 and sma50 < sma200:
            return "🟡 Uptrend (but below 200 SMA)"
        elif price < sma50 < sma200:
            return "🔴 Strong Downtrend"
        else:
            return "🟠 Mixed / Range"
    else:
        if price > sma50:
            return "🟢 Above 50 SMA"
        else:
            return "🔴 Below 50 SMA"

def get_action_signal(df, info):
    if df is None or df.empty:
        return "No data"
    
    price = df['Close'].iloc[-1]
    rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 50
    sma20 = df['SMA_20'].iloc[-1] if 'SMA_20' in df.columns else price
    sma50 = df['SMA_50'].iloc[-1] if 'SMA_50' in df.columns else price
    
    signals = []
    
    # RSI signals
    if rsi < 30:
        signals.append("Oversold RSI")
    elif rsi > 70:
        signals.append("Overbought RSI")
    
    # Trend
    trend = get_trend(df)
    if "Uptrend" in trend:
        signals.append("Uptrend")
    elif "Downtrend" in trend:
        signals.append("Downtrend")
    
    # Distance from MA
    if abs(price - sma50) / sma50 < 0.02:
        signals.append("Near 50 SMA")
    
    # Simple action
    if rsi < 35 and price > sma50:
        return "✅ Potential bounce (oversold in uptrend)"
    elif rsi > 70 and price > sma20 * 1.05:
        return "⚠️ Overbought - caution / consider partial profit"
    elif price > sma50 and "Uptrend" in trend:
        return "📈 Hold / add on dips"
    elif price < sma50 and rsi > 40:
        return "📉 Weak / avoid or short-term only"
    else:
        return "⚪ Neutral - monitor"

# Sidebar
with st.sidebar:
    st.title("📈 Stock Dashboard")
    st.markdown("---")
    
    # Watchlist management
    st.subheader("Watchlist")
    watchlist = get_watchlist()
    
    new_ticker = st.text_input("Add ticker", placeholder="AAPL").upper().strip()
    notes = st.text_input("Notes (optional)", placeholder="Why watching?")
    if st.button("➕ Add to Watchlist") and new_ticker:
        add_to_watchlist(new_ticker, notes)
        st.rerun()
    
    if watchlist:
        remove_ticker = st.selectbox("Remove from watchlist", [""] + list(watchlist.keys()))
        if remove_ticker and st.button("🗑️ Remove"):
            remove_from_watchlist(remove_ticker)
            st.rerun()
    
    st.markdown("---")
    st.caption("Data from Yahoo Finance (delayed). For personal research only.")

# Main content
st.title("US Stock Analysis Dashboard")

# Market Overview
st.subheader("🌐 Market Context")
market = get_market_overview()
cols = st.columns(5)
for i, (ticker, data) in enumerate(market.items()):
    with cols[i]:
        delta_color = "normal" if data["change_1d"] >= 0 else "inverse"
        st.metric(
            ticker,
            f"${data['price']:.2f}" if ticker != "^VIX" else f"{data['price']:.2f}",
            f"{data['change_1d']:+.2f}%",
            delta_color=delta_color
        )

# Simple market bias
spy_change = market.get("SPY", {}).get("change_1d", 0)
vix = market.get("^VIX", {}).get("price", 20)
if spy_change > 0.5 and vix < 20:
    bias = "🟢 Risk-on: Markets higher, VIX calm"
elif spy_change < -0.5 and vix > 25:
    bias = "🔴 Risk-off: Selling pressure, elevated VIX"
else:
    bias = "🟡 Mixed / Neutral market"
st.info(bias)

st.markdown("---")

# Watchlist Action List
st.subheader("📋 Watchlist Action List")
if watchlist:
    action_data = []
    for ticker in watchlist.keys():
        hist, info, _ = get_stock_data(ticker, period="1y")
        if hist is not None and not hist.empty:
            df = calculate_indicators(hist)
            action = get_action_signal(df, info)
            price = hist['Close'].iloc[-1]
            change = ((price / hist['Close'].iloc[-2]) - 1) * 100 if len(hist) > 1 else 0
            rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else None
            action_data.append({
                "Ticker": ticker,
                "Price": f"${price:.2f}",
                "1D %": f"{change:+.2f}%",
                "RSI": f"{rsi:.1f}" if rsi else "-",
                "Trend": get_trend(df),
                "Action": action
            })
    
    if action_data:
        st.dataframe(pd.DataFrame(action_data), use_container_width=True, hide_index=True)
else:
    st.info("Add tickers to your watchlist to see the action list.")

st.markdown("---")

# Individual Stock Analysis
st.subheader("🔍 Stock Analysis")
col1, col2 = st.columns([2, 1])

with col1:
    selected = st.selectbox(
        "Select ticker",
        options=list(watchlist.keys()) + ["Custom..."] if watchlist else ["Custom..."]
    )
    
    if selected == "Custom...":
        selected = st.text_input("Enter ticker", "AAPL").upper()

if selected and selected != "Custom...":
    with st.spinner(f"Loading {selected}..."):
        hist, info, news = get_stock_data(selected, period="1y")
        
        if hist is not None and not hist.empty:
            df = calculate_indicators(hist)
            
            # Metrics
            price = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2] if len(hist) > 1 else price
            change = ((price / prev) - 1) * 100
            volume = hist['Volume'].iloc[-1]
            avg_vol = hist['Volume'].mean()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Price", f"${price:.2f}", f"{change:+.2f}%")
            m2.metric("Volume", f"{volume:,.0f}", f"Avg: {avg_vol:,.0f}")
            m3.metric("RSI (14)", f"{df['RSI_14'].iloc[-1]:.1f}" if 'RSI_14' in df.columns else "-")
            m4.metric("Trend", get_trend(df))
            
            # Key levels
            high_52 = hist['High'].max()
            low_52 = hist['Low'].min()
            st.caption(f"52-Week High: ${high_52:.2f} | 52-Week Low: ${low_52:.2f}")
            
            # Chart
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                vertical_spacing=0.03,
                                row_heights=[0.6, 0.2, 0.2],
                                subplot_titles=(f"{selected} Price", "RSI", "MACD"))
            
            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name="Price"
            ), row=1, col=1)
            
            # MAs
            if 'SMA_20' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="SMA 20", line=dict(color='orange')), row=1, col=1)
            if 'SMA_50' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name="SMA 50", line=dict(color='blue')), row=1, col=1)
            if 'SMA_200' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name="SMA 200", line=dict(color='purple')), row=1, col=1)
            
            # RSI
            if 'RSI_14' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='purple')), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            
            # MACD
            if 'MACD_12_26_9' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], name="MACD", line=dict(color='blue')), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], name="Signal", line=dict(color='orange')), row=3, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="Histogram"), row=3, col=1)
            
            fig.update_layout(height=800, xaxis_rangeslider_visible=False, showlegend=True)
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="RSI", row=2, col=1)
            fig.update_yaxes(title_text="MACD", row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Action for this stock
            st.subheader("Suggested Action")
            st.success(get_action_signal(df, info))
            
            # News
            st.subheader("Latest News")
            if news:
                for item in news[:6]:
                    title = item.get('title', 'No title')
                    link = item.get('link', '#')
                    publisher = item.get('publisher', '')
                    st.markdown(f"**[{title}]({link})**  \n*{publisher}*")
            else:
                st.info("No recent news available.")
            
            # Company info
            with st.expander("Company Info"):
                if info:
                    st.write(f"**Name:** {info.get('longName', selected)}")
                    st.write(f"**Sector:** {info.get('sector', 'N/A')}")
                    st.write(f"**Industry:** {info.get('industry', 'N/A')}")
                    st.write(f"**Market Cap:** ${info.get('marketCap', 0):,.0f}" if info.get('marketCap') else "N/A")
                    st.write(f"**PE Ratio:** {info.get('trailingPE', 'N/A')}")
else:
    st.info("Select or enter a ticker to analyze.")

st.markdown("---")
st.caption("⚠️ For personal research and education only. Not financial advice. Data is delayed.")
