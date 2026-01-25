import pandas as pd
import yfinance as yf


def download_stock_data(tickers: list[str], start_date: str) -> pd.DataFrame:
    """
    Download historical stock data with a list of tickers from the specified start date to the current date.

    Parameters:
    - tickers (list[str]): A list of stock ticker symbols.
    - start_date (str): The start date for fetching historical data in 'YYYY-MM-DD' format.

    Returns:
    - pd.DataFrame: A pandas DataFrame containing the historical stock data, organized by ticker.
    """
    data = yf.download(tickers, start=start_date, progress=False, group_by="ticker")
    return data

def download_stock_info(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch stock information for a list of tickers.

    Parameters:
    - tickers (list[str]): A list of stock ticker symbols.

    Returns:
    - dict[str, dict]: A dictionary where each key is a ticker symbol and the value is a dictionary of stock information.
    """
    stocks_info = {}
    for ticker in tickers:
        info = yf.Ticker(ticker).info
        if not info:
            print(f"Warning: No information found for ticker {ticker}.")
            continue
        stocks_info[ticker] = info

    return stocks_info


def get_daily_value_of_holdings(
    historical_data: pd.DataFrame,
    date: str,
    holding_stock: dict[str, int],
    last_known_value: float,
) -> float:
    """
    Calculate the total value of stock holdings on a specific date using historical data. If data for the specified date
    is incomplete, return the last known value.

    Parameters:
    - historical_data (pd.DataFrame): A DataFrame containing historical stock data, indexed by date and with columns including 'Close'.
    - date (str): The date for which to calculate the holdings' value, in 'YYYY-MM-DD' format.
    - holding_stock (dict[str, int]): A dictionary mapping stock symbols (str) to the number of shares held (int).
    - last_known_value (float): The fallback value to use if data for the specified date is unavailable.

    Returns:
    - float: The total value of the stock holdings on the specified date or the last known value if unavailable.

    Note:
    - The number of holding_stock in First Trade might be not integer, but we just use integer for simplify.
    """
    total_value = 0.0
    for symbol, quantity in holding_stock.items():
        try:
            if symbol in historical_data and date in historical_data[symbol].index:
                stock_data = historical_data[symbol].loc[date]
                closing_price = stock_data["Close"]
                total_value += closing_price * quantity
            else:
                total_value = last_known_value
                break  # Use last known value if data for this date is not available
        except Exception as e:
            print(f"Error processing data for {symbol} on {date}: {e}")
            total_value = last_known_value
            break  # Use last known value on error

    return total_value if total_value > 0 else last_known_value
