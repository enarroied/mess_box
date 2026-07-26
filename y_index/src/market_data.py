from datetime import datetime, timedelta

import pandas as pd
import requests
from openbb import obb

from src.utils import load_parquet_cache, rate_limit, save_parquet_cache

SEC_HEADERS = {"User-Agent": "J Index research contact@example.com"}

SEC_COUNTRY_CODES = {
    "F4": "China",
    "K3": "Hong Kong",
    "U0": "Singapore",
}


def check_ticker_history(ticker, minimum_days=365):
    """Check if ticker has enough historical data."""

    try:
        prices = obb.equity.price.historical(
            ticker,
            provider="yfinance",
            start_date=(datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d"),
        ).to_df()

        if prices.empty:
            return {
                "Symbol": ticker,
                "status": "no_data",
            }

        first_date = pd.to_datetime(prices.index.min())

        last_date = pd.to_datetime(prices.index.max())

        days = (last_date - first_date).days

        if days >= minimum_days:
            status = "ok"
        else:
            status = "too_recent"

        return {
            "Symbol": ticker,
            "status": status,
            "first_date": first_date,
            "last_date": last_date,
            "days_history": days,
        }

    except Exception as e:
        return {
            "Symbol": ticker,
            "status": "error",
            "error": str(e),
        }


def download_company_metadata(ticker):
    """Download metadata for one company."""

    try:
        profile = (
            obb.equity.profile(
                ticker,
                provider="yfinance",
            )
            .to_df()
            .iloc[0]
        )

        return {
            "Symbol": ticker,
            "Company": profile.get("name"),
            "Sector": profile.get("sector"),
            "Industry": profile.get("industry"),
            "Country": profile.get("country"),
            "Currency": profile.get("currency"),
            "MarketCap": profile.get("market_cap"),
        }

    except Exception as e:
        print(f"{ticker}: {e}")

        return {
            "Symbol": ticker,
            "Company": None,
            "Sector": None,
            "Industry": None,
            "Country": None,
            "Currency": None,
            "MarketCap": None,
        }


def enrich_companies(
    universe,
    cache_path="data/company_metadata.parquet",
):
    """Download metadata for all companies."""

    cache = load_parquet_cache(
        cache_path,
        columns=[
            "Symbol",
            "Company",
            "Sector",
            "Industry",
            "Country",
            "Currency",
            "MarketCap",
        ],
    )

    cached = set(cache["Symbol"])

    rows = []

    counter = 0

    for ticker in universe["Symbol"]:
        if ticker in cached:
            rows.append(cache.loc[cache["Symbol"] == ticker].iloc[0])

            continue

        print(ticker)

        row = download_company_metadata(ticker)

        rows.append(row)

        counter = rate_limit(counter)

    metadata = pd.DataFrame(rows).drop_duplicates("Symbol").reset_index(drop=True)

    save_parquet_cache(metadata, cache_path)

    return universe.merge(
        metadata,
        on="Symbol",
        how="left",
        suffixes=("", "_meta"),
    )


def get_sec_company_info(cik):
    """Retrieve company metadata from SEC submissions API."""

    cik = str(int(cik)).zfill(10)

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    try:
        r = requests.get(
            url,
            headers=SEC_HEADERS,
            timeout=10,
        )

        r.raise_for_status()

        data = r.json()

        address = data.get("addresses", {}).get("business", {})

        if not address:
            address = data.get("addresses", {}).get("mailing", {})

        foreign = address.get("isForeignLocation")

        if foreign == 1:
            country = (
                address.get("country")
                or SEC_COUNTRY_CODES.get(address.get("stateOrCountry"))
                or address.get("stateOrCountry")
            )
        else:
            country = "United States"

        return {
            "Country": country,
            "SIC": data.get("sic"),
            "SIC_Description": data.get("sicDescription"),
        }

    except Exception as e:
        print(f"SEC API error for CIK {cik}: {e}")

        return {
            "Country": None,
            "SIC": None,
            "SIC_Description": None,
        }


def enrich_with_sec(df):
    """Add SEC company information."""

    rows = []

    counter = 0

    for _, row in df.iterrows():
        sec_info = get_sec_company_info(row["CIK"])

        rows.append(
            {
                "Symbol": row["Symbol"],
                **sec_info,
            }
        )

        counter = rate_limit(counter, every=5, pause=0.2)

    sec_df = pd.DataFrame(rows)

    if "Country" in df.columns:
        df = df.drop(columns=["Country"])

    return df.merge(
        sec_df,
        on="Symbol",
        how="left",
    )
