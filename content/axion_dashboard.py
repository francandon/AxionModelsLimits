# axion_dashboard.py
import io
import json
import base64

import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for PNG output
import matplotlib.pyplot as plt

from PlotFuncs import FigSetup, AxionPhoton

# --- Physics helpers ---------------------------------------------------------
alpha = 1 / 137.035999084
K = 5.70e6
_pref = alpha / (2 * np.pi)


def g_agamma(m_eV, C):
    return np.abs(_pref * C * (m_eV / K))


# models and categories as in your notebook
MODELS = [
    {"name": "KSVZ", "Ndw": "1", "C": (-1.92, -1.92)},
    {"name": "DFSZ-I", "Ndw": "6,3", "C": (0.75, 0.75)},
    {"name": "DFSZ-II", "Ndw": "6,3", "C": (-1.25, -1.25)},
    {"name": "Astrophobic QCD axion", "Ndw": "1,2", "C": (-6.59, 0.74)},
    {"name": r"VISH$\nu$", "Ndw": "1", "C": (0.75, 0.75)},
    {"name": r"$\nu$DFSZ", "Ndw": "6", "C": (0.75, 0.75)},
    {"name": "Majoraxion", "Ndw": "—", "C": (2.66, 2.66)},
    {"name": "Composite Axion", "Ndw": "0/2/6", "C": (1.33, 2.66)},
]

CATEGORIES = {
    "Helioscopes": AxionPhoton.Helioscopes,
    "White Dwarfs": AxionPhoton.WhiteDwarfs,
    "Stellar Bounds": AxionPhoton.StellarBounds,
    "Haloscopes": AxionPhoton.Haloscopes,
    "Solar Basin": AxionPhoton.SolarBasin,
    "StAB": AxionPhoton.StAB,
    "QCD Axion": AxionPhoton.QCDAxion,
}


def _call_on_ax_and_close_new_figs(name, fn, ax, kwargs=None):
    """
    Helper: call one of the AxionPhoton plotting functions on our Axes,
    but prevent it from opening its own figure.
    """
    import matplotlib.pyplot as plt

    prev_figs = set(plt.get_fignums())
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    was_auto = ax.get_autoscale_on()

    ax.set_autoscale_on(False)
    plt.sca(ax)

    try:
        if kwargs is None:
            kwargs = {}
        try:
            fn(ax, **kwargs)      # positional ax
        except TypeError:
            fn(ax=ax, **kwargs)   # keyword ax
    except Exception as e:
        print(f"[axion_dashboard] ERROR in {name}: {e}")
    finally:
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_autoscale_on(was_auto)

        for num in (set(plt.get_fignums()) - prev_figs):
            plt.close(num)


# --- main entry point for JS / Pyodide ---------------------------------------
def make_axion_plot(config_json: str) -> str:
    """
    Main API for JS. `config_json` is a JSON string with, e.g.:

    {
      "mmin": 1e-12,
      "mmax": 1e-1,
      "ymin": 1e-20,
      "ymax": 1e-8,
      "models": ["KSVZ", "DFSZ-I"],
      "categories": ["Helioscopes", "Haloscopes"]
    }

    Returns: base64-encoded PNG (no header).
    """
    cfg = json.loads(config_json)

    mmin = float(cfg["mmin"])
    mmax = float(cfg["mmax"])
    ymin = float(cfg["ymin"])
    ymax = float(cfg["ymax"])
    selected_models = set(cfg.get("models", []))
    selected_categories = set(cfg.get("categories", []))

    # --- set up figure/axes using your PlotFuncs helper
    fig, ax = FigSetup(
        Shape="Rectangular",
        xlab=r"$m_a$ [eV]",
        ylab=r"$|g_{a\gamma}|$ [GeV$^{-1}$]",
        mathpazo=True,
    )

    # LaTeX is not supported in Pyodide, keep it off
    matplotlib.rcParams["text.usetex"] = False

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(mmin, mmax)
    ax.set_ylim(ymin, ymax)

    # --- model curves --------------------------------------------------------
    m_grid = np.logspace(np.log10(mmin), np.log10(mmax), 600)
    for md in MODELS:
        if md["name"] not in selected_models:
            continue
        cmin, cmax = md["C"]
        ndw = md.get("Ndw", "—")
        if np.isclose(cmin, cmax):
            yy = g_agamma(m_grid, cmin)
            ax.plot(m_grid, yy, lw=2, alpha=0.95,
                    label=rf"{md['name']} ($N_{{\rm dw}}$={ndw})")
        else:
            y1 = g_agamma(m_grid, cmin)
            y2 = g_agamma(m_grid, cmax)
            ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
            ax.fill_between(m_grid, ylo, yhi, alpha=0.25)
            ax.plot(m_grid, np.sqrt(ylo * yhi), lw=1.5, alpha=0.85,
                    label=rf"{md['name']} ($N_{{\rm dw}}$={ndw})")

    # --- experimental/astro bounds ------------------------------------------
    for name in selected_categories:
        fn = CATEGORIES.get(name)
        if fn is None:
            continue
        _call_on_ax_and_close_new_figs(name, fn, ax, {})

    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.set_title("Axion–Photon Coupling vs Mass", pad=8)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    return base64.b64encode(buf.getvalue()).decode("ascii")
