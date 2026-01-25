import copy
from typing import Any, Dict

import pandas as pd
from data_processing.data_downloader import get_daily_value_of_holdings


def get_need_stock_lists(transactions: pd.DataFrame) -> list[str]:
    """
    Extract a list of unique stock ticker symbols from transaction records.

    Parameters:
    - transactions (pd.DataFrame): A DataFrame containing transaction records, with a 'Symbol' column for stock symbols.

    Returns:
    - list[str]: A list of unique stock ticker symbols present in the transactions.
    """
    tickers = transactions["Symbol"].unique().tolist()
    # Remove any whitespace and filter out empty strings
    tickers = [symbol.strip() for symbol in tickers if symbol.strip()]
    return tickers


def get_daily_cash_and_stocks(transactions: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """
    Calculate daily cash and stock holdings from transaction records.

    Parameters:
    - transactions (pd.DataFrame): DataFrame containing transaction records with columns
      'Symbol', 'Action', 'Amount', 'Quantity', and 'TradeDate'.

    Returns:
    - dict[str, dict[str, Any]]: A dictionary with dates as keys and dictionaries as values,
      where each nested dictionary includes 'current_value' and 'holding_stock' for the day.
    """
    original_value = 0
    current_value = 0
    holding_stock: dict[str, int] = {}
    daily_values: dict[str, dict[str, Any]] = {}

    for _, row in transactions.iterrows():
        symbol = row.Symbol.strip()
        if symbol:
            if row.Action == "BUY" or row.Action == "SELL":
                current_value += row.Amount
                holding_stock[symbol] = holding_stock.get(symbol, 0) + row.Quantity
            elif row.Action in ["Dividend", "Other"]:
                if row.Action == "Other" and not (
                    "TFR TO TYPE" in row.Description
                    or "TFR FROM TYPE" in row.Description
                ):
                    holding_stock[symbol] = holding_stock.get(symbol, 0) + row.Quantity
            else:
                print(f"Format error in row: {row}")
                assert False, "Transaction format error"

        else:
            if row.Action != "Interest":
                original_value += row.Amount
            current_value += row.Amount

        daily_holdings = copy.deepcopy(holding_stock)
        daily_values[row.TradeDate] = {
            "current_value": current_value,
            "holding_stock": daily_holdings,
        }

    return daily_values


def get_daily_cash_and_chosen_index(
    transactions: pd.DataFrame, historical_data: pd.DataFrame, index_ticker: str
) -> dict[str, dict[str, Any]]:
    """
    Calculate daily cash values and holdings of a chosen index from transaction records.

    Parameters:
    - transactions (pd.DataFrame): DataFrame of transactions.
    - historical_data (pd.DataFrame): DataFrame with historical data for the index.
    - index_ticker (str): Ticker symbol of the index.

    Returns:
    - dict[str, dict[str, Any]]: Daily cash values and stock holdings for the index.
    """
    current_value = 0
    holding_stock: dict[str, int] = {}
    daily_values: dict[str, dict[str, Any]] = {}

    for _, row in transactions.iterrows():
        if not row.Symbol.strip():
            if row.Action != "Interest" and (
                "Funds Received" in row.Description
                or "ACH DEPOSIT" in row.Description
                or "ACH DISBURSEMENT" in row.Description
            ):
                current_value += row.Amount
                stock_data = historical_data[index_ticker].loc[row.TradeDate]
                closing_price = stock_data["Close"]
                buy_amount = int(current_value // closing_price)
                holding_stock[index_ticker] = (
                    holding_stock.get(index_ticker, 0) + buy_amount
                )
                current_value -= buy_amount * closing_price

        daily_holdings = copy.deepcopy(holding_stock)
        daily_values[row.TradeDate] = {
            "current_value": current_value,
            "holding_stock": daily_holdings,
        }

    return daily_values


def get_daily_cash_without_investment(
    transactions: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """
    Calculate daily cash values without investing in stocks or indices from transaction records.

    Parameters:
    - transactions (pd.DataFrame): DataFrame of transactions.

    Returns:
    - dict[str, dict[str, Any]]: Daily cash values without stock holdings.
    """
    current_value = 0
    daily_values: dict[str, dict[str, Any]] = {}

    for _, row in transactions.iterrows():
        # Adjust current value based on transaction amount without buying stocks
        if not row.Symbol.strip():
            # Consider all cash movements except 'Interest' as cash adjustments
            if row.Action != "Interest":
                current_value += row.Amount

        # Record daily cash value
        daily_values[row.TradeDate] = {
            "current_value": current_value,
            "holding_stock": {},  # No stocks held, empty dict for consistency
        }

    return daily_values


def get_portfolio_daily_values(
    daily_values: Dict[str, Dict[str, Dict[str, float]]],
    start_date: str,
    end_date: str,
    historical_data: pd.DataFrame,
    splits_cache: Dict = None,
    first_purchase_dates: Dict[str, str] = None,
) -> Dict[str, float]:
    """
    Calculate the portfolio's daily values over a specified date range based on transactions and historical stock data.

    Parameters:
    - daily_values (Dict[str, Dict[str, Dict[str, float]]]): A nested dictionary containing each date's holding information.
      Each key is a date string 'YYYY-MM-DD', mapping to a dictionary that contains 'holding_stock', which itself maps stock symbols
      to the quantity held for that day.
    - start_date (str): The start date of the period for calculating daily portfolio values.
    - end_date (str): The end date of the period.
    - historical_data (pd.DataFrame): The DataFrame containing historical stock data, indexed by date.
    - splits_cache (Dict): Optional cache of stock splits data.
    - first_purchase_dates (Dict[str, str]): Optional mapping of ticker to first purchase date.

    Returns:
    - Dict[str, float]: A dictionary mapping each date within the specified range to the total value of the portfolio for that date.
    """
    from data_processing.split_adjuster import get_split_adjustment_for_date

    portfolio_daily_values: Dict[str, float] = {}
    date_range = pd.date_range(start=start_date, end=end_date)
    last_known_value = 0.0
    last_holdings: Dict[str, int] = {}
    last_cash = 0

    for single_date in date_range:
        date_str = single_date.strftime("%Y-%m-%d")
        day_data = daily_values.get(date_str, {})

        current_holdings = day_data.get("holding_stock", last_holdings)

        # Apply date-aware split adjustments if splits_cache provided
        if splits_cache and first_purchase_dates:
            adjusted_holdings = {}
            for ticker, quantity in current_holdings.items():
                if ticker and ticker in splits_cache:
                    purchase_date = first_purchase_dates.get(ticker, start_date)
                    ratio = get_split_adjustment_for_date(
                        ticker, date_str, purchase_date, splits_cache
                    )
                    adjusted_holdings[ticker] = quantity * ratio
                else:
                    adjusted_holdings[ticker] = quantity
            current_holdings = adjusted_holdings

        last_known_value = get_daily_value_of_holdings(
            historical_data, date_str, current_holdings, last_known_value
        )
        portfolio_daily_values[date_str] = last_known_value + day_data.get(
            "current_value", last_cash
        )

        # Update the last holdings for the next iteration
        last_holdings = day_data.get("holding_stock", last_holdings)
        last_cash = day_data.get("current_value", last_cash)
    return portfolio_daily_values
