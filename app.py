import panel as pn
import sys
import os

# 1. Initialize Panel (No ipywidgets dependency!)
pn.extension('mathjax', sizing_mode="stretch_width")

# --- WEB BROWSER DATA LOADING ---
if 'pyodide' in sys.modules:
    from pyodide.http import open_url
    import zipfile
    import io
    
    # Check if data exists, if not download
    if not os.path.exists('./PlotFuncs.py'):
        print("Downloading assets...")
        try:
            zip_data = open_url('./assets.zip').read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                z.extractall('.')
            print("Assets extracted.")
        except Exception as e:
            print(f"Failed to load assets: {e}")

# --- IMPORTS ---
import matplotlib.pyplot as plt
import numpy as np
# Note: We do NOT import ipywidgets. We use Panel widgets.

# Safely import PlotFuncs
try:
    from PlotFuncs import FigSetup, AxionPhoton
except ImportError:
    print("PlotFuncs not found. Plotting will fail until assets are loaded.")

# --- PHYSICS ---
alpha = 1/137.035999084
K = 5.70e6
pref = alpha/(2*np.pi)

def g_agamma(m_eV, C):
    return np.abs(pref * C * (m_eV / K))

# Data definitions
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

# --- DASHBOARD LOGIC ---
def create_dashboard():
    # 1. Static Matplotlib Backend (Fastest & Safest for Web)
    plt.switch_backend('agg') 
    
    # 2. Widgets (Pure Panel - No ipywidgets)
    # We use Exponent sliders: Value -12 means 10^-12
    mmin = pn.widgets.FloatSlider(name='Min Mass (10^x eV)', start=-15, end=8, step=0.5, value=-12)
    mmax = pn.widgets.FloatSlider(name='Max Mass (10^x eV)', start=-15, end=8, step=0.5, value=-1)
    ymin = pn.widgets.FloatSlider(name='Min Coupling (10^x)', start=-30, end=-5, step=0.5, value=-20)
    ymax = pn.widgets.FloatSlider(name='Max Coupling (10^x)', start=-30, end=-5, step=0.5, value=-8)

    save_btn = pn.widgets.Button(name='Download PDF', button_type='success')
    
    # Model Checks
    model_checks = {m["name"]: pn.widgets.Checkbox(name=m["name"], value=True) for m in models}
    
    # Buttons for Models
    sel_all_mod = pn.widgets.Button(name='Select All')
    sel_no_mod  = pn.widgets.Button(name='Select None')

    def update_models(event, state):
        for chk in model_checks.values(): chk.value = state
    sel_all_mod.on_click(lambda e: update_models(e, True))
    sel_no_mod.on_click(lambda e: update_models(e, False))

    # Category Checks
    cat_widgets = {}
    tabs = pn.Tabs(("Models", pn.Column(pn.Column(*model_checks.values(), height=300, scroll=True), pn.Row(sel_all_mod, sel_no_mod))))

    for cat_name, items in categories.items():
        checks = {it["name"]: pn.widgets.Checkbox(name=it["name"], value=it.get("visible", False)) for it in items}
        
        b_all = pn.widgets.Button(name='All')
        b_no  = pn.widgets.Button(name='None')
        
        # Closure to capture specific checks
        def make_callback(c_dict, state):
            return lambda e: [setattr(w, 'value', state) for w in c_dict.values()]
            
        b_all.on_click(make_callback(checks, True))
        b_no.on_click(make_callback(checks, False))
        
        # Save ref to items for plotting
        cat_widgets[cat_name] = {"checks": checks, "items": items}
        
        tabs.append((cat_name, pn.Column(pn.Column(*checks.values(), height=300, scroll=True), pn.Row(b_all, b_no))))

    # 3. The Plotting Function
    # We use a Matplotlib Pane which auto-updates when we return a new fig
    mpl_pane = pn.pane.Matplotlib(tight=True, dpi=140, format='png')

    def update_plot(*events):
        plt.close('all')
        # Create figure
        fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\gamma}|$ [GeV$^{-1}$]', mathpazo=False)
        
        # Convert Exponents to Values
        xlims = (10**mmin.value, 10**mmax.value)
        ylims = (10**ymin.value, 10**ymax.value)
        
        ax.set_xlim(*xlims)
        ax.set_ylim(*ylims)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel(r"$m_a$ [eV]")
        ax.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]")

        # Plot Models
        m_grid = np.logspace(np.log10(xlims[0]), np.log10(xlims[1]), 500)
        for m in models:
            if model_checks[m["name"]].value:
                cmin, cmax = m["C"]
                ndw = m.get("Ndw", "—")
                if np.isclose(cmin, cmax):
                    yy = g_agamma(m_grid, cmin)
                    ax.plot(m_grid, yy, lw=2, alpha=0.95, label=rf"{m['name']}")
                else:
                    y1 = g_agamma(m_grid, cmin); y2 = g_agamma(m_grid, cmax)
                    ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
                    ax.fill_between(m_grid, ylo, yhi, alpha=0.25)
                    ax.plot(m_grid, np.sqrt(ylo*yhi), lw=1.5, alpha=0.85, label=rf"{m['name']}")

        # Plot Bounds (Helper)
        def _plot_bound(fn, kw):
            # Hack: Save/Restore limits because some bounds auto-scale
            old_x = ax.get_xlim(); old_y = ax.get_ylim()
            try:
                try: fn(ax, **kw)
                except TypeError: fn(ax=ax, **kw)
            except Exception: pass
            ax.set_xlim(old_x); ax.set_ylim(old_y)

        for cat in cat_widgets.values():
            for it in cat["items"]:
                if cat["checks"][it["name"]].value:
                    _plot_bound(it["fn"], it.get("kwargs", {}))

        ax.grid(True, which='both', ls=':', alpha=0.4)
        ax.legend(loc='lower right', fontsize=8, frameon=False)
        ax.set_title("Axion–Photon Coupling vs Mass")
        
        mpl_pane.object = fig
        return mpl_pane

    # 4. Bind Widgets to Update Function
    # Collect all widgets to watch
    watch_list = [mmin, mmax, ymin, ymax] 
    watch_list += list(model_checks.values())
    for c in cat_widgets.values():
        watch_list += list(c["checks"].values())

    # Trigger update when any widget changes
    pn.bind(update_plot, *watch_list, watch=True)

    # Save Button Logic
    def save_callback(event):
        mpl_pane.object.savefig("AxionLimits.pdf")
        mpl_pane.object.savefig("AxionLimits.png")
        # Note: In browser, this saves to virtual FS. Downloading from button is tricky in pure Panel-WASM without JS.
        # But the plot is generated.
    save_btn.on_click(save_callback)

    # Initial Draw
    update_plot()

    # Layout
    controls = pn.Column(mmin, mmax, ymin, ymax, save_btn, width=320)
    return pn.Row(pn.Column(tabs, controls), mpl_pane)


# --- TEMPLATE ---
template = pn.template.MaterialTemplate(
    title="Axion Limits Explorer",
    main=[create_dashboard()],
)
template.servable()