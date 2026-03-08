import pandas as pd
import seaborn as sns
from pathlib import Path
from typing import Dict, Any, Optional


class DatasetHandler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.csv_path = config["csv_path"]

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        self.df = pd.read_csv(self.csv_path)

        entity_col = config.get("entity_col")
        time_col = config.get("time_col")
        value_col = config.get("value_col")

        self.entity_col = entity_col or self._detect_column(0, "entity")
        self.time_col = time_col or self._detect_column(1, "time")
        self.value_col = value_col or self._detect_column(2, "value")

        self.all_times = sorted(self.df[self.time_col].unique())
        self.color_map = self._create_color_map()

    def _detect_column(self, index: int, col_type: str) -> str:
        cols = list(self.df.columns)
        if index >= len(cols):
            raise ValueError(
                f"Cannot auto-detect {col_type} column: CSV has only {len(cols)} columns, "
                f"need at least {index + 1}. Please specify in config."
            )
        return cols[index]

    def _create_color_map(self) -> Dict[str, Any]:
        unique_entities = list(self.df[self.entity_col].unique())
        palette = sns.color_palette("tab20", len(unique_entities))
        return dict(zip(unique_entities, palette))

    def get_top_n_for_time(self, time_value: Any, n: int = 10) -> pd.DataFrame:
        df_filtered = self.df[self.df[self.time_col] == time_value].copy()

        total = df_filtered[self.value_col].sum()

        top_n = df_filtered.nlargest(n, self.value_col).reset_index(drop=True)

        if total > 0:
            top_n["percent_of_total"] = (top_n[self.value_col] * 100 / total).round(2)

        return top_n

    @property
    def y_label(self) -> str:
        return self.entity_col

    @property
    def x_label(self) -> str:
        return self.value_col

    @property
    def time_label(self) -> str:
        return self.time_col
