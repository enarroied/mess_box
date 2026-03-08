import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import ticker
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import nullcontext


def _format_big_number(x, pos):
    if x >= 1e12:
        return f"{x / 1e12:.1f}T"
    elif x >= 1e9:
        return f"{x / 1e9:.1f}B"
    elif x >= 1e6:
        return f"{x / 1e6:.1f}M"
    elif x >= 1e3:
        return f"{x / 1e3:.1f}K"
    return f"{int(x)}"


class ChartGenerator:
    def __init__(self, dataset, config: Dict[str, Any]):
        self.dataset = dataset
        self.config = config
        self.chart_config = config.get("chart", {})

    def _resolve_figure_size(self) -> tuple:
        fmt = self.config["format"]
        if fmt == "shorts":
            return (9, 16)
        elif fmt == "square":
            return (10, 10)
        else:  # landscape
            return (16, 9)

    def _apply_style(self):
        style = self.chart_config.get("style")
        if style:
            return plt.style.context(style)
        return nullcontext()

    def _get_palette(self, entities: list = None):
        custom_colors = self.chart_config.get("colors")
        if custom_colors:
            return custom_colors

        color_map = self.dataset.color_map
        if entities and color_map:
            return {e: color_map.get(e, "#333333") for e in entities}

        return "tab20"

    def _format_title(self, time_value: Any) -> str:
        template = self.chart_config.get("title_template", "{year}")
        time_col = self.dataset.time_label
        return template.replace(f"{{{time_col}}}", str(time_value)).replace(
            "{year}", str(time_value)
        )

    def generate_frame(self, df, time_value: Any, output_path: Path) -> Path:
        figsize = self._resolve_figure_size()

        fig = plt.figure(figsize=figsize)

        if self.config["format"] == "shorts":
            ax = fig.add_axes([0.25, 0.1, 0.7, 0.8])
        elif self.config["format"] == "square":
            ax = fig.add_axes([0.3, 0.08, 0.65, 0.84])
        else:  # landscape
            ax = fig.add_axes([0.15, 0.15, 0.8, 0.75])

        with self._apply_style():
            entities = df[self.dataset.entity_col].tolist()
            palette = self._get_palette(entities)

            sns.barplot(
                data=df,
                y=self.dataset.entity_col,
                x=self.dataset.value_col,
                hue=self.dataset.entity_col,
                palette=palette,
                dodge=False,
                legend=False,
                ax=ax,
            )

            ax.xaxis.set_major_formatter(ticker.FuncFormatter(_format_big_number))

            global_max = self.dataset.get_global_max()
            ax.set_xlim(0, global_max * 1.1)

            ax.spines["left"].set_position(("axes", 0))
            ax.tick_params(axis="y", which="major", pad=20)
            ax.set_xlabel(self.dataset.x_label, fontsize=20)
            ax.set_ylabel("")

            title = self._format_title(time_value)
            ax.set_title(title, fontsize=28, weight="bold", pad=20)
            ax.tick_params(axis="both", which="major", labelsize=16)

            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()

        return output_path

    def generate_frames(
        self,
        frames_dir: Path,
    ) -> list[Path]:
        frames_dir.mkdir(parents=True, exist_ok=True)

        top_n = self.chart_config.get("top_n", 10)
        time_values = self.dataset.all_times

        frame_paths = []

        for i, time_val in enumerate(time_values):
            df = self.dataset.get_top_n_for_time(time_val, n=top_n)
            output_path = frames_dir / f"frame_{i:04d}.png"
            self.generate_frame(df, time_val, output_path)
            frame_paths.append(output_path)
            print(f"Generated frame {i + 1}/{len(time_values)}: {time_val}")

        return frame_paths
