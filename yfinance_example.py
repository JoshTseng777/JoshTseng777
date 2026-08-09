"""Example: fetch recent stock price data using yfinance."""

import yfinance as yf

TICKER = "AAPL"


def main():
    ticker = yf.Ticker(TICKER)
    history = ticker.history(period="5d")
    print(f"Last 5 days of {TICKER} closing prices:")
    print(history["Close"])


if __name__ == "__main__":
    main()
