import math
import random
import string
from dataclasses import dataclass, field
from typing import ClassVar, Tuple

import numpy as np
from matplotlib import axes, figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from util import normalize_to_interval


def random_string_of_length(n):
    return "".join(random.choice(string.ascii_uppercase) for i in range(n))


def divide_chunks(iterable, chunk_size):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i : i + chunk_size]



@dataclass
class Tick:
    position: float
    label: str

    def draw(self, ax, pos=None):
        if pos is None:
            pos = self.position

        ax.text(
            x=pos,
            y=0,
            s=self.label,
            verticalalignment="top",
            horizontalalignment="center",
            fontsize=10,
        )


@dataclass
class HorizontalBar:
    y_position: float
    width: float
    xdata: np.ndarray = field(repr=False)
    ydata: np.ndarray = field(repr=False)
    ax: axes.Axes = field(repr=False)
    label: str = field(repr=False)
    ticks: Tuple[Tick] = field(repr=False)
    index: int  # from 0 to N - 1, with N the total number of bars in Figure
    scale_factor: int

    height: ClassVar[float] = 0.75
    background_color: ClassVar[str] = "0.95"
    ydata_normalized: np.ndarray = field(init=False, repr=False)
    y_extent: Tuple[float] = field(init=False, repr=False)

    def __post_init__(self):
        self.y_extent = (
            self.y_position - self.height / 2,
            self.y_position + self.height / 2,
        )
        self.ydata_normalized = self.normalize_y()

    def __eq__(self, other):
        if not isinstance(other, HorizontalBar):
            return NotImplemented
        return self.index == other.index

    def __str__(self):
        return f"{self.index} {self.label}: {self.y_extent[0]}<{self.y_position}>{self.y_extent[1]}"

    def normalize_y(self, y_data=None):
        if y_data is None:
            y_data = self.ydata

        a, b = self.y_extent
        return normalize_to_interval(a, b, y_data)

    def draw_solid_background(self):
        self.ax.barh(
            y=self.y_position,
            width=self.width,
            height=self.height,
            color=self.background_color,
            zorder=-20,
        )

    def add_label(self, left_offset=-0.1):
        self.ax.text(
            x=left_offset,
            y=self.y_position,
            s=self.label,
            horizontalalignment="right",
            fontsize=16,
        )

    def add_left_spine(self, color="black", linewidth=3):
        self.ax.axvline(
            x=0,
            ymin=(self.y_position - 0.4) / self.scale_factor,
            ymax=(self.y_position + 0.4) / self.scale_factor,
            color=color,
            linewidth=linewidth,
        )

    def add_vertical_tick_line(self, x_pos, color="0.5", linewidth=0.5):
        self.ax.axvline(
            x=x_pos,
            ymin=(self.y_position - 0.375) / self.scale_factor,
            ymax=(self.y_position + 0.375) / self.scale_factor,
            color=color,
            linewidth=linewidth,
            zorder=-15,
        )

    def add_tick_lines(self):
        for tick in self.ticks:
            self.add_vertical_tick_line(tick.position * self.scale_factor)

    def prepare(self):
        self.draw_solid_background()
        self.add_label()
        self.add_left_spine()
        self.add_tick_lines()

    def plot_data(self, y_data=None, color="black", linewidth=2, zorder=2):
        if y_data is None:
            y_data = self.ydata_normalized

        self.ax.plot(
            self.xdata, y_data, color=color, linewidth=linewidth, zorder=zorder
        )


@dataclass
class FigureHorizontalBars:
    X: np.ndarray = field(repr=False)
    Y: np.ndarray = field(repr=False)
    x_ticks: Tuple[Tick] = field(repr=False)
    y_labels: Tuple[str] = field(repr=False)

    fig: figure.Figure = field(init=False, repr=False)
    bars: Tuple[HorizontalBar] = field(init=False, repr=False)
    n_subplots: int = field(init=False, repr=False)
    max_bars_per_subplot: ClassVar[int] = 8

    def __post_init__(self):
        n_bars = self.Y.shape[0]
        self.n_subplots = math.ceil(n_bars / self.max_bars_per_subplot)

        self.fig = figure.Figure(figsize=(20, 8), dpi=192)
        canvas = FigureCanvasAgg(self.fig)

        self.bars = self.create_bars()

    def create_bars(self):
        bars = list()
        nrows, ncols = 1, self.n_subplots

        for subplot_index, subplot_y_data in zip(  # loop over subplots
            range(self.n_subplots), divide_chunks(self.Y, self.max_bars_per_subplot)
        ):
            bars_per_subplot = subplot_y_data.shape[0]
            subplot_x_data = normalize_to_interval(0.0, bars_per_subplot, self.X)

            subplot_ax = self.fig.add_subplot(nrows, ncols, subplot_index + 1, aspect=1)
            subplot_ax.set_xlim(0, bars_per_subplot)
            subplot_ax.set_ylim(0, bars_per_subplot)

            for tick in self.x_ticks:
                tick.draw(ax=subplot_ax, pos=tick.position * bars_per_subplot)

            subplot_ax.set_axis_off()
            # loop over horizontal bars in each subplot
            for bar_index, bar_y_data in enumerate(subplot_y_data):
                overall_bar_index = (
                    subplot_index * self.max_bars_per_subplot + bar_index
                )
                bar_center = bars_per_subplot - (bar_index + 0.5)

                bar = HorizontalBar(
                    y_position=bar_center,
                    width=bars_per_subplot,
                    xdata=subplot_x_data,
                    ydata=bar_y_data,
                    ax=subplot_ax,
                    label=self.y_labels[overall_bar_index],
                    ticks=self.x_ticks,
                    index=overall_bar_index,
                    scale_factor=bars_per_subplot,
                )
                bars.append(bar)

        return tuple(bars)

    def prepare(self):
        for bar in self.bars:
            bar.prepare()

    def plot_lines(self):
        for bar in self.bars:
            bar.plot_data()

    def plot_other_lines(self):
        for main_bar in self.bars:
            for secondary_bar in self.bars:
                if main_bar != secondary_bar:
                    main_bar.plot_data(
                        y_data=main_bar.normalize_y(secondary_bar.ydata),
                        color="0.5",
                        linewidth=0.5,
                        zorder=-10,
                    )

    def render(self):
        self.prepare()
        self.plot_lines()
        self.plot_other_lines()

    def save(self, fname="gpu_figure.png", dpi=192):
        self.fig.savefig(fname, dpi=dpi)


def main():
    """Main entry point."""
    hbars = 16
    num_data_points = 200
    X = np.linspace(start=0, stop=2 * np.pi, num=num_data_points, endpoint=True)

    Y = np.zeros(shape=(hbars, num_data_points), dtype=np.float64)

    random.seed(42)
    labels = list()
    for row in range(hbars):
        Y[row] = np.sin((row + 1) * X)
        labels.append(random_string_of_length(4))

    Y_labels = tuple(labels)
    X_ticks = tuple(
        [
            Tick(0.0, "$0$"),
            Tick(0.25, "$\\frac{\\pi}{2}$"),
            Tick(0.5, "$\\pi$"),
            Tick(0.75, "$\\frac{3\\pi}{2}$"),
            Tick(1.0, "$2\\pi$"),
        ]
    )
    # ----------------------------------------------------------------------------------

    f = FigureHorizontalBars(
        X=X,
        Y=Y,
        x_ticks=X_ticks,
        y_labels=Y_labels,
    )
    f.render()
    f.save()


if __name__ == "__main__":
    main()
