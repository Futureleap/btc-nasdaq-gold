import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📈 BTC & Nasdaq 100 Swing Trading Agent")

# Ticker izbor
tickers = {
    "Bitcoin (BTC-USD)": "BTC-USD",
    "Nasdaq 100 (^NDX)": "^NDX"
}

selected = st.selectbox("Izaberi Asset:", list(tickers.keys()))
ticker = tickers[selected]

# Učitavanje podataka
try:
    data = yf.download(ticker, period="180d", interval="1d")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if not data.empty and 'Close' in data.columns:
        # Tehnički indikatori
        data['SMA20'] = data['Close'].rolling(window=20).mean()
        data['Bollinger_High'] = data['SMA20'] + 2 * data['Close'].rolling(window=20).std()
        data['Bollinger_Low'] = data['SMA20'] - 2 * data['Close'].rolling(window=20).std()
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['Signal'] = macd.macd_signal()

        st.subheader("📊 Cene i SMA20")
        st.line_chart(data[['Close', 'SMA20']])

        st.subheader("📉 RSI")
        st.line_chart(data[['RSI']])

        st.subheader("📉 MACD i Signal Line")
        st.line_chart(data[['MACD', 'Signal']])

        # === BACKTEST ===
        def backtest_strategy(df, initial_capital=10000):
            df = df.dropna().copy()
            position = 0
            cash = initial_capital
            holdings = 0
            trades = 0

            for i in range(1, len(df)):
                # Kupovni signal: RSI < 30 i MACD presek naviše
                if df['RSI'].iloc[i] < 30 and df['MACD'].iloc[i] > df['Signal'].iloc[i] and position == 0:
                    holdings = cash / df['Close'].iloc[i]
                    cash = 0
                    position = 1
                    trades += 1

                # Prodajni signal: RSI > 70 i MACD presek naniže
                elif df['RSI'].iloc[i] > 70 and df['MACD'].iloc[i] < df['Signal'].iloc[i] and position == 1:
                    cash = holdings * df['Close'].iloc[i]
                    holdings = 0
                    position = 0
                    trades += 1

            if position == 1:
                cash = holdings * df['Close'].iloc[-1]

            final_balance = cash
            return_percent = (final_balance - initial_capital) / initial_capital * 100

            return {
                "final_balance": final_balance,
                "return_percent": return_percent,
                "total_trades": trades
            }

        st.subheader("🧠 Backtest Rezultati")
        initial_capital = 10000
        result = backtest_strategy(data.copy(), initial_capital)
        st.metric("📈 Finalni Balans", f"${result['final_balance']:.2f}")
        st.metric("📊 Ukupan Povraćaj", f"{result['return_percent']:.2f}%")
        st.metric("🔁 Ukupno Trgovanja", f"{result['total_trades']}")

    else:
        st.error("⚠️ Podaci nisu dostupni za izabrani asset. Pokušaj ponovo kasnije.")
except Exception as e:
    st.error(f"❌ Greška pri učitavanju podataka: {e}")
