import time
from datetime import datetime, timedelta

import pandas as pd
from openbb import obb

from src.market_data import enrich_companies, enrich_with_sec
from src.utils import load_parquet_cache, save_parquet_cache


def companies_with_letter(df, letter):
    """Return companies whose ticker contains a given letter."""

    return (
        df[
            df["Symbol"].str.contains(
                letter.upper(),
                regex=False,
                na=False,
            )
        ]
        .sort_values("Symbol")
        .reset_index(drop=True)
    )


def ticker_letter_counts(df):
    """Count companies containing each ticker letter.

    Each company counts only once per letter.
    """

    letters = (
        df["Symbol"]
        .apply(lambda x: set(x))
        .explode()
        .value_counts()
        .sort_values()
        .rename_axis("letter")
        .reset_index(name="companies")
    )

    return letters


def least_common_letters(df, n=10):
    return ticker_letter_counts(df).head(n)


def compute_market_cap_weights(df):
    """Compute market-cap weights."""

    df = df.copy()

    total_market_cap = df["MarketCap"].sum()

    df["Weight"] = df["MarketCap"] / total_market_cap

    return df.sort_values(
        "Weight",
        ascending=False,
    ).reset_index(drop=True)


def classify_market_cap(market_cap):
    """Classify a company by market capitalization."""

    if pd.isna(market_cap):
        return None

    if market_cap >= 200e9:
        return "Mega Cap"

    if market_cap >= 10e9:
        return "Large Cap"

    if market_cap >= 2e9:
        return "Mid Cap"

    if market_cap >= 300e6:
        return "Small Cap"

    if market_cap >= 50e6:
        return "Micro Cap"

    return "Nano Cap"


def build_j_index_constituents(j_index):
    companies = enrich_companies(j_index)

    companies = compute_market_cap_weights(companies)

    companies["Size"] = companies["MarketCap"].apply(classify_market_cap)

    companies = enrich_with_sec(companies)

    columns = [
        "Symbol",
        "Company",
        "Sector",
        "MarketCap",
        "Weight",
        "Size",
        "Currency",
        "Country",
        "SIC",
        "SIC_Description",
    ]

    return (
        companies[columns]
        .sort_values(
            "Weight",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def download_index_prices(
    constituents,
    lookback_days=365,
    cache_path="data/j_index_prices.parquet",
):
    """Download adjusted close prices for all index constituents.

    Uses parquet cache to avoid re-downloading on every run.
    """

    cached = load_parquet_cache(cache_path)

    tickers = constituents["Symbol"].tolist()

    if not cached.empty:
        cached_tickers = set(cached.columns)
        missing = [t for t in tickers if t not in cached_tickers]
    else:
        missing = tickers

    if not missing:
        return cached

    start_date = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    new_data = []

    counter = 0

    for ticker in missing:
        try:
            prices = obb.equity.price.historical(
                ticker,
                provider="yfinance",
                start_date=start_date,
            ).to_df()

            if not prices.empty:
                close = prices["close"].rename(ticker)
                new_data.append(close)
                print(f"{ticker}: {len(prices)} days")
            else:
                print(f"{ticker}: no data")

        except Exception as e:
            print(f"{ticker}: {e}")

        counter += 1

        if counter % 5 == 0:
            time.sleep(1)

    if new_data:
        new_prices = pd.concat(new_data, axis=1)

        if not cached.empty:
            new_prices = pd.concat([cached, new_prices], axis=1)

        new_prices = new_prices.loc[:, ~new_prices.columns.duplicated()]

        save_parquet_cache(new_prices, cache_path)

        return new_prices

    return cached


def calculate_j_index(
    constituents,
    lookback_days=365,
    start_level=1000,
):
    """Calculate the J Index time series.

    1. Download adjusted close prices for all constituents.
    2. Calculate daily simple returns.
    3. Multiply by fixed market-cap weights (renormalized daily for available tickers).
    4. Chain into an index starting at start_level.
    """

    prices = download_index_prices(constituents, lookback_days)

    returns = prices.pct_change()

    weights = constituents.set_index("Symbol")["Weight"]

    aligned_weights = weights.reindex(returns.columns)

    weighted_returns = pd.DataFrame(
        index=returns.index,
        columns=returns.columns,
        dtype=float,
    )

    for date in returns.index:
        day_returns = returns.loc[date]

        available = day_returns.notna()

        if available.any():
            day_weights = aligned_weights[available]

            day_weights = day_weights / day_weights.sum()

            weighted_returns.loc[date] = day_returns * day_weights

    portfolio_return = weighted_returns.sum(axis=1)

    index_level = start_level * (1 + portfolio_return).cumprod()

    result = pd.DataFrame(
        {
            "Date": index_level.index,
            "Index": index_level.values,
            "Daily_Return": portfolio_return.values,
        }
    )

    return result
