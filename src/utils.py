import time
import json
from pathlib import Path
from typing import Dict, List

import requests
import matplotlib.pyplot as plt
import numpy as np


def plot_portfolios(
    portfolios_daily_values: List[Dict[str, float]], sample_day: int, labels: List[str]
) -> None:
    plt.figure(figsize=(10, 6))
    colors = ["b", "g", "r", "c", "m", "y", "k"]

    for i, portfolio_values in enumerate(portfolios_daily_values):
        dates = list(portfolio_values.keys())
        values = list(portfolio_values.values())

        sampled_dates = [date for j, date in enumerate(dates) if j % sample_day == 0]
        sampled_values = [
            value for j, value in enumerate(values) if j % sample_day == 0
        ]

        label = labels[i] if i < len(labels) else f"Portfolio {i+1}"

        plt.plot(
            sampled_dates,
            sampled_values,
            marker=".",
            linestyle="-",
            color=colors[i % len(colors)],
            label=label,
        )

    plt.title("Portfolio Values Over Time")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def calculate_daily_returns(portfolio_values: Dict[str, float]) -> List[float]:
    sorted_dates = sorted(portfolio_values.keys())
    returns = []
    for i in range(1, len(sorted_dates)):
        prev_value = portfolio_values[sorted_dates[i - 1]]
        current_value = portfolio_values[sorted_dates[i]]
        daily_return = (current_value - prev_value) / prev_value if prev_value else 0
        returns.append(daily_return)
    return returns


def calculate_sharpe_ratio(
    daily_returns: List[float], risk_free_rate_annual: float
) -> float:
    # Filter out zero returns (e.g., market closed days)
    filtered_returns = [r for r in daily_returns if r != 0.0]

    if not filtered_returns:
        return 0.0  # Avoid division by zero if all returns were zero

    risk_free_rate_daily = (1 + risk_free_rate_annual) ** (1 / 252) - 1
    excess_returns = np.array(filtered_returns) - risk_free_rate_daily
    avg_excess_return = np.mean(excess_returns)
    std_dev_excess_return = np.std(excess_returns)

    return (
        avg_excess_return / std_dev_excess_return * np.sqrt(252)
        if std_dev_excess_return != 0
        else 0.0
    )


def is_valid_ticker(ticker: str) -> bool:
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        return not hist.empty
    except Exception:
        return False


def get_company_name(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ""
    except Exception:
        return ""


def build_ticker_mapping(
    tickers: List[str],
    api_key: str,
    cache_file: str = "ticker_mapping_cache.json",
) -> Dict[str, str]:
    OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
    headers = {
        "Content-Type": "application/json",
        "X-OPENFIGI-APIKEY": api_key,
    }

    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    to_query = [t for t in tickers if t not in cache]
    print(f"🔍 Querying {len(to_query)} tickers from OpenFIGI...")

    for i, ticker in enumerate(to_query):
        print(f"[{i+1}/{len(to_query)}] Processing {ticker}...")

        body = [{
            "idType": "TICKER",
            "idValue": ticker,
            "exchCode": "US"
        }]

        try:
            response = requests.post(OPENFIGI_URL, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()

            if result and isinstance(result[0].get("data"), list) and result[0]["data"]:
                data = result[0]["data"][0]
                mapped_ticker = data.get("ticker", ticker)
                cache[ticker] = mapped_ticker
                print(f"   ✅ {ticker} → {mapped_ticker}")
            else:
                cache[ticker] = ticker
                print(f"   ⚠️ No mapping found for {ticker}")
        except Exception as e:
            print(f"   [ERROR] Failed to map {ticker}: {e}")
            cache[ticker] = ticker

        time.sleep(1)

    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)

    print("✅ Final mapping:")
    for old, new in cache.items():
        if old != new:
            print(f"   {old} → {new}")

    return cache

def calculate_portfolio_beta():
    pass