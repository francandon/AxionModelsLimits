import panel as pn
import sys
import os
import re
import io

# 1. Initialize Panel
pn.extension('mathjax', sizing_mode="stretch_width")

# --- WEB BROWSER DATA LOADING ---
if 'pyodide' in sys.modules:
    import pyodide_http
    pyodide_http.patch_all() 
    import requests
    import zipfile
    from js import window, URL

    if not os.path.exists('./PlotFuncs.py'):
        print("Downloading assets...")
        try:
            base_url = window.location.href
            assets_url = URL.new('./assets.zip', base_url).href
            response = requests.get(assets_url)
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    z.extractall('.')
                print("Assets extracted.")
        except Exception as e:
            print(f"Asset load failed: {e}")

# --- IMPORTS ---
import matplotlib.pyplot as plt
import matplotlib.text
import numpy as np

# Safety import
try:
    from PlotFuncs import FigSetup, AxionPhoton
except ImportError:
    def AxionPhoton(*args): pass
    def FigSetup(*args, **kwargs): return plt.subplots()

# --- PHYSICS ---
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
        {"name": "White Dwarfs",   "fn": AxionPhoton.WhiteDwarfs},
        {"name": "Stellar Bounds", "fn": AxionPhoton.StellarBounds}
    ],
    "Experimental Bounds": [
        {"name": "Helioscopes",     "fn": AxionPhoton.Helioscopes, "visible": True},
        {"name": "Haloscopes",  "fn": AxionPhoton.Haloscopes},
        {"name": "Solar Basin",  "fn": AxionPhoton.SolarBasin},
        {"name": "StAB",         "fn": AxionPhoton.StAB}
    ],
    #"Test QCD" : [
    #    {"name": "QCD Axion",    "fn": AxionPhoton.QCDAxion}
    #],
}

# --- TEXT CLEANER (Fixes the {\bf ...} issue) ---
def clean_latex(fig):
    """
    Finds text objects containing incompatible LaTeX (like {\bf ...})
    and converts them to standard Matplotlib bold/math.
    """
    for text_obj in fig.findobj(matplotlib.text.Text):
        s = text_obj.get_text()
        
        # 1. Force Disable TeX for this object
        text_obj.set_usetex(False)
        
        # 2. Fix {\bf TEXT} -> TEXT (and make it bold)
        if r"{\bf" in s:
            # Extract text inside {\bf ...}
            s_clean = re.sub(r'\{\\bf\s+(.*?)\}', r'\1', s)
            text_obj.set_text(s_clean)
            text_obj.set_weight('bold')
        
        # 3. Fix simple LaTeX that Matplotlib understands
        # Matplotlib needs raw strings for math, e.g. $\nu$ is fine, but \nu might fail outside math mode
        # This is a heuristic cleanup
        if "\\" in s and "$" not in s:
            # If it looks like a greek letter but isn't wrapped in $, wrap it
            if any(x in s for x in ['nu', 'alpha', 'gamma', 'rho']):
                # Attempt to wrap the whole string in math mode if it looks like pure math
                pass 

# --- DASHBOARD LOGIC ---
def create_dashboard():
    plt.switch_backend('agg') 
    plt.style.use('default')
    plt.rcParams['text.usetex'] = False
    plt.rcParams['font.family'] = 'serif'
    
    # 1. Widgets
    # We bind to 'value_throttled' later to make it fluid
    mmin = pn.widgets.FloatSlider(name='Min Mass (10^x eV)', start=-15, end=8, step=0.5, value=-12)
    mmax = pn.widgets.FloatSlider(name='Max Mass (10^x eV)', start=-15, end=8, step=0.5, value=-1)
    ymin = pn.widgets.FloatSlider(name='Min Coupling (10^x)', start=-30, end=-5, step=0.5, value=-20)
    ymax = pn.widgets.FloatSlider(name='Max Coupling (10^x)', start=-30, end=-5, step=0.5, value=-8)

    # 2. File Download Widget (Replaces Button)
    download_btn = pn.widgets.FileDownload(
        filename="AxionLimits.pdf", 
        button_type="success", 
        label="Download PDF", 
        height=40
    )

    # 3. Model & Category Selectors
    model_checks = {m["name"]: pn.widgets.Checkbox(name=m["name"], value=True) for m in models}
    
    sel_all_mod = pn.widgets.Button(name='Select All')
    sel_no_mod  = pn.widgets.Button(name='Select None')
    
    def update_models(event, state):
        for chk in model_checks.values(): chk.value = state
    sel_all_mod.on_click(lambda e: update_models(e, True))
    sel_no_mod.on_click(lambda e: update_models(e, False))

    cat_widgets = {}
    tabs = pn.Tabs(("Models", pn.Column(pn.Column(*model_checks.values(), height=300, scroll=True), pn.Row(sel_all_mod, sel_no_mod))))

    for cat_name, items in categories.items():
        checks = {it["name"]: pn.widgets.Checkbox(name=it["name"], value=it.get("visible", False)) for it in items}
        b_all = pn.widgets.Button(name='All', height=30)
        b_no  = pn.widgets.Button(name='None', height=30)
        
        def make_callback(c_dict, state):
            return lambda e: [setattr(w, 'value', state) for w in c_dict.values()]
        
        b_all.on_click(make_callback(checks, True))
        b_no.on_click(make_callback(checks, False))
        
        cat_widgets[cat_name] = {"checks": checks, "items": items}
        tabs.append((cat_name, pn.Column(pn.Column(*checks.values(), height=300, scroll=True), pn.Row(b_all, b_no))))

    # 4. Plotting
    mpl_pane = pn.pane.Matplotlib(tight=True, dpi=140, format='png')

    # This global variable will hold the figure for downloading
    current_fig = [None] 

    def update_plot(mmin_val, mmax_val, ymin_val, ymax_val, *args):
        plt.close('all')
        plt.rcParams['text.usetex'] = False # Ensure off
        
        # Create Figure
        fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\gamma}|$ [GeV$^{-1}$]', mathpazo=False)
        current_fig[0] = fig # Save reference for downloader
        
        # Apply Limits
        xlims = (10**mmin_val, 10**mmax_val)
        ylims = (10**ymin_val, 10**ymax_val)
        ax.set_xlim(*xlims); ax.set_ylim(*ylims)
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel(r"$m_a$ [eV]")
        ax.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]")

        # Models
        m_grid = np.logspace(np.log10(xlims[0]), np.log10(xlims[1]), 500)
        for m in models:
            if model_checks[m["name"]].value:
                cmin, cmax = m["C"]
                if np.isclose(cmin, cmax):
                    yy = g_agamma(m_grid, cmin)
                    ax.plot(m_grid, yy, lw=2, alpha=0.95, label=rf"{m['name']}")
                else:
                    y1 = g_agamma(m_grid, cmin); y2 = g_agamma(m_grid, cmax)
                    ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
                    ax.fill_between(m_grid, ylo, yhi, alpha=0.25)
                    ax.plot(m_grid, np.sqrt(ylo*yhi), lw=1.5, alpha=0.85, label=rf"{m['name']}")

        # Bounds
        def _plot_bound(fn, kw):
            # Save limits
            ox, oy = ax.get_xlim(), ax.get_ylim()
            try:
                try: fn(ax, **kw)
                except TypeError: fn(ax=ax, **kw)
            except Exception: pass
            # Restore limits (prevents bounds from autoscaling the view)
            ax.set_xlim(ox); ax.set_ylim(oy)

        for cat in cat_widgets.values():
            for it in cat["items"]:
                if cat["checks"][it["name"]].value:
                    _plot_bound(it["fn"], it.get("kwargs", {}))

        # Cosmetics & Cleaning
        ax.grid(True, which='both', ls=':', alpha=0.4)
        ax.legend(loc='lower right', fontsize=8, frameon=False)
        ax.set_title("Axion–Photon Coupling vs Mass")
        
        # Run the Cleaner
        clean_latex(fig)
        
        mpl_pane.object = fig
        return mpl_pane

    # 5. Bind Logic (THE FLUIDITY FIX)
    # We bind to .param.value_throttled -> Only updates when mouse is released
    
    triggers = [
        mmin.param.value_throttled, 
        mmax.param.value_throttled, 
        ymin.param.value_throttled, 
        ymax.param.value_throttled
    ]
    # Add checkboxes (they don't need throttling)
    triggers += [c.param.value for c in model_checks.values()]
    for c in cat_widgets.values():
        triggers += [chk.param.value for chk in c["checks"].values()]

    pn.bind(update_plot, *triggers, watch=True)

    # 6. Download Logic
    def download_callback():
        if current_fig[0] is None: return None
        buf = io.BytesIO()
        # Save as PDF
        current_fig[0].savefig(buf, format='pdf', bbox_inches='tight')
        buf.seek(0)
        return buf

    download_btn.callback = download_callback

    # Initial Draw
    update_plot(mmin.value, mmax.value, ymin.value, ymax.value)

    # Layout
    controls = pn.Column(mmin, mmax, ymin, ymax, download_btn, width=320)
    return pn.Row(pn.Column(tabs, controls), mpl_pane)

# --- TEMPLATE ---
template = pn.template.MaterialTemplate(
    title="Axion Limits Explorer",
    main=[create_dashboard()],
)
template.servable()