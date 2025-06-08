import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import Dense, LSTM

st.set_page_config(layout="wide")
st.title("📈 BTC & Nasdaq 100 Swing Trading Agent")

# ---------------------------- SETTINGS ----------------------------
tickers = {
    "Bitcoin (BTC-USD)": "BTC-USD",
    "Nasdaq 100 (^NDX)": "^NDX"
}
selected = st.selectbox("Izaberi Asset:", list(tickers.keys()))
ticker = tickers[selected]
initial_capital = 10000

# ---------------------------- DATA FETCH ----------------------------
try:
    data = yf.download(ticker, period="180d", interval="1d")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty or 'Close' not in data.columns:
        st.error("⚠️ Nema dostupnih podataka.")
        st.stop()

    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['RSI'] = 100 - (100 / (1 + data['Close'].pct_change().rolling(window=14).mean() / data['Close'].pct_change().rolling(window=14).std()))
    data['EMA12'] = data['Close'].ewm(span=12).mean()
    data['EMA26'] = data['Close'].ewm(span=26).mean()
    data['MACD'] = data['EMA12'] - data['EMA26']
    data['Signal'] = data['MACD'].ewm(span=9).mean()

except Exception as e:
    st.error(f"❌ Greška pri učitavanju podataka: {e}")
    st.stop()

# ---------------------------- BACKTESTING STRATEGY ----------------------------
def backtest_strategy(df, capital):
    position = 0
    buy_price = 0
    balance = capital
    signals = []
    buy_signals = []
    sell_signals = []

    for i in range(1, len(df)):
        # Buy condition: RSI < 30 and MACD crossover
        if df['RSI'][i] < 30 and df['MACD'][i] > df['Signal'][i] and df['MACD'][i-1] <= df['Signal'][i-1]:
            if position == 0:
                position = balance / df['Close'][i]
                buy_price = df['Close'][i]
                balance = 0
                buy_signals.append((df.index[i], df['Close'][i]))
                signals.append("BUY")
            else:
                signals.append("HOLD")
        # Sell condition: RSI > 70 and MACD crossunder
        elif df['RSI'][i] > 70 and df['MACD'][i] < df['Signal'][i] and df['MACD'][i-1] >= df['Signal'][i-1]:
            if position > 0:
                balance = position * df['Close'][i]
                position = 0
                sell_signals.append((df.index[i], df['Close'][i]))
                signals.append("SELL")
            else:
                signals.append("HOLD")
        else:
            signals.append("HOLD")

    final_balance = balance + position * df['Close'].iloc[-1]
    return final_balance, signals, buy_signals, sell_signals

result, signals, buy_signals, sell_signals = backtest_strategy(data.copy(), initial_capital)

# ---------------------------- VISUALIZATION ----------------------------
st.subheader("📊 Cene i SMA20")
st.line_chart(data[['Close', 'SMA20']])

st.subheader("📉 RSI")
st.line_chart(data[['RSI']])

st.subheader("📉 MACD i Signal Line")
st.line_chart(data[['MACD', 'Signal']])

# Altair chart sa signalima
st.subheader("🧠 Backtest Signali")
buy_df = pd.DataFrame(buy_signals, columns=["Date", "Price"])
sell_df = pd.DataFrame(sell_signals, columns=["Date", "Price"])
data_reset = data.reset_index()

base = alt.Chart(data_reset).mark_line().encode(
    x='Date:T',
    y='Close:Q'
).properties(title=f"{selected} Cena sa BUY/SELL signalima")

buy_points = alt.Chart(buy_df).mark_point(color='green', shape='triangle-up', size=100).encode(
    x='Date:T',
    y='Price:Q'
)

sell_points = alt.Chart(sell_df).mark_point(color='red', shape='triangle-down', size=100).encode(
    x='Date:T',
    y='Price:Q'
)

st.altair_chart(base + buy_points + sell_points, use_container_width=True)

# ---------------------------- RESULTS ----------------------------
st.subheader("📈 Finalni Balans")
st.metric("💰 Balans na kraju", f"${result:.2f}")
returns = (result - initial_capital) / initial_capital * 100
st.metric("📊 Ukupan Povraćaj", f"{returns:.2f}%")
st.metric("🔁 Ukupno Trgovanja", f"{len(buy_signals) + len(sell_signals)}")


