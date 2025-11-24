import panel as pn
import sys
import os

# 1. Initialize Panel
pn.extension('ipywidgets', 'mathjax', sizing_mode="stretch_width")

# --- WEB BROWSER DATA LOADING (Pyodide specific) ---
if 'pyodide' in sys.modules:
    import pyodide_http
    pyodide_http.patch_all() 
    import requests
    import zipfile
    import io
    
    # Only download if not already extracted
    if not os.path.exists('./PlotFuncs.py'):
        print("Downloading assets...")
        # 'assets.zip' must be in the same folder as index.html on the website
        response = requests.get('./assets.zip')
        
        if response.status_code == 200:
            print("Extracting assets...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall('.')
        else:
            print(f"Failed to load assets.zip (Status: {response.status_code})")

# --- IMPORTS ---
import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import display, clear_output

# Import your custom library
# Ensure PlotFuncs.py and limit_data/ are in the same folder (or extracted there)
try:
    from PlotFuncs import FigSetup, AxionPhoton, MySaveFig, BlackHoleSpins, FilledLimit
except ImportError:
    # Fallback/Error handling if file not found locally during convert
    print("Warning: PlotFuncs not found. This might crash unless running in browser with assets.zip.")
    pass

# --- PHYSICS CONSTANTS ---
alpha = 1/137.035999084
K = 5.70e6
pref = alpha/(2*np.pi)

def g_agamma(m_eV, C):
    return np.abs(pref * C * (m_eV / K))

models = [
    {"name": "KSVZ", "Ndw": "1", "C": (-1.92, -1.92)},
    {"name": "DFSZ-I", "Ndw": "6,3", "C": (0.75, 0.75)},
    {"name": "DFSZ-II", "Ndw": "6,3", "C": (-1.25, -1.25)},
    {"name": "Astrophobic QCD axion", "Ndw": "1,2", "C": (-6.59, 0.74)},
    {"name": r"VISH$\nu$", "Ndw": "1", "C": (0.75, 0.75)},
    {"name": r"$\nu$DFSZ", "Ndw": "6", "C": (0.75, 0.75)},
    {"name": "Majoraxion", "Ndw": "—", "C": (2.66, 2.66)},
    {"name": "Composite Axion", "Ndw": "0/2/6", "C": (1.33, 2.66)},
]

categories = {
    "Astrophysical Bounds": [
        {"name": "Helioscopes",     "fn": AxionPhoton.Helioscopes, "visible": True},
        {"name": "White Dwarfs",   "fn": AxionPhoton.WhiteDwarfs},
        {"name": "Stellar Bounds", "fn": AxionPhoton.StellarBounds}

    ],
    "Experimental Bounds": [
        {"name": "Haloscopes",  "fn": AxionPhoton.Haloscopes},
        {"name": "Solar Basin",  "fn": AxionPhoton.SolarBasin},
        {"name": "StAB",         "fn": AxionPhoton.StAB}
    ],
    "Test QCD" : [
        {"name": "QCD Axion",    "fn": AxionPhoton.QCDAxion}
    ],
}

# --- DASHBOARD CREATION FUNCTION ---
def create_dashboard():
    # 1. Setup Figure
    plt.close('all')
    # We use mathpazo=False to avoid font issues in browser unless fonts are loaded
    fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\gamma}|$ [GeV$^{-1}$]', mathpazo=False)
    
    # 2. Define Helper Functions
    def html_label(html, width="160px"):
        lab = widgets.HTML(value=html)
        lab.layout.width = width
        return lab

    mmin_label = html_label("m<sub>a</sub><sup>min</sup> [eV]")
    mmax_label = html_label("m<sub>a</sub><sup>max</sup> [eV]")
    ymin_label = html_label("g<sub>aγ</sub><sup>min</sup>")
    ymax_label = html_label("g<sub>aγ</sub><sup>max</sup>")

    # 3. Define Widgets
    mmin = widgets.FloatLogSlider(value=1e-12, base=10, min=-15, max=8, step=0.1, readout_format=".1e")
    mmax = widgets.FloatLogSlider(value=1e-1,  base=10, min=-15, max=8, step=0.1, readout_format=".1e")
    ymin = widgets.FloatLogSlider(value=1e-20, base=10, min=-30, max=-5, step=0.1, readout_format=".1e")
    ymax = widgets.FloatLogSlider(value=1e-8,  base=10, min=-30, max=-5, step=0.1, readout_format=".1e")

    mmin_box = widgets.HBox([mmin_label, mmin])
    mmax_box = widgets.HBox([mmax_label, mmax])
    ymin_box = widgets.HBox([ymin_label, ymin])
    ymax_box = widgets.HBox([ymax_label, ymax])

    mmin.layout.width = mmax.layout.width = ymin.layout.width = ymax.layout.width = "260px"
    
    # 4. Tab 0: Models
    model_checks = [widgets.Checkbox(value=True, description=m["name"]) for m in models]
    sel_all_models  = widgets.Button(description='Seleccionar todo')
    sel_none_models = widgets.Button(description='Deseleccionar todo')

    modelos_panel = widgets.VBox([
        widgets.VBox(model_checks, layout=widgets.Layout(min_width='260px', max_height='350px', overflow='auto')),
        widgets.HBox([sel_all_models, sel_none_models]),
    ])

    tabs_children = [modelos_panel]
    tab_titles = ['Modelos']
    cat_checkgroups = {}

    if categories:
        for tab_name, items in categories.items():
            checks = [widgets.Checkbox(value=bool(it.get("visible", False)), description=it["name"]) for it in items]
            sel_all_btn  = widgets.Button(description='Seleccionar todo')
            sel_none_btn = widgets.Button(description='Deseleccionar todo')

            panel = widgets.VBox([
                widgets.VBox(checks, layout=widgets.Layout(min_width='260px', max_height='350px', overflow='auto')),
                widgets.HBox([sel_all_btn, sel_none_btn]),
            ])

            tabs_children.append(panel)
            tab_titles.append(tab_name)
            cat_checkgroups[tab_name] = {"checks": checks, "items": items,
                                        "sel_all": sel_all_btn, "sel_none": sel_none_btn}

    tabs = widgets.Tab(children=tabs_children)
    for i, t in enumerate(tab_titles):
        tabs.set_title(i, t)

    # 5. Right Panel & UI Assembly
    save_btn = widgets.Button(description='Guardar figura', button_style='success')
    right = widgets.VBox([mmin_box, mmax_box, ymin_box, ymax_box, save_btn])
    
    # --- HERE IS THE DEFINITION OF UI ---
    ui = widgets.HBox([tabs, right])

    # 6. Output Widget (The Plot)
    out = widgets.Output()

    # 7. Redraw Logic
    def redraw(*_):
        # We must clear the axis and redraw everything
        ax.cla()
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel(r"$m_a$ [eV]")
        ax.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]")
        
        xlims = (mmin.value, mmax.value)
        ylims = (ymin.value, ymax.value)
        ax.set_xlim(*xlims); ax.set_ylim(*ylims)

        # -- Models --
        m_grid = np.logspace(np.log10(xlims[0]), np.log10(xlims[1]), 600)
        for chk, md in zip(model_checks, models):
            if not chk.value: continue
            cmin, cmax = md["C"]
            ndw = md.get("Ndw", "—")
            if np.isclose(cmin, cmax):
                yy = g_agamma(m_grid, cmin)
                ax.plot(m_grid, yy, lw=2, alpha=0.95, label=rf"{md['name']} ($N_{{\rm dw}}$={ndw})")
            else:
                y1 = g_agamma(m_grid, cmin); y2 = g_agamma(m_grid, cmax)
                ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
                ax.fill_between(m_grid, ylo, yhi, alpha=0.25)
                ax.plot(m_grid, np.sqrt(ylo*yhi), lw=1.5, alpha=0.85, label=rf"{md['name']} ($N_{{\rm dw}}$={ndw})")

        # -- Bounds helper --
        def _call_on_ax(name, fn, ax, kwargs):
            # Safe wrapper to call PlotFuncs on our specific axis
            xlim = ax.get_xlim(); ylim = ax.get_ylim()
            was_auto = ax.get_autoscale_on(); ax.set_autoscale_on(False)
            try:
                try: fn(ax, **(kwargs or {}))
                except TypeError: fn(ax=ax, **(kwargs or {}))
            except Exception as e:
                print(f"Error plotting {name}: {e}")
            finally:
                ax.set_xlim(xlim); ax.set_ylim(ylim); ax.set_autoscale_on(was_auto)

        # -- Plot Bounds --
        if categories:
            for tab_name, grp in cat_checkgroups.items():
                for chk, it in zip(grp["checks"], grp["items"]):
                    if chk.value:
                        _call_on_ax(it["name"], it["fn"], ax, it.get("kwargs", {}))

        # Cosmetics
        ax.grid(True, which='both', ls=':', alpha=0.4)
        ax.legend(loc='lower right', fontsize=9, frameon=False)
        ax.set_title("Axion–Photon Coupling vs Mass", pad=8)

        # Force Update in the Output Widget
        with out:
            clear_output(wait=True)
            display(fig)

    # 8. Event Handlers
    def on_save(_):
        # Saving in browser downloads the file to the browser's download folder
        fig.savefig("AxionPhoton_Dashboard.pdf", bbox_inches='tight')
        fig.savefig("AxionPhoton_Dashboard.png", dpi=300, bbox_inches='tight')
    
    save_btn.on_click(on_save)

    sel_all_models.on_click(lambda _: [setattr(c, "value", True)  for c in model_checks])
    sel_none_models.on_click(lambda _: [setattr(c, "value", False) for c in model_checks])
    
    for grp in cat_checkgroups.values():
        grp["sel_all"].on_click(lambda _, g=grp: [setattr(c, "value", True)  for c in g["checks"]])
        grp["sel_none"].on_click(lambda _, g=grp: [setattr(c, "value", False) for c in g["checks"]])

    for w in (mmin, mmax, ymin, ymax): w.observe(redraw, names='value')
    for chk in model_checks: chk.observe(redraw, names='value')
    for grp in cat_checkgroups.values():
        for chk in grp["checks"]: chk.observe(redraw, names='value')

    # Initial Draw
    redraw()

    # 9. Return the combined layout (Controls + Plot)
    # We stack them vertically so the plot appears below the controls
    return widgets.VBox([ui, out])

# --- TEMPLATE SETUP ---
intro_text = """
# Axion Limits
Interactive dashboard for Axion-Photon coupling.
Select models and bounds to visualize.
"""

template = pn.template.MaterialTemplate(
    title="Axion Limits Explorer",
    sidebar=[intro_text],
    main=[pn.panel(create_dashboard(), sizing_mode="scale_width")],
)

template.servable()