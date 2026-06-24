"""Axion–Photon Coupling Explorer.

Optimized Panel/Pyodide implementation of the redesigned interface.

Build with ``build_site.sh`` supplied alongside this file.  The WebAssembly
build must include ``assets_fixed.zip`` as a Panel resource; the app deliberately
performs no synchronous HTTP download during startup.
"""

import base64
import io
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.text
import numpy as np
import panel as pn


# -----------------------------------------------------------------------------
# Panel resources and visual tokens
# -----------------------------------------------------------------------------
pn.extension(
    "katex",
    sizing_mode="stretch_width",
    css_files=[
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;0,700&family=IBM+Plex+Mono:wght@400;500;600&display=swap",
    ],
)

NAVY = "#1b3b5a"
NAVY_DEEP = "#102233"
NAVY_MID = "#294f75"
STEEL = "#3f6493"
ACCENT = "#c9772f"
PAPER = "#e9edf3"
CARD = "#ffffff"
LINE = "#dbe3ee"
LINE_SOFT = "#eef2f7"
MUTED = "#65758a"
MUTED_2 = "#8b98a9"

MODEL_PALETTE = [
    "#0173B2",
    "#DE8F05",
    "#CC78BC",
    "#CA9161",
    "#56B4E9",
    "#1B9E77",
    "#C9B215",
    "#E84C3D",
]

GLOBAL_CSS = f"""
:root {{
  --axe-navy:{NAVY}; --axe-navy-deep:{NAVY_DEEP}; --axe-steel:{STEEL};
  --axe-accent:{ACCENT}; --axe-paper:{PAPER}; --axe-card:{CARD};
  --axe-line:{LINE}; --axe-line-soft:{LINE_SOFT}; --axe-muted:{MUTED};
}}
html, body {{ min-height:100%; background:{PAPER}; }}
body, .bk-root {{
  margin:0; color:{NAVY_DEEP};
  font-family:'IBM Plex Sans',system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
}}
.axe-page {{ width:100%; max-width:1540px; margin:0 auto; }}
.axe-body {{ box-sizing:border-box; }}
.axe-sidebar {{
  scrollbar-width:thin; scrollbar-color:#b7c4d3 transparent;
}}
.axe-sidebar::-webkit-scrollbar {{ width:6px; }}
.axe-sidebar::-webkit-scrollbar-thumb {{ background:#b7c4d3; border-radius:99px; }}
.axe-eyebrow {{
  font-family:'IBM Plex Mono',monospace; font-size:10px; font-weight:600;
  letter-spacing:.12em; text-transform:uppercase; color:{ACCENT};
}}
.axe-card-title {{
  color:{NAVY_DEEP}; font-size:13px; line-height:1.25; font-weight:700;
}}
.axe-card-caption {{
  color:{MUTED_2}; font-size:11px; line-height:1.45; margin-top:4px;
}}
.axe-range-label {{
  color:{NAVY}; font-size:12px; line-height:1.2; font-weight:600;
}}
.axe-range-value {{
  color:{STEEL}; font-family:'IBM Plex Mono',monospace; font-size:10.5px;
  white-space:nowrap;
}}
.axe-slider-side {{
  width:28px; color:{MUTED_2}; font-family:'IBM Plex Mono',monospace;
  font-size:9px; text-transform:lowercase;
}}
.axe-model-name {{ font-size:12px; font-weight:600; color:{NAVY_DEEP}; white-space:nowrap; }}
.axe-model-coeff {{
  font-family:'IBM Plex Mono',monospace; font-size:10.5px; color:{MUTED_2};
  text-align:right; white-space:nowrap;
}}
.axe-model-row {{
  border-bottom:1px solid {LINE_SOFT}; min-height:38px; box-sizing:border-box;
}}
.axe-model-row:last-child {{ border-bottom:0; }}
.axe-plot-stage {{ position:relative; overflow:hidden; border:1px solid {LINE_SOFT}; border-radius:9px; }}
.axe-live-badge {{
  position:absolute; z-index:5; left:16px; top:13px; pointer-events:none;
  border:1px solid {LINE}; border-radius:5px; background:rgba(255,255,255,.92);
  color:{MUTED_2}; padding:5px 8px; font-family:'IBM Plex Mono',monospace;
  font-size:9.5px; letter-spacing:.08em; text-transform:uppercase;
}}
.axe-plot-title {{
  font-family:'IBM Plex Serif',serif; color:{NAVY_DEEP}; font-size:17px;
  font-weight:600; line-height:1.2;
}}
.axe-plot-subtitle {{ color:{MUTED}; font-size:11.5px; margin-top:4px; }}
.axe-window-note {{
  color:{STEEL}; font-family:'IBM Plex Mono',monospace; font-size:10.5px;
}}
.axe-plot-note {{ color:{MUTED_2}; font-size:10.5px; text-align:right; }}
.axe-equation-card {{ overflow:hidden; }}
.axe-equation-band {{
  background:linear-gradient(180deg,#f8fafc,#eef3f8); border-top:1px solid {LINE_SOFT};
  border-bottom:1px solid {LINE_SOFT};
}}
.axe-equation-constant {{ min-width:190px; text-align:center; }}
.axe-equation-caption {{ color:{MUTED_2}; font-size:10.5px; margin-top:2px; text-align:center; }}
.axe-table-wrap {{ overflow-x:auto; }}
.modern-card.pn-card, .modern-card .card {{ background:transparent !important; border:0 !important; box-shadow:none !important; }}
.modern-card > .card > .card-header, .modern-card .card-header {{
  background:{CARD} !important; border:1px solid {LINE} !important; border-radius:11px !important;
  box-shadow:0 5px 18px rgba(16,34,51,.04); color:{NAVY_DEEP} !important;
  font-size:13px !important; font-weight:700 !important; padding:12px 14px !important;
}}
.modern-card > .card > .card-body, .modern-card .card-body {{
  background:{CARD} !important; border:1px solid {LINE} !important; border-top:0 !important;
  border-radius:0 0 11px 11px !important; padding:10px !important;
}}
.modern-accordion .accordion-item, .modern-accordion .card {{
  border:1px solid {LINE} !important; border-radius:8px !important; overflow:hidden;
  box-shadow:none !important; margin-bottom:7px !important;
}}
.modern-accordion .accordion-button, .modern-accordion .card-header {{
  background:{LINE_SOFT} !important; color:{NAVY_DEEP} !important;
  font-size:11.5px !important; font-weight:600 !important; padding:8px 10px !important;
}}
.subgroup-accordion .accordion-button, .subgroup-accordion .card-header {{
  background:#fff !important; color:{STEEL} !important;
  font-family:'IBM Plex Mono',monospace !important; font-size:10.5px !important;
}}
@media (max-width: 980px) {{
  .axe-body {{ flex-wrap:wrap !important; }}
  .axe-sidebar {{ position:relative !important; top:auto !important; width:100% !important;
    max-height:none !important; margin-right:0 !important; }}
}}
"""
pn.config.raw_css.append(GLOBAL_CSS)

