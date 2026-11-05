"""Chart styling shared by all scripts: two validated colours, light grid, thin marks."""
import matplotlib

matplotlib.use("Agg")  # draw to files only, no window needed
import matplotlib.pyplot as plt

BLUE = "#2a78d6"     # series 1
ORANGE = "#eb6834"   # series 2 / highlight
INK = "#0b0b0b"      # primary text
INK_SOFT = "#52514e" # secondary text
SURFACE = "#fcfcfb"
GRID = "#e4e3df"


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_SOFT,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
    })


def clean_axes(ax, grid_axis="y") -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
