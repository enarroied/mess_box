import pandas as pd
import seaborn as sns
import yaml
from typing import Optional, Dict, Any


def import_filters_from_yaml(filepath: str) -> Dict[str, Any]:
    """Load a YAML file and return a dictionary (or empty dict on error)."""
    try:
        with open(filepath, "r") as fh:
            data = yaml.safe_load(fh) or {}
            if not isinstance(data, dict):
                print(
                    f"Warning: YAML at {filepath} did not parse to a dict. Got {type(data)}"
                )
                return {}
            return data
    except FileNotFoundError:
        print(f"Error: The file at {filepath} was not found.")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return {}


class TableToPlot:
    """
    Loads a CSV, optionally renames columns, applies YAML filters (works whether YAML uses
    original column names or the renamed names), and provides helpers for top-n by year.
    """

    def __init__(
        self,
        filename: str,
        categorical_column: str,
        filter_out_path: str = "",
        colums_to_rename: Optional[Dict[str, str]] = None,
        year_column: Optional[str] = "Year",
    ):
        self.filename = filename
        self.categorical_column = categorical_column
        self.filter_out = (
            import_filters_from_yaml(filter_out_path) if filter_out_path else {}
        )
        self.colums_to_rename = colums_to_rename or {}
        self.df = pd.read_csv(self.filename)
        if self.colums_to_rename:
            self.df = self.df.rename(columns=self.colums_to_rename)

        self.clean_df = self._load_and_clean()
        self.color_map = self.create_color_palette()
        self.all_years = list(self.df[year_column].unique())

    def _load_and_clean(self) -> pd.DataFrame:
        """Apply the `filter_out` rules to the DataFrame, accepting filter keys that
        reference either original names (keys of colums_to_rename) or the final renamed names.
        """
        df_cp = self.df.copy()

        for filter_col, values_to_filter in self.filter_out.items():
            # normalize values to a list
            if values_to_filter is None:
                continue
            if not isinstance(values_to_filter, (list, tuple, set)):
                values = [values_to_filter]
            else:
                values = list(values_to_filter)

            if filter_col in df_cp.columns:
                actual_col = filter_col
            else:
                mapped = self.colums_to_rename.get(filter_col)
                if mapped and mapped in df_cp.columns:
                    actual_col = mapped
                else:
                    if (
                        filter_col in self.colums_to_rename.values()
                        and filter_col in df_cp.columns
                    ):
                        actual_col = filter_col
                    else:
                        print(
                            f"Warning: filter column '{filter_col}' not found in data columns. Skipping filter."
                        )
                        continue
            df_cp = df_cp[~df_cp[actual_col].isin(values)]
        return df_cp

    def get_top_entities(
        self, n: int = 10, by_column: Optional[str] = None
    ) -> pd.DataFrame:
        """Return top-n rows either by specified column or just head(n)."""
        if by_column and by_column in self.clean_df.columns:
            return self.clean_df.nlargest(n, by_column).reset_index(drop=True)
        return self.clean_df.head(n).reset_index(drop=True)

    def create_color_palette(self, base_palette: str = "tab20") -> Dict[str, Any]:
        """Create a color mapping for unique values of `categorical_column`."""
        if self.categorical_column not in self.clean_df.columns:
            print(
                f"Warning: categorical column '{self.categorical_column}' not found. Returning empty color map."
            )
            return {}
        categories = list(self.clean_df[self.categorical_column].unique())
        palette = sns.color_palette(base_palette, len(categories))
        return dict(zip(categories, palette))

    def _filter_by_year(self, year: int, year_column: str = "Year"):
        if year_column not in self.clean_df.columns:
            raise KeyError(f"Year column '{year_column}' not found in data.")
        return self.clean_df[self.clean_df[year_column] == year].copy()

    def get_top_n_by_year(
        self,
        year: int,
        order_column: str,
        year_column: str = "Year",
        rows_to_order: int = 10,
    ):
        """
        Return (top_df, total) for the selected year. top_df includes Percent of Total
        computed from the provided order_column (no hard-coded 'Population').
        """
        df_filtered = self._filter_by_year(year, year_column)
        if order_column not in df_filtered.columns:
            raise KeyError(
                f"Order column '{order_column}' not found in filtered data for year {year}."
            )
        total = df_filtered[order_column].sum()
        top_n = (
            df_filtered.nlargest(rows_to_order, order_column)
            .drop(columns=[year_column], errors="ignore")
            .reset_index(drop=True)
        )
        top_n["Percent of Total"] = (top_n[order_column] * 100 / total).round(2)
        return top_n
