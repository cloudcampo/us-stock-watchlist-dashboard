# US Stock Watchlist Dashboard

Personal Streamlit dashboard for US stock analysis.

## Features
- Market overview (SPY, QQQ, DIA, IWM, VIX)
- Persistent watchlist (SQLite)
- Action list for all watchlist stocks
- Interactive charts with SMA, RSI, MACD
- Key levels and trend analysis
- Latest news
- Simple action suggestions

## Run Locally

1. Create virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run app.py
```

4. Open the URL shown (usually http://localhost:8501)

## Deploy to Streamlit Cloud (Free)
1. Push this folder to a public GitHub repo
2. Go to https://share.streamlit.io
3. Connect your repo and deploy `app.py`

## Notes
- Data from Yahoo Finance (delayed, unofficial API)
- Watchlist stored in `watchlist.db` (created automatically)
- For personal research only — not financial advice