BTN_PRIMARY_SS = f"""
:host {{ --primary-bg-color:{NAVY}; }}
.bk-btn, .bk-btn-primary {{ background:{NAVY} !important; border-color:{NAVY} !important;
  color:#fff !important; border-radius:7px !important; font-weight:600 !important; }}
.bk-btn:hover {{ background:{NAVY_MID} !important; border-color:{NAVY_MID} !important; }}
"""
BTN_LIGHT_SS = f"""
.bk-btn, .bk-btn-light, .bk-btn-default {{ background:#fff !important; border:1px solid {LINE} !important;
  color:{NAVY} !important; border-radius:7px !important; font-weight:600 !important; }}
.bk-btn:hover {{ background:{LINE_SOFT} !important; }}
"""
BTN_TINY_SS = f"""
.bk-btn, .bk-btn-light, .bk-btn-default {{ background:{LINE_SOFT} !important; border:1px solid {LINE} !important;
  color:{STEEL} !important; border-radius:5px !important; font-family:'IBM Plex Mono',monospace !important;
  font-size:9.5px !important; font-weight:600 !important; padding:0 7px !important; }}
"""
BTN_EXPORT_SS = f"""
.bk-btn, .bk-btn-success {{ background:{ACCENT} !important; border-color:{ACCENT} !important;
  color:#fff !important; border-radius:7px !important; font-weight:700 !important; }}
.bk-btn:hover {{ filter:brightness(1.04); }}
"""
CHECK_SS = f"""
.bk-input-group {{ margin:0 !important; }}
label {{ margin:0 !important; min-height:18px !important; }}
input[type=checkbox] {{ accent-color:{NAVY}; width:15px !important; height:15px !important; }}
"""
SLIDER_SS = f"""
:host {{ --primary-color:{NAVY}; }}
.bk-input-group {{ margin:0 !important; }}
.noUi-target {{ height:4px !important; border:0 !important; border-radius:99px !important;
  background:#d6dfeb !important; box-shadow:none !important; }}
.noUi-connect {{ background:{NAVY} !important; }}
.noUi-handle {{ width:15px !important; height:15px !important; right:-7px !important; top:-6px !important;
  border:2px solid #fff !important; border-radius:50% !important; background:{NAVY} !important;
  box-shadow:0 1px 5px rgba(16,34,51,.28) !important; }}
.noUi-handle:before, .noUi-handle:after {{ display:none !important; }}
input[type=range] {{ accent-color:{NAVY}; }}
"""


def html(markup: str, **params: Any) -> pn.pane.HTML:
    defaults: dict[str, Any] = {"sizing_mode": "stretch_width", "margin": 0}
    defaults.update(params)
    return pn.pane.HTML(markup, **defaults)


def _image_data_uri(path: str) -> str:
    """Embed the logo so its browser path cannot break in a WASM build."""
    try:
        suffix = Path(path).suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(suffix, "image/png")
        encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except OSError:
        return path


# -----------------------------------------------------------------------------
# Runtime resources
# -----------------------------------------------------------------------------
def _ensure_runtime_assets() -> None:
    """Extract packaged data from the local resource archive.

    ``panel convert --resources`` puts the archive into Pyodide's virtual file
    system before this script executes.  No blocking browser HTTP request is
    necessary.
    """
    plot_funcs = Path("PlotFuncs.py")
    data_dir = Path("limit_data")
    if plot_funcs.exists() and data_dir.exists():
        return

    archive = next((Path(name) for name in ("assets_fixed.zip", "assets_optimized.zip", "assets.zip") if Path(name).exists()), None)
    if archive is not None:
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(".")

    if not plot_funcs.exists() or not data_dir.exists():
        raise FileNotFoundError(
            "PlotFuncs.py/limit_data are unavailable. Build with the supplied "
            "build_site.sh so assets_fixed.zip is included with --resources."
        )


_ensure_runtime_assets()

from PlotFuncs import AxionPhoton  # noqa: E402

ORGANIZATION_LOGO = _image_data_uri("./assets/logo_WISP.jpg")


# -----------------------------------------------------------------------------
# Physics model definitions
# -----------------------------------------------------------------------------
alpha = 1 / 137.035999084
K = 5.70e6
pref = alpha / (2 * np.pi)


def g_agamma(m_eV: np.ndarray, coefficient: float) -> np.ndarray:
    return np.abs(pref * coefficient * (m_eV / K))


models = [
    {"name": "KSVZ", "display_name": "KSVZ", "Ndw": "1", "C": (-1.92, -1.92), "category": "KSVZ-like"},
    {"name": "DFSZ-I", "display_name": "DFSZ-I", "Ndw": "6,3", "C": (0.75, 0.75), "category": "DFSZ-like"},
    {"name": "DFSZ-II", "display_name": "DFSZ-II", "Ndw": "6,3", "C": (-1.25, -1.25), "category": "DFSZ-like"},
    {"name": "Astrophobic QCD axion", "display_name": "Astrophobic axion", "Ndw": "1,2", "C": (-6.59, 0.74), "category": "Strongly deviated"},
    {"name": r"VISH$\nu$", "display_name": "VISHν", "Ndw": "1", "C": (0.75, 0.75), "category": "Strongly deviated"},
    {"name": r"$\nu$DFSZ", "display_name": "νDFSZ", "Ndw": "6", "C": (0.75, 0.75), "category": "DFSZ-like"},
    {"name": "Majoraxion", "display_name": "Majoraxion", "Ndw": "—", "C": (2.66, 2.66), "category": "Strongly deviated"},
    {"name": "Composite Axion", "display_name": "Composite axion", "Ndw": "0/2/6", "C": (1.33, 2.66), "category": "Strongly deviated"},
]

