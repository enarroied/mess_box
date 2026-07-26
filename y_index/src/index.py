import pandas as pd

from src.market_data import enrich_companies, enrich_with_sec


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
