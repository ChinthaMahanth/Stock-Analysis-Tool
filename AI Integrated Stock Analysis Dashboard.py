import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ollama
import tempfile
import base64
from plotly.subplots import make_subplots
import os

# Basic Layout
st.set_page_config(layout="wide")
st.title("Analysis Dashboard")
st.sidebar.header("Stock Configurations")

# Stock Ticker and Range
ticker = st.sidebar.text_input("Enter Stock Ticker: ")
startDate = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
endDate = st.sidebar.date_input("End Date", value=pd.to_datetime("2024-12-14"))

if st.sidebar.button("Gather Data"):
    st.session_state["stockData"] = yf.download(ticker, start=startDate, end=endDate)
    st.success("Stock Data Loaded Successfully!")

if "stockData" in st.session_state:
    data = st.session_state["stockData"]
    data.columns = data.columns = ["Close", "High", "Low", "Open", "Volume"]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
        subplot_titles=("Candlestick Chart", "Relative Strength Index (RSI)")
    )
    
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Candlestick"
        ),
        row=1, col=1
    )

    st.sidebar.subheader("Technical Indicators")
    indicators = st.sidebar.multiselect("Select Indicators: ", ["20-Day SMA", "20-Day EMA", "RSI", "20-Day Bollinger Bands"])

    def add_indicator(indicator):
        if indicator == "20-Day SMA":
            sma = data["Close"].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=data.index, y=sma, mode="lines", name="SMA (20)"), row=1, col=1)
        elif indicator == "20-Day EMA":
            ema = data["Close"].ewm(span=20).mean()
            fig.add_trace(go.Scatter(x=data.index, y=ema, mode="lines", name="EMA (20)"), row=1, col=1)
        elif indicator == "20-Day Bollinger Bands":
            sma = data["Close"].rolling(window=20).mean()
            std = data["Close"].rolling(window=20).std()
            bb_upper = sma + 2 *std
            bb_lower = sma - 2 * std
            fig.add_trace(go.Scatter(x=data.index, y=bb_upper, mode='lines', name="BB Upper"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=bb_lower, mode="lines", name="BB Lower"), row=1, col=1)
        elif indicator == "RSI":
            delta = data["Close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            fig.add_trace(go.Scatter(x=data.index, y=rsi, mode="lines", name="RSI"), row=2, col=1)
            

    for indicator in indicators:
        add_indicator(indicator)

    
    fig.update_layout(xaxis_rangeslider_visible=False, showlegend=True, height=800)
    st.plotly_chart(fig)

    st.subheader("AI-Powered Analysis")
    if st.button("Run Analysis"):
        with st.spinner("Analyzing the chart, please wait..."):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                fig.write_image(tmpfile.name)
                tmpfile_path = tmpfile.name

            with open(tmpfile_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            messages = [{
                "role": "user",
                "content": "You are a technical stock trader at a hedgefund. Use the indicators to give a buy/sell decision",
                "images": [image_data]
            }]
            response = ollama.chat(model="llama3.2-vision", messages=messages)

            st.write("Analysis Results:")
            st.write(["message"]["content"])

            os.remove(tmpfile_path)