categories: dict[str, dict[str, list[dict[str, Any]]]] = {
    "Astrophysical Sources": {
        "Stellar Evolution": [
            {"name": "Low-Mass Astro", "fn": AxionPhoton.LowMassAstroBounds},
            {"name": "Stellar Bounds", "fn": AxionPhoton.StellarBounds},
            {"name": "White Dwarfs", "fn": AxionPhoton.WhiteDwarfs},
        ],
        "Supernovae and Transients": [
            {"name": "Supernova 1987A", "fn": AxionPhoton.SN1987A_gamma},
            {"name": "M82 Decay", "fn": AxionPhoton.M82_decay},
        ],
        "Compact Objects and High-Energy Sky": [],
    },
    "Cosmology and Diffuse Backgrounds": {
        "Dark Matter and Background Light": [
            {"name": "Dark Matter Decay", "fn": AxionPhoton.DarkMatterDecay},
        ],
        "Early Universe and Diffuse Media": [
            {"name": "Irreducible FreezeIn", "fn": AxionPhoton.IrreducibleFreezeIn},
        ],
    },
    "Haloscopes and Resonators": {
        "Combined Haloscope Bounds": [
            {"name": "Haloscopes All", "fn": AxionPhoton.Haloscopes},
        ],
        "Cavity Haloscopes": [],
        "Broadband and Low-Frequency Searches": [],
        "Future Haloscope Concepts": [],
    },
    "Helioscopes": {
        "Solar Axion Searches": [
            {"name": "Helioscopes", "fn": AxionPhoton.Helioscopes, "visible": True},
        ],
    },
    "Laboratory and Precision Searches": {
        "Light Shining Through Walls": [
            {"name": "LSW Experiments", "fn": AxionPhoton.LSW},
        ],
        "Polarimetry and Precision Probes": [],
        "Other Laboratory Searches": [],
    },
    "Colliders and Beam Dumps": {
        "Combined Collider Bounds": [
            {"name": "Collider Bounds", "fn": AxionPhoton.ColliderBounds},
        ],
        "Collider Searches": [],
        "Beam Dumps and Fixed Targets": [],
    },
}


# Populate the catalogue from the AxionPhoton API, while avoiding duplicates.
try:
    api_callables: list[tuple[str, Any]] = []
    for api_name in dir(AxionPhoton):
        if api_name.startswith("_"):
            continue
        try:
            api_member = getattr(AxionPhoton, api_name)
        except Exception:
            continue
        if callable(api_member):
            api_callables.append((api_name, api_member))

    category_rules = [
        ("Colliders and Beam Dumps", "Beam Dumps and Fixed Targets", ["beamdump", "mini", "nomad", "gluex", "primex"]),
        ("Colliders and Beam Dumps", "Collider Searches", ["atlas", "cms", "lhc", "lep", "babar", "belle", "besiii", "opal", "collider"]),
        ("Helioscopes", "Solar Axion Searches", ["helioscope", "helioscopes", "cast", "iaxo"]),
        ("Haloscopes and Resonators", "Cavity Haloscopes", ["admx", "rbf", "haystac", "taseh", "capp", "quax", "organ", "rades", "grahal", "base"]),
        ("Haloscopes and Resonators", "Broadband and Low-Frequency Searches", ["abracad", "dmradio", "srf", "wisplc", "upload", "lida"]),
        ("Haloscopes and Resonators", "Future Haloscope Concepts", ["madmax", "dali", "alpha", "flash", "cadex", "brass", "bread", "toorad", "lampost", "twistedanyoncavity"]),
        ("Haloscopes and Resonators", "Combined Haloscope Bounds", ["haloscope", "haloscopes"]),
        ("Laboratory and Precision Searches", "Light Shining Through Walls", ["alps", "lsw", "osqar", "crows", "sapphires", "wispfi"]),
        ("Laboratory and Precision Searches", "Polarimetry and Precision Probes", ["pvlas", "dance", "aligo", "supermag"]),
        ("Laboratory and Precision Searches", "Other Laboratory Searches", ["adbc", "shaft"]),
        ("Cosmology and Diffuse Backgrounds", "Dark Matter and Background Light", ["darkmatterdecay", "alpdecay", "planck", "cobe", "firas", "cmb", "cosmicbackground", "bicep", "polarbear", "mojave", "spt", "ppta", "quijote", "ppa"]),
        ("Cosmology and Diffuse Backgrounds", "Early Universe and Diffuse Media", ["bbn", "diffuse", "ionisation", "freeze"]),
        ("Astrophysical Sources", "Supernovae and Transients", ["fermi", "sn", "sne", "gw", "typeic", "m82", "theseus"]),
        ("Astrophysical Sources", "Stellar Evolution", ["globular", "white", "solar", "star", "stars", "mwd", "stab"]),
        ("Astrophysical Sources", "Compact Objects and High-Energy Sky", ["hydra", "m87", "hess", "mrk", "magic", "hawc", "chandra", "ngc", "h182", "nustar", "xmm", "integral", "xray", "xrays", "pulsar", "neutron", "muse", "jwst", "winered", "hst", "desi", "vimos", "gamma", "leot", "erosita", "axionstar"]),
    ]

    def humanize(name: str) -> str:
        spaced = name.replace("_", " ")
        if re.match(r"^[A-Z0-9 \-]+$", name):
            return " ".join(spaced.split())
        spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", spaced)
        return " ".join(spaced.split()).strip()

    existing_names: set[str] = set()
    existing_functions: set[Any] = set()
    for group in categories.values():
        for subgroup in group.values():
            for item in subgroup:
                existing_names.add(item["name"])
                existing_functions.add(item["fn"])

    for api_name, function in sorted(api_callables):
        if api_name == "QCDAxion":
            continue
        display = humanize(api_name)
        if display in existing_names or function in existing_functions:
            continue
        lower_name = api_name.lower()
        target_group, target_subgroup = "Other Bounds", "Uncategorized"
        for group_name, subgroup_name, keywords in category_rules:
            if any(keyword in lower_name for keyword in keywords):
                target_group, target_subgroup = group_name, subgroup_name
                break
        categories.setdefault(target_group, {}).setdefault(target_subgroup, []).append(
            {"name": display, "fn": function}
        )
        existing_names.add(display)
        existing_functions.add(function)
except Exception as exc:
    print(f"Bounds catalogue discovery warning: {exc}")


# -----------------------------------------------------------------------------
# Plot helpers
# -----------------------------------------------------------------------------
def clean_latex(figure: plt.Figure) -> None:
    """Make PlotFuncs labels compatible with browser Matplotlib/mathtext."""
    for text_object in figure.findobj(matplotlib.text.Text):
        text_object.set_usetex(False)
        text = text_object.get_text()
        if r"{\bf" in text:
            text_object.set_text(re.sub(r"\{\\bf\s+(.*?)\}", r"\1", text))
            text_object.set_weight("bold")


def prune_out_of_bounds_labels(axis: plt.Axes) -> None:
    try:
        x0, x1 = axis.get_xlim()
        y0, y1 = axis.get_ylim()
    except Exception:
        return
    for text_object in list(axis.texts):
        try:
            display_coordinates = text_object.get_transform().transform(text_object.get_position())
            x_data, y_data = axis.transData.inverted().transform(display_coordinates)
        except Exception:
            continue
        if x_data < x0 or x_data > x1 or y_data < y0 or y_data > y1:
            try:
                text_object.remove()
            except Exception:
                pass


def remove_new_figure_labels(figure: plt.Figure, previous: set[Any]) -> None:
    for text_object in list(figure.texts):
        if text_object not in previous:
            try:
                text_object.remove()
            except Exception:
                pass


def setup_axes(axis: plt.Axes, x_limits: tuple[float, float], y_limits: tuple[float, float]) -> None:
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlim(*x_limits)
    axis.set_ylim(*y_limits)
    axis.set_xlabel(r"$m_a$ [eV]", fontsize=18, labelpad=7)
    axis.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]", fontsize=18, labelpad=8)
    axis.tick_params(which="major", direction="in", width=1.3, length=7, labelsize=11, top=False, right=False)
    axis.tick_params(which="minor", direction="in", width=0.8, length=4, top=False, right=False)
    axis.grid(False)
    for spine in axis.spines.values():
        spine.set_linewidth(1.2)


