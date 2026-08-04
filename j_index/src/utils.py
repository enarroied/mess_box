import time

import pandas as pd
from pathlib import Path


def load_parquet_cache(cache_path, columns=None):
    """Load a parquet cache if it exists.

    If the cache does not exist, return an empty dataframe
    with the requested columns.
    """

    cache_path = Path(cache_path)

    if cache_path.exists():
        return pd.read_parquet(
            cache_path,
            engine="pyarrow",
        )

    if columns:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame()


def save_parquet_cache(df, cache_path, index=False):
    """Save dataframe as parquet cache."""

    cache_path = Path(cache_path)

    cache_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        cache_path,
        engine="pyarrow",
        index=index,
    )


def rate_limit(counter, every=5, pause=1):
    """Sleep every N calls to be polite to APIs."""

    counter += 1

    if counter % every == 0:
        time.sleep(pause)

    return counter


def result_to_df(result):
    """Return a pandas DataFrame from an OBBject result.

    With `output_type = "dataframe"` the OpenBB endpoints already return a
    DataFrame, otherwise they return an OBBject with a `.to_df()` method.
    """

    if hasattr(result, "to_df"):
        return result.to_df()

    return result
