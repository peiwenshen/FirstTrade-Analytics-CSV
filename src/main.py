import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd

from utils import (
    plot_portfolios,
    calculate_daily_returns,
    calculate_sharpe_ratio,
    build_ticker_mapping,
)
from data_processing.csv_merger import merge_csvs
from data_processing.data_cleaner import (
    get_need_stock_lists,
    get_daily_cash_and_stocks,
    get_daily_cash_and_chosen_index,
    get_daily_cash_without_investment,
    get_portfolio_daily_values,
)
from data_processing.data_downloader import download_stock_data


# Configuration
RISK_FREE_RATE_ANNUAL = 0.04386
OPENFIGI_API_KEY = "65baa7f4-4e98-496d-bcd8-70cb1cab9d8d"


def load_and_prepare_transactions(
    file_paths: List[str], api_key: str
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Load, merge, and prepare transaction data from CSV files.

    Parameters:
    - file_paths (List[str]): List of paths to CSV files.
    - api_key (str): OpenFIGI API key for ticker mapping.

    Returns:
    - Tuple[pd.DataFrame, Dict[str, str]]: Prepared transactions and ticker mapping.
    """
    transactions = merge_csvs(file_paths)

    unique_tickers = transactions['Symbol'].unique().tolist()

    print("\nMapping outdated tickers using OpenFIGI...")
    ticker_mapping = build_ticker_mapping(unique_tickers, api_key=api_key)
    transactions['Symbol'] = transactions['Symbol'].replace(ticker_mapping)

    print("\nTicker mapping applied:")
    print(transactions['Symbol'].unique())

    return transactions, ticker_mapping


def analyze_portfolio(
    transactions: pd.DataFrame,
    historical_data: pd.DataFrame,
    compare_indices: List[str],
    start_date: str,
    end_date: str,
) -> Tuple[List[Dict[str, float]], List[str]]:
    """
    Run portfolio analysis calculations.

    Parameters:
    - transactions (pd.DataFrame): Transaction data.
    - historical_data (pd.DataFrame): Historical stock price data.
    - compare_indices (List[str]): List of indices to compare against.
    - start_date (str): Start date for analysis.
    - end_date (str): End date for analysis.

    Returns:
    - Tuple[List[Dict[str, float]], List[str]]: Portfolio daily values and labels.
    """
    portfolios_daily_values = []
    labels = []

    # Personal portfolio
    daily_values = get_daily_cash_and_stocks(transactions)
    portfolio_daily_values = get_portfolio_daily_values(
        daily_values, start_date, end_date, historical_data
    )
    portfolios_daily_values.append(portfolio_daily_values)
    labels.append("My Portfolio")

    # Index comparisons
    for index in compare_indices:
        daily_values_index = get_daily_cash_and_chosen_index(
            transactions, historical_data, index
        )
        portfolio_daily_values_index = get_portfolio_daily_values(
            daily_values_index, start_date, end_date, historical_data
        )
        portfolios_daily_values.append(portfolio_daily_values_index)
        labels.append(f"{index} Index")

    # Cash-only strategy
    daily_values_cash = get_daily_cash_without_investment(transactions)
    portfolio_daily_values_cash = get_portfolio_daily_values(
        daily_values_cash, start_date, end_date, historical_data
    )
    portfolios_daily_values.append(portfolio_daily_values_cash)
    labels.append("Cash Only")

    return portfolios_daily_values, labels


def display_results(
    portfolios_daily_values: List[Dict[str, float]],
    labels: List[str],
    risk_free_rate: float,
    sample_day: int = 30,
) -> None:
    """
    Display portfolio analysis results.

    Parameters:
    - portfolios_daily_values (List[Dict[str, float]]): List of portfolio daily values.
    - labels (List[str]): Labels for each portfolio.
    - risk_free_rate (float): Annual risk-free rate for Sharpe ratio calculation.
    - sample_day (int): Sampling interval for plot.
    """
    plot_portfolios(portfolios_daily_values, sample_day=sample_day, labels=labels)

    cash_only_final_value = list(portfolios_daily_values[-1].values())[-1]

    print("\nFinal Value and Percentage Earnings Compared to Cash Only:")
    for label, portfolio_daily_values in zip(labels, portfolios_daily_values):
        portfolio_final_value = list(portfolio_daily_values.values())[-1]
        percentage_earning = (
            (portfolio_final_value - cash_only_final_value) / cash_only_final_value
        ) * 100
        daily_returns = calculate_daily_returns(portfolio_daily_values)
        sharpe_ratio = calculate_sharpe_ratio(daily_returns, risk_free_rate)
        if label == "Cash Only":
            sharpe_ratio = 0  # Sharpe ratio for cash is not applicable
        print(
            f"{label}: Final Value = {portfolio_final_value:.2f}, "
            f"Percentage Earning = {percentage_earning:.2f}%, "
            f"Sharpe Ratio: {sharpe_ratio:.2f}."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Compare portfolio performance against chosen indices."
    )
    parser.add_argument(
        "file_paths",
        type=str,
        nargs="+",
        help="CSV file path(s) containing transaction data. Supports multiple files.",
    )
    parser.add_argument(
        "--indices",
        type=str,
        nargs="+",
        default=["SPY"],
        help="List of indices to compare (e.g., --indices SPY QQQ). Default: SPY",
    )

    args = parser.parse_args()

    file_paths = args.file_paths
    compare_indices = args.indices

    # Load and prepare transactions
    transactions, _ = load_and_prepare_transactions(file_paths, OPENFIGI_API_KEY)

    # Build ticker list
    tickers = list(set(get_need_stock_lists(transactions) + compare_indices))

    # Determine date range
    start_date = transactions["TradeDate"].min()
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\nAnalysis period: {start_date} to {end_date}")

    # Download stock data
    historical_data = download_stock_data(tickers, start_date)

    # Analyze portfolio
    portfolios_daily_values, labels = analyze_portfolio(
        transactions, historical_data, compare_indices, start_date, end_date
    )

    # Display results
    display_results(portfolios_daily_values, labels, RISK_FREE_RATE_ANNUAL)


if __name__ == "__main__":
    main()
