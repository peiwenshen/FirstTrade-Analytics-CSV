"""CSV loading and merging utilities for FirstTrade transaction data."""

from typing import List

import pandas as pd


def load_csv(file_path: str) -> pd.DataFrame:
    """
    Load a single FirstTrade CSV file.

    Parameters:
    - file_path (str): Path to the CSV file.

    Returns:
    - pd.DataFrame: The loaded transaction data.
    """
    df = pd.read_csv(file_path)
    df['Symbol'] = df['Symbol'].astype(str).str.strip().str.upper()
    return df


def deduplicate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate transactions from a DataFrame.

    Transactions are considered duplicates if they have the same values for:
    Symbol, TradeDate, Amount, Action, Quantity, and CUSIP.

    Parameters:
    - df (pd.DataFrame): DataFrame containing transaction records.

    Returns:
    - pd.DataFrame: DataFrame with duplicates removed.
    """
    dedup_columns = ['Symbol', 'TradeDate', 'Amount', 'Action', 'Quantity', 'CUSIP']
    original_count = len(df)
    df_deduped = df.drop_duplicates(subset=dedup_columns, keep='first')
    removed_count = original_count - len(df_deduped)
    if removed_count > 0:
        print(f"  Removed {removed_count} duplicate transactions")
    return df_deduped


def merge_csvs(file_paths: List[str]) -> pd.DataFrame:
    """
    Merge multiple FirstTrade CSV files into a single DataFrame.

    Handles deduplication and sorts transactions chronologically.

    Parameters:
    - file_paths (List[str]): List of paths to CSV files.

    Returns:
    - pd.DataFrame: Merged and deduplicated transaction data, sorted by TradeDate.
    """
    if not file_paths:
        raise ValueError("At least one CSV file path is required")

    print(f"Loading {len(file_paths)} CSV file(s)...")

    dfs = []
    for path in file_paths:
        print(f"  Loading: {path}")
        df = load_csv(path)
        print(f"    {len(df)} transactions")
        dfs.append(df)

    if len(dfs) == 1:
        merged = dfs[0]
    else:
        merged = pd.concat(dfs, ignore_index=True)
        print(f"  Total before deduplication: {len(merged)} transactions")
        merged = deduplicate_transactions(merged)

    merged = merged.sort_values(by='TradeDate', ascending=True).reset_index(drop=True)
    print(f"  Final transaction count: {len(merged)}")

    return merged
