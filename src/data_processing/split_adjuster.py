"""Stock split adjustment utilities for historical date calculations."""

from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import yfinance as yf


def get_stock_splits(ticker: str) -> List[Tuple[str, float]]:
    """
    Get all stock splits for a ticker.

    Parameters:
    - ticker (str): Stock ticker symbol.

    Returns:
    - List[Tuple[str, float]]: List of (date, split_ratio) tuples.
    """
    try:
        t = yf.Ticker(ticker)
        splits = t.splits
        if splits.empty:
            return []

        result = []
        for date, ratio in splits.items():
            result.append((date.strftime("%Y-%m-%d"), float(ratio)))
        return result
    except Exception:
        return []


def get_split_adjustment_for_date(
    ticker: str,
    calc_date: str,
    first_purchase_date: str,
    splits_cache: Dict[str, List[Tuple[str, float]]] = None
) -> float:
    """
    Get the split adjustment ratio for a specific calculation date.

    Only applies adjustments for splits that occurred AFTER the calculation date
    but AFTER the first purchase date.

    Parameters:
    - ticker (str): Stock ticker symbol.
    - calc_date (str): The date we're calculating portfolio value for.
    - first_purchase_date (str): When the stock was first purchased.
    - splits_cache (Dict): Optional cache of splits data.

    Returns:
    - float: Split adjustment ratio (1.0 if no adjustment needed).
    """
    if splits_cache and ticker in splits_cache:
        splits = splits_cache[ticker]
    else:
        splits = get_stock_splits(ticker)

    if not splits:
        return 1.0

    calc_dt = datetime.strptime(calc_date, "%Y-%m-%d")
    purchase_dt = datetime.strptime(first_purchase_date, "%Y-%m-%d")

    ratio = 1.0
    for split_date, split_ratio in splits:
        split_dt = datetime.strptime(split_date, "%Y-%m-%d")
        # Apply adjustment if split happened AFTER calc_date AND AFTER purchase
        if split_dt > calc_dt and split_dt > purchase_dt:
            ratio *= split_ratio

    return ratio


def build_splits_cache(tickers: List[str]) -> Dict[str, List[Tuple[str, float]]]:
    """
    Build a cache of split data for all tickers.

    Parameters:
    - tickers (List[str]): List of stock ticker symbols.

    Returns:
    - Dict[str, List[Tuple[str, float]]]: Mapping of ticker to splits list.
    """
    cache = {}
    for ticker in tickers:
        if ticker:
            splits = get_stock_splits(ticker)
            if splits:
                cache[ticker] = splits
    return cache


def get_first_purchase_dates(transactions: pd.DataFrame) -> Dict[str, str]:
    """
    Get the first purchase date for each stock from transactions.

    Parameters:
    - transactions (pd.DataFrame): Transaction data.

    Returns:
    - Dict[str, str]: Mapping of ticker to first purchase date.
    """
    first_dates = {}
    for _, row in transactions.iterrows():
        symbol = str(row['Symbol']).strip()
        if symbol and row['Action'] == 'BUY':
            if symbol not in first_dates:
                first_dates[symbol] = row['TradeDate']
    return first_dates
