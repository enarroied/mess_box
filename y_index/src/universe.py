import json
import time

import pandas as pd

from src.utils import load_parquet_cache


def load_sec_companies(path):
    """Load SEC company_tickers.json."""

    with open(path, "r") as f:
        sec = json.load(f)

    df = pd.DataFrame.from_dict(sec, orient="index").rename(
        columns={
            "ticker": "Symbol",
            "title": "Company",
            "cik_str": "CIK",
        }
    )

    df["Symbol"] = df["Symbol"].str.upper()

    return df


def load_nasdaq(path):
    """Load nasdaqlisted.txt."""

    df = pd.read_csv(path, sep="|")

    df = df[df["Symbol"] != "File Creation Time"]

    df = df[
        (df["ETF"] == "N") & (df["NextShares"] == "N") & (df["Test Issue"] == "N")
    ]

    return df


def merge_company_universe(sec_df, nasdaq_df):
    """Keep only SEC-reporting companies that trade on Nasdaq."""

    return nasdaq_df.merge(
        sec_df,
        on="Symbol",
        how="inner",
    )


def remove_non_equity_securities(df):
    """Remove securities that are not common equity."""

    bad_patterns = [
        "warrant",
        "rights?",
        "unit",
        "preferred",
        "depositary",
        "note",
        "bond",
        "debenture",
    ]

    regex = "|".join(bad_patterns)

    mask = ~df["Security Name"].str.lower().str.contains(
        regex,
        regex=True,
        na=False,
    )

    return df[mask]


def remove_spacs(df):
    """Remove SPACs / blank check companies."""

    patterns = [
        " acquisition ",
        " acquisition$",
        " acquisition corp",
        " acquisition corporation",
        " acquisition holdings",
        " blank check",
    ]

    regex = "|".join(patterns)

    mask = ~df["Company"].str.lower().str.contains(
        regex,
        regex=True,
        na=False,
    )

    return df[mask]


def filter_tradable_companies(
    df,
    cache_path="data/history_cache.parquet",
    minimum_days=365,
):
    """Remove companies without sufficient Yahoo history.

    Uses parquet cache to avoid repeated downloads.
    """

    from src.market_data import check_ticker_history

    cache = load_parquet_cache(
        cache_path,
        columns=[
            "Symbol",
            "status",
            "first_date",
            "last_date",
            "days_history",
            "checked_at",
        ],
    )

    checked = set(cache["Symbol"])

    results = []

    counter = 0

    for ticker in df["Symbol"]:
        if ticker in checked:
            row = cache[cache["Symbol"] == ticker].iloc[0]
            results.append(row.to_dict())
            continue

        result = check_ticker_history(
            ticker,
            minimum_days,
        )

        print(ticker, result.get("status"))

        results.append(result)

        counter += 1

        if counter % 5 == 0:
            time.sleep(1)

    new_cache = pd.DataFrame(results)

    cache = pd.concat(
        [cache, new_cache],
        ignore_index=True,
    ).drop_duplicates(
        subset="Symbol",
        keep="last",
    )

    from src.utils import save_parquet_cache

    save_parquet_cache(cache, cache_path)

    valid = cache[cache["status"] == "ok"]["Symbol"]

    return df[df["Symbol"].isin(valid)].reset_index(drop=True)


def build_company_universe(
    sec_json_path,
    nasdaq_path,
    history_cache="data/history_cache.parquet",
):
    sec = load_sec_companies(sec_json_path)

    nasdaq = load_nasdaq(nasdaq_path)

    universe = merge_company_universe(sec, nasdaq)

    universe = remove_non_equity_securities(universe)

    universe = remove_spacs(universe)

    universe = filter_tradable_companies(
        universe,
        cache_path=history_cache,
    )

    return universe
