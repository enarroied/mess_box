import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import ticker
from contextlib import nullcontext
import pandas as pd
from typing import Union


def _format_big_number_for_axis(x, pos):
    if x >= 1e9:
        return f"{x/1e9:.1f}B"
    return f"{int(x/1e6)}M"


class BasePopulationPlotter:
    def __init__(self, df, year, historical_max, palette: Union[str | dict], filename=None):
        self.df = df
        self.year = year
        self.historical_max = historical_max
        self.filename = filename
        self.palette = palette

    def _apply_style(self):
        """Default: no special style."""
        return nullcontext()

    def _plot(self, ax):
        raise NotImplementedError("Subclasses must implement _plot(ax)")

    def _format_axis(self, ax):
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_format_big_number_for_axis))
        ax.set_xlim(0, self.historical_max)

    def save(self):
        fig = plt.figure(figsize=(9, 16))
        ax = fig.add_axes([0.3, 0.08, 0.65, 0.84])

        with self._apply_style():
            self._plot(ax)
            self._format_axis(ax)

            ax.spines["left"].set_position(("axes", 0))
            ax.tick_params(axis="y", which="major", pad=20)
            ax.set_xlabel("Population", fontsize=20)
            ax.set_ylabel("")
            ax.set_title(f"Top 10 countries - {self.year}", fontsize=24, weight="bold")
            ax.tick_params(axis="both", which="major", labelsize=18)

            plt.savefig(self.filename, dpi=300)
            plt.close()
        return self.filename


class CleanBarPlotter(BasePopulationPlotter):
    def _plot(self, ax):
        sns.barplot(
            data=self.df,
            y="Country",
            x="Population",
            hue="Country",
            palette=self.palette,
            dodge=False,
            legend=False,
            ax=ax,
        )


class XKCDBarPlotter(BasePopulationPlotter):
    def _apply_style(self):
        return plt.xkcd()

    def _plot(self, ax):
        sns.barplot(
            data=self.df,
            y="Country",
            x="Population",
            hue="Country",
            palette=self.palette,
            dodge=False,
            legend=False,
            ax=ax,
        )