# -----------------------------------------------------------------------------
# Equations section, rendered by Panel's native KaTeX model
# -----------------------------------------------------------------------------
def build_equations_section() -> pn.Column:
    rows: list[str] = []
    dash = {"KSVZ-like": "solid", "DFSZ-like": "dashed", "Strongly deviated": "dotted"}
    for index, model in enumerate(models):
        c_min, c_max = model["C"]
        coefficient = f"{c_min:+.2f}" if np.isclose(c_min, c_max) else f"{c_min:.2f} &hellip; {c_max:.2f}"
        category = model["category"]
        color = MODEL_PALETTE[index % len(MODEL_PALETTE)]
        rows.append(
            f"""
            <tr style="border-bottom:1px solid {LINE_SOFT};">
              <td style="padding:11px 8px;white-space:nowrap;">
                <span style="display:inline-block;width:27px;border-top:2.5px {dash[category]} {color};vertical-align:middle;margin-right:10px;"></span>
                <strong style="color:{NAVY_DEEP};">{model['display_name']}</strong>
              </td>
              <td style="padding:11px 8px;color:{MUTED};">{category}</td>
              <td style="padding:11px 8px;text-align:right;font-family:'IBM Plex Mono',monospace;color:{NAVY};">{coefficient}</td>
              <td style="padding:11px 8px;text-align:right;font-family:'IBM Plex Mono',monospace;color:{MUTED};">{model['Ndw']}</td>
            </tr>
            """
        )

    section_header = html(
        f"""
        <div id="models-equations" style="padding:20px 24px 17px;scroll-margin-top:18px;">
          <div class="axe-eyebrow">Methodology</div>
          <div style="font-family:'IBM Plex Serif',serif;font-size:23px;font-weight:600;color:{NAVY_DEEP};margin-top:7px;">Models &amp; equations</div>
          <p style="font-size:13px;color:{MUTED};line-height:1.55;max-width:820px;margin:8px 0 0;">
            Every model line is generated from the QCD axion&ndash;photon relation. The model-dependent anomaly
            coefficient sets the slope in the coupling plane; models quoting a range are drawn as filled bands.
          </p>
        </div>
        """
    )

    master_equation = pn.pane.LaTeX(
        r"$\displaystyle |g_{a\gamma}| = \frac{\alpha}{2\pi}\frac{|C_{a\gamma}|}{f_a} = \frac{\alpha}{2\pi}\frac{m_a}{\Lambda}\left|E/N-1.92\right|$",
        renderer="katex",
        styles={"font-size": "21px", "text-align": "center", "color": NAVY_DEEP},
        sizing_mode="stretch_width",
        margin=(3, 0, 9, 0),
    )

    constants = pn.Row(
        pn.Column(
            pn.pane.LaTeX(r"$C_{a\gamma}=E/N-1.92$", renderer="katex", styles={"font-size": "14px", "text-align": "center", "color": NAVY}),
            html('<div class="axe-equation-caption">model anomaly ratio</div>'),
            css_classes=["axe-equation-constant"],
        ),
        pn.Column(
            pn.pane.LaTeX(r"$\alpha=1/137.036$", renderer="katex", styles={"font-size": "14px", "text-align": "center", "color": NAVY}),
            html('<div class="axe-equation-caption">fine-structure constant</div>'),
            css_classes=["axe-equation-constant"],
        ),
        pn.Column(
            pn.pane.LaTeX(r"$\Lambda=5.70\times10^{6}$", renderer="katex", styles={"font-size": "14px", "text-align": "center", "color": NAVY}),
            html('<div class="axe-equation-caption">mass–coupling normalisation</div>'),
            css_classes=["axe-equation-constant"],
        ),
        sizing_mode="stretch_width",
        align="center",
        styles={"justify-content": "center", "gap": "28px", "flex-wrap": "wrap"},
    )

    equation_band = pn.Column(
        master_equation,
        constants,
        css_classes=["axe-equation-band"],
        styles={"padding": "27px 24px 29px"},
        sizing_mode="stretch_width",
    )

    table = html(
        f"""
        <div class="axe-table-wrap" style="padding:7px 24px 22px;">
          <table style="width:100%;border-collapse:collapse;font-size:12.5px;min-width:620px;">
            <thead>
              <tr style="font-family:'IBM Plex Mono',monospace;font-size:9.5px;color:{MUTED};text-transform:uppercase;letter-spacing:.06em;border-bottom:1.5px solid {LINE};">
                <th style="text-align:left;padding:12px 8px;">Model</th>
                <th style="text-align:left;padding:12px 8px;">Class</th>
                <th style="text-align:right;padding:12px 8px;">C<sub>aγ</sub></th>
                <th style="text-align:right;padding:12px 8px;">N<sub>DW</sub></th>
              </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </div>
        """
    )

    return pn.Column(
        section_header,
        equation_band,
        table,
        css_classes=["axe-equation-card"],
        styles={
            "background": CARD,
            "border": f"1px solid {LINE}",
            "border-radius": "13px",
            "box-shadow": "0 10px 30px rgba(16,34,51,.055)",
        },
        sizing_mode="stretch_width",
    )


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
def create_dashboard() -> tuple[pn.Column, pn.Column]:
    plt.rcParams.update(
        {
            "text.usetex": False,
            "font.family": "serif",
            "font.size": 11,
            "axes.grid": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    defaults = {"mmin": -8.0, "mmax": 2.0, "ymin": -16.0, "ymax": -8.0}
    suspended = [False]

    def make_slider(value: float, start: float, end: float) -> pn.widgets.FloatSlider:
        return pn.widgets.FloatSlider(
            name="",
            start=start,
            end=end,
            step=0.5,
            value=value,
            show_value=False,
            sizing_mode="stretch_width",
            height=28,
            margin=(0, 0, 0, 0),
            stylesheets=[SLIDER_SS],
        )

    mmin = make_slider(defaults["mmin"], -15, 12)
    mmax = make_slider(defaults["mmax"], -15, 12)
    ymin = make_slider(defaults["ymin"], -30, -5)
    ymax = make_slider(defaults["ymax"], -30, -5)

    mass_range_text = html("")
    coupling_range_text = html("")
    window_note = html("")

    def update_range_labels(*_: Any) -> None:
        mass_range_text.object = (
            f'<div class="axe-range-value">10<sup>{mmin.value:g}</sup> &ndash; 10<sup>{mmax.value:g}</sup> eV</div>'
        )
        coupling_range_text.object = (
            f'<div class="axe-range-value">10<sup>{ymin.value:g}</sup> &ndash; 10<sup>{ymax.value:g}</sup> GeV<sup>&minus;1</sup></div>'
        )
        window_note.object = (
            f'<div class="axe-window-note">window &middot; 10<sup>{mmin.value:g}</sup> &ndash; 10<sup>{mmax.value:g}</sup> eV '
            f'&times; 10<sup>{ymin.value:g}</sup> &ndash; 10<sup>{ymax.value:g}</sup> GeV<sup>&minus;1</sup></div>'
        )

    for slider in (mmin, mmax, ymin, ymax):
        slider.param.watch(update_range_labels, "value")
    update_range_labels()

    # QCD models: only eight controls, so render them immediately and in the
    # same single-list format as the visual reference.
    model_checks: dict[str, pn.widgets.Checkbox] = {}
    model_rows: list[pn.Row] = []
    line_style = {"KSVZ-like": "solid", "DFSZ-like": "dashed", "Strongly deviated": "dotted"}
    for index, model in enumerate(models):
        checkbox = pn.widgets.Checkbox(name="", value=True, width=23, height=25, margin=(0, 0, 0, 0), stylesheets=[CHECK_SS])
        model_checks[model["name"]] = checkbox
        c_min, c_max = model["C"]
        coefficient = f"{c_min:+.2f}" if np.isclose(c_min, c_max) else "band"
        color = MODEL_PALETTE[index % len(MODEL_PALETTE)]
        swatch = html(
            f'<span style="display:inline-block;width:28px;border-top:2.5px {line_style[model["category"]]} {color};vertical-align:middle;"></span>',
            width=34,
            height=24,
            sizing_mode="fixed",
        )
        row = pn.Row(
            checkbox,
            swatch,
            html(f'<div class="axe-model-name">{model["display_name"]}</div>'),
            pn.Spacer(),
            html(f'<div class="axe-model-coeff">{coefficient}</div>', width=50, height=24, sizing_mode="fixed"),
            css_classes=["axe-model-row"],
            sizing_mode="stretch_width",
            align="center",
            margin=0,
            styles={"padding": "5px 4px"},
        )
        model_rows.append(row)

    # Bound state exists independently of the widgets, allowing the very large
    # bounds catalogue to be constructed lazily only when the card is opened.
    bound_items: dict[str, dict[str, Any]] = {}
    bound_locations: dict[str, tuple[str, str]] = {}
    for group_name, subgroups in categories.items():
        for subgroup_name, items in subgroups.items():
            for item in items:
                bound_items[item["name"]] = item
                bound_locations[item["name"]] = (group_name, subgroup_name)

    bound_defaults = {name: bool(item.get("visible", False)) for name, item in bound_items.items()}
    bound_states = dict(bound_defaults)
    bound_checkboxes: dict[str, pn.widgets.Checkbox] = {}

    mpl_pane = pn.pane.Matplotlib(
        None,
        tight=False,
        dpi=115,
        high_dpi=False,
        format="png",
        sizing_mode="stretch_width",
        height=555,
        margin=0,
    )
    current_figure: list[plt.Figure | None] = [None]
    current_axis: list[plt.Axes | None] = [None]

    def update_plot(*_: Any) -> None:
        if suspended[0]:
            return
        if mmin.value >= mmax.value or ymin.value >= ymax.value:
            return

        if current_figure[0] is None or current_axis[0] is None:
            figure, axis = plt.subplots(figsize=(10.6, 6.35))
            current_figure[0] = figure
            current_axis[0] = axis
        else:
            figure = current_figure[0]
            axis = current_axis[0]
            axis.clear()

        plt.sca(axis)
        x_limits = (10 ** mmin.value, 10 ** mmax.value)
        y_limits = (10 ** ymin.value, 10 ** ymax.value)
        setup_axes(axis, x_limits, y_limits)
        figure.subplots_adjust(left=0.12, right=0.78, bottom=0.14, top=0.96)

        linestyle_map = {"KSVZ-like": "-", "DFSZ-like": "--", "Strongly deviated": ":"}
        linewidth_map = {"KSVZ-like": 1.9, "DFSZ-like": 1.9, "Strongly deviated": 2.0}
        mass_grid = np.logspace(np.log10(x_limits[0]), np.log10(x_limits[1]), 320)

        color_index = 0
        for category_index, category_name in enumerate(("KSVZ-like", "DFSZ-like", "Strongly deviated")):
            category_models = [model for model in models if model["category"] == category_name]
            if category_index:
                axis.plot([], [], " ", label="")
            axis.plot(
                [],
                [],
                linestyle=linestyle_map[category_name],
                color="black",
                linewidth=linewidth_map[category_name],
                label=category_name,
            )
            for model in category_models:
                if not model_checks[model["name"]].value:
                    continue
                color = MODEL_PALETTE[color_index % len(MODEL_PALETTE)]
                c_min, c_max = model["C"]
                if np.isclose(c_min, c_max):
                    axis.plot(
                        mass_grid,
                        g_agamma(mass_grid, c_min),
                        lw=linewidth_map[category_name],
                        alpha=0.92,
                        label=model["name"],
                        color=color,
                        linestyle=linestyle_map[category_name],
                    )
                else:
                    y_one = g_agamma(mass_grid, c_min)
                    y_two = g_agamma(mass_grid, c_max)
                    axis.fill_between(mass_grid, np.minimum(y_one, y_two), np.maximum(y_one, y_two), alpha=0.28, color=color)
                    axis.plot(
                        [],
                        [],
                        lw=linewidth_map[category_name] * 3,
                        alpha=0.5,
                        label=model["name"],
                        color=color,
                        linestyle=linestyle_map[category_name],
                    )
                color_index += 1

        def plot_bound(function: Any, kwargs: dict[str, Any]) -> None:
            old_x, old_y = axis.get_xlim(), axis.get_ylim()
            existing_figure_text = set(figure.texts)
            plt.sca(axis)
            try:
                try:
                    function(axis, **kwargs)
                except TypeError:
                    function(ax=axis, **kwargs)
            except Exception as exc:
                print(f"Could not draw bound {getattr(function, '__name__', function)}: {exc}")
            axis.set_xlim(old_x)
            axis.set_ylim(old_y)
            prune_out_of_bounds_labels(axis)
            remove_new_figure_labels(figure, existing_figure_text)

        for name, enabled in bound_states.items():
            if enabled:
                item = bound_items[name]
                plot_bound(item["fn"], item.get("kwargs", {}))

        legend = axis.legend(
            loc="upper left",
            bbox_to_anchor=(1.01, 1.0),
            fontsize=9.3,
            frameon=False,
            title="Theoretical Models",
            title_fontsize=10.2,
            borderaxespad=0,
            handlelength=2.2,
            labelspacing=0.35,
        )
        for text_object in legend.get_texts():
            if text_object.get_text() in {"KSVZ-like", "DFSZ-like", "Strongly deviated"}:
                text_object.set_fontweight("bold")
        clean_latex(figure)
        prune_out_of_bounds_labels(axis)

        if mpl_pane.object is None:
            mpl_pane.object = figure
        else:
            mpl_pane.param.trigger("object")

    def refresh_from_checkbox(event: Any) -> None:
        if not suspended[0]:
            update_plot()

    for checkbox in model_checks.values():
        checkbox.param.watch(refresh_from_checkbox, "value")

    for slider in (mmin, mmax, ymin, ymax):
        slider.param.watch(lambda event: update_plot(), "value_throttled")

    def set_models(state: bool) -> None:
        suspended[0] = True
        try:
            for checkbox in model_checks.values():
                checkbox.value = state
        finally:
            suspended[0] = False
        update_plot()

    all_models = pn.widgets.Button(name="ALL", width=38, height=24, button_type="light", stylesheets=[BTN_TINY_SS], margin=0)
    no_models = pn.widgets.Button(name="NONE", width=46, height=24, button_type="light", stylesheets=[BTN_TINY_SS], margin=0)
    all_models.on_click(lambda _: set_models(True))
    no_models.on_click(lambda _: set_models(False))

    model_card = pn.Column(
        pn.Row(
            pn.Column(
                html('<div class="axe-card-title">QCD axion models</div>'),
                html('<div class="axe-card-caption">Theoretical prediction lines &amp; bands.</div>'),
                margin=0,
            ),
            pn.Spacer(),
            all_models,
            no_models,
            sizing_mode="stretch_width",
            align="start",
            margin=0,
        ),
        *model_rows,
        styles={
            "background": CARD,
            "border": f"1px solid {LINE}",
            "border-radius": "11px",
            "box-shadow": "0 6px 18px rgba(16,34,51,.045)",
            "padding": "15px 13px 8px",
        },
        sizing_mode="stretch_width",
    )

    bounds_placeholder = pn.Column(
        html(f'<div style="font-size:11px;color:{MUTED};line-height:1.5;padding:3px 2px;">Open this card to load the full experimental-bounds catalogue.</div>'),
        sizing_mode="stretch_width",
    )
    limit_card = pn.Card(
        bounds_placeholder,
        title="Bounds and sensitivities",
        collapsed=True,
        css_classes=["modern-card"],
        sizing_mode="stretch_width",
    )
    bounds_built = [False]

    def set_bounds(names: list[str], state: bool) -> None:
        suspended[0] = True
        try:
            for name in names:
                bound_states[name] = state
                checkbox = bound_checkboxes.get(name)
                if checkbox is not None:
                    checkbox.value = state
        finally:
            suspended[0] = False
        update_plot()

    def build_bounds_catalogue() -> None:
        if bounds_built[0]:
            return
        outer = pn.Accordion(toggle=True, css_classes=["modern-accordion"], sizing_mode="stretch_width")
        for group_name, subgroups in categories.items():
            inner = pn.Accordion(toggle=True, css_classes=["modern-accordion", "subgroup-accordion"], sizing_mode="stretch_width")
            for subgroup_name, items in subgroups.items():
                if not items:
                    continue
                subgroup_names = [item["name"] for item in items]
                checks: list[pn.widgets.Checkbox] = []
                for item in items:
                    name = item["name"]
                    checkbox = pn.widgets.Checkbox(name=name, value=bound_states[name], stylesheets=[CHECK_SS], margin=(1, 0))
                    bound_checkboxes[name] = checkbox

                    def on_change(event: Any, bound_name: str = name) -> None:
                        bound_states[bound_name] = bool(event.new)
                        if not suspended[0]:
                            update_plot()

                    checkbox.param.watch(on_change, "value")
                    checks.append(checkbox)

                select_all = pn.widgets.Button(name="All", button_type="light", height=25, stylesheets=[BTN_TINY_SS])
                clear_all = pn.widgets.Button(name="Clear", button_type="light", height=25, stylesheets=[BTN_TINY_SS])
                select_all.on_click(lambda _, names=subgroup_names: set_bounds(names, True))
                clear_all.on_click(lambda _, names=subgroup_names: set_bounds(names, False))
                subgroup_panel = pn.Column(
                    pn.Column(*checks, height=140, scroll=True, sizing_mode="stretch_width"),
                    pn.Row(select_all, clear_all, sizing_mode="stretch_width"),
                    sizing_mode="stretch_width",
                )
                inner.append((subgroup_name, subgroup_panel))
            if len(inner):
                outer.append((group_name, inner))
        bounds_placeholder.objects = [outer]
        bounds_built[0] = True

    def on_bounds_card(event: Any) -> None:
        if event.new is False:
            build_bounds_catalogue()

    limit_card.param.watch(on_bounds_card, "collapsed")

    # Compact plot-window card matching the reference rather than four visible
    # native widget labels.
    def slider_row(side_label: str, widget: pn.widgets.FloatSlider) -> pn.Row:
        return pn.Row(
            html(f'<div class="axe-slider-side">{side_label}</div>', width=31, height=24, sizing_mode="fixed"),
            widget,
            sizing_mode="stretch_width",
            align="center",
            margin=(0, 0, 2, 0),
        )

    range_card = pn.Column(
        html('<div class="axe-card-title">Plot window</div>'),
        html('<div class="axe-card-caption">Log-scale axis limits, applied before bounds are drawn.</div>'),
        pn.Row(
            html(r'<div class="axe-range-label">Axion mass <i>m</i><sub>a</sub></div>'),
            pn.Spacer(),
            mass_range_text,
            sizing_mode="stretch_width",
            align="center",
            margin=(11, 0, 2, 0),
        ),
        slider_row("min", mmin),
        slider_row("max", mmax),
        pn.layout.Divider(margin=(7, 0, 8, 0)),
        pn.Row(
            html(r'<div class="axe-range-label">Coupling |<i>g</i><sub>aγ</sub>|</div>'),
            pn.Spacer(),
            coupling_range_text,
            sizing_mode="stretch_width",
            align="center",
            margin=(0, 0, 2, 0),
        ),
        slider_row("min", ymin),
        slider_row("max", ymax),
        styles={
            "background": CARD,
            "border": f"1px solid {LINE}",
            "border-radius": "11px",
            "box-shadow": "0 6px 18px rgba(16,34,51,.045)",
            "padding": "15px",
        },
        sizing_mode="stretch_width",
    )

    reset_button = pn.widgets.Button(name="RESET", width=58, height=27, button_type="light", stylesheets=[BTN_TINY_SS], margin=0)

    def reset_dashboard(_: Any = None) -> None:
        suspended[0] = True
        try:
            mmin.value = defaults["mmin"]
            mmax.value = defaults["mmax"]
            ymin.value = defaults["ymin"]
            ymax.value = defaults["ymax"]
            for checkbox in model_checks.values():
                checkbox.value = True
            for name, value in bound_defaults.items():
                bound_states[name] = value
                checkbox = bound_checkboxes.get(name)
                if checkbox is not None:
                    checkbox.value = value
        finally:
            suspended[0] = False
        update_range_labels()
        update_plot()

    reset_button.on_click(reset_dashboard)

    controls_header = pn.Row(
        pn.Column(
            html(f'<div style="font-family:\'IBM Plex Serif\',serif;font-size:15px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{NAVY_DEEP};">Controls</div>'),
            html(f'<div style="font-size:11.5px;color:{MUTED};line-height:1.45;margin-top:5px;">Set the visible parameter window and the layers drawn on the plot.</div>'),
            margin=0,
        ),
        pn.Spacer(),
        reset_button,
        sizing_mode="stretch_width",
        align="start",
        margin=(0, 0, 2, 0),
    )

    sidebar = pn.Column(
        controls_header,
        range_card,
        model_card,
        limit_card,
        css_classes=["axe-sidebar"],
        width=330,
        min_width=300,
        margin=(0, 18, 0, 0),
        styles={
            "position": "sticky",
            "top": "12px",
            "max-height": "calc(100vh - 24px)",
            "overflow-y": "auto",
            "padding": "4px 5px 18px 1px",
        },
    )

    # Downloads and plot-card actions.
    def download_figure(file_format: str) -> io.BytesIO | None:
        if current_figure[0] is None:
            return None
        buffer = io.BytesIO()
        current_figure[0].savefig(buffer, format=file_format, bbox_inches="tight", dpi=170 if file_format == "png" else None)
        buffer.seek(0)
        return buffer

    share_button = pn.widgets.Button(name="Share", width=66, height=35, button_type="light", stylesheets=[BTN_LIGHT_SS])

    def share_link(_: Any) -> None:
        if "pyodide" not in sys.modules:
            return
        try:
            from js import navigator, window  # type: ignore

            navigator.clipboard.writeText(window.location.href)
            share_button.name = "Copied"
        except Exception as exc:
            print(f"Could not copy link: {exc}")

    share_button.on_click(share_link)
    png_button = pn.widgets.FileDownload(
        callback=lambda: download_figure("png"),
        filename="AxionLimits.png",
        label="PNG",
        width=58,
        height=35,
        stylesheets=[BTN_LIGHT_SS],
    )
    pdf_button = pn.widgets.FileDownload(
        callback=lambda: download_figure("pdf"),
        filename="AxionLimits.pdf",
        label="Export PDF",
        width=106,
        height=35,
        stylesheets=[BTN_EXPORT_SS],
    )

    plot_title = pn.Column(
        html('<div class="axe-plot-title">Axion–photon coupling plane</div>'),
        html('<div class="axe-plot-subtitle">Exclusion regions &amp; QCD model predictions in (<i>m</i><sub>a</sub>, |<i>g</i><sub>aγ</sub>|)</div>'),
        margin=0,
    )
    plot_header = pn.Row(
        plot_title,
        pn.Spacer(),
        share_button,
        png_button,
        pdf_button,
        sizing_mode="stretch_width",
        align="center",
        margin=0,
        styles={"padding": "4px 0 14px"},
    )

    plot_stage = pn.Column(
        html('<div class="axe-live-badge">Live figure</div>'),
        mpl_pane,
        css_classes=["axe-plot-stage"],
        sizing_mode="stretch_width",
        margin=0,
        styles={"position": "relative", "background": "#fff"},
    )
    plot_footer = pn.Row(
        window_note,
        pn.Spacer(),
        html('<div class="axe-plot-note">Shaded = experimental exclusion &nbsp;&middot;&nbsp; Lines/bands = model predictions</div>'),
        sizing_mode="stretch_width",
        align="center",
        margin=(12, 0, 0, 0),
        styles={"border-top": f"1px solid {LINE_SOFT}", "padding-top": "12px"},
    )

    plot_card = pn.Column(
        plot_header,
        plot_stage,
        plot_footer,
        styles={
            "background": CARD,
            "border": f"1px solid {LINE}",
            "border-radius": "13px",
            "box-shadow": "0 13px 38px rgba(16,34,51,.075)",
            "padding": "15px 20px 14px",
        },
        sizing_mode="stretch_width",
    )

    update_plot()
    main = pn.Column(plot_card, pn.Spacer(height=18), build_equations_section(), sizing_mode="stretch_width", min_width=700)
    return sidebar, main


# -----------------------------------------------------------------------------
# Page chrome
# -----------------------------------------------------------------------------
HEADER_HTML = f"""
<header style="background:#fff;border-bottom:1px solid {LINE};">
  <div style="max-width:1540px;margin:0 auto;padding:13px 28px;display:flex;align-items:center;gap:20px;box-sizing:border-box;">
    <div style="display:flex;align-items:center;gap:16px;min-width:0;">
      <img src="{ORGANIZATION_LOGO}" alt="COSMIC WISPers" style="height:52px;width:auto;object-fit:contain;">
      <div style="border-left:1px solid {LINE};padding-left:17px;min-width:0;">
        <div style="font-family:'IBM Plex Serif',serif;font-weight:600;font-size:22px;letter-spacing:-.015em;color:{NAVY_DEEP};line-height:1.15;white-space:nowrap;">Axion–Photon Coupling Explorer</div>
        <div style="font-size:11.5px;color:{MUTED};margin-top:3px;">COSMIC WISPers · COST Action <span style="font-family:'IBM Plex Mono',monospace;color:{STEEL};">CA21106</span></div>
      </div>
    </div>
    <div style="flex:1;"></div>
    <nav style="display:flex;align-items:center;gap:8px;white-space:nowrap;">
      <a href="https://cosmicwispers.eu/" target="_blank" rel="noopener" style="text-decoration:none;font-size:12px;font-weight:600;color:{NAVY};padding:9px 13px;border-radius:7px;border:1px solid {LINE};">Consortium</a>
      <a href="#models-equations" style="text-decoration:none;font-size:12px;font-weight:600;color:{NAVY};padding:9px 13px;border-radius:7px;border:1px solid {LINE};">Models &amp; Equations</a>
      <a href="https://github.com/francandon/AxionModelsLimits" target="_blank" rel="noopener" style="text-decoration:none;font-size:12px;font-weight:700;color:#fff;background:{NAVY};padding:9px 15px;border-radius:7px;">GitHub</a>
    </nav>
  </div>
</header>
"""

FOOTER_HTML = f"""
<footer style="background:{NAVY_DEEP};color:#c7d2e0;margin-top:30px;">
  <div style="max-width:1540px;margin:0 auto;padding:32px 28px 17px;display:grid;grid-template-columns:1.5fr 1fr 1.2fr;gap:34px;box-sizing:border-box;">
    <div>
      <div style="display:flex;align-items:center;gap:13px;margin-bottom:13px;">
        <img src="{ORGANIZATION_LOGO}" alt="" style="height:44px;width:auto;">
        <div style="font-family:'IBM Plex Serif',serif;font-size:15px;font-weight:600;color:#fff;line-height:1.2;">COSMIC WISPers<br><span style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;font-weight:400;color:#8ea3bd;">CA21106</span></div>
      </div>
      <p style="font-size:12px;line-height:1.6;color:#9fb1c8;margin:0;max-width:390px;">Funded by the European Cooperation in Science and Technology (COST). This explorer renders axion–photon constraints and theoretical model predictions for the WISP community.</p>
    </div>
    <div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;color:#8ea3bd;letter-spacing:.1em;text-transform:uppercase;margin-bottom:11px;">Authors</div>
      <div style="font-size:12.5px;line-height:1.9;color:#cdd9e7;">Francisco Rodríguez Candón<br>Francesca Lecce<br>Philip Sørensen</div>
    </div>
    <div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;color:#8ea3bd;letter-spacing:.1em;text-transform:uppercase;margin-bottom:11px;">How to cite</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.65;color:#9fb1c8;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:11px 12px;">Rodríguez Candón, Lecce &amp; Sørensen (2025), <span style="color:#dfe8f2;">Axion–Photon Coupling Explorer</span>. Limit data adapted from C. O’Hare, AxionLimits.</div>
    </div>
  </div>
  <div style="border-top:1px solid rgba(255,255,255,.08);">
    <div style="max-width:1540px;margin:0 auto;padding:12px 28px;font-size:10.5px;color:#7d90a8;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;box-sizing:border-box;">
      <span>© 2025 COSMIC WISPers Consortium</span>
      <span style="font-family:'IBM Plex Mono',monospace;">More model details in the WISP dictionary.</span>
    </div>
  </div>
</footer>
"""

sidebar, main = create_dashboard()
body = pn.Row(
    sidebar,
    main,
    css_classes=["axe-page", "axe-body"],
    sizing_mode="stretch_width",
    styles={"padding": "24px 28px 8px", "align-items": "flex-start", "box-sizing": "border-box"},
)

page = pn.Column(
    html(HEADER_HTML),
    body,
    html(FOOTER_HTML),
    sizing_mode="stretch_width",
    styles={"background": PAPER, "min-height": "100vh"},
    margin=0,
)
page.servable(title="Axion Limits Explorer")
