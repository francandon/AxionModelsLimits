import panel as pn
import sys
import os

# 1. Initialize Panel
pn.extension('mathjax', sizing_mode="stretch_width")

# --- WEB BROWSER DATA LOADING ---
if 'pyodide' in sys.modules:
    import pyodide_http
    pyodide_http.patch_all() 
    import requests
    import zipfile
    import io
    from js import window, URL # Import JavaScript tools

    if not os.path.exists('./PlotFuncs.py'):
        print("Downloading assets...")
        
        # 1. Calculate the FULL URL (e.g., https://site.com/repo/assets.zip)
        # This fixes the "MissingSchema" error
        base_url = window.location.href
        assets_url = URL.new('./assets.zip', base_url).href
        print(f"Downloading from: {assets_url}")
        
        # 2. Synchronous Download
        response = requests.get(assets_url)
        
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall('.')
            print("Assets extracted successfully.")
        else:
            print(f"Failed to download assets. Status: {response.status_code}")

# --- IMPORTS ---
import matplotlib.pyplot as plt
import numpy as np

try:
    from PlotFuncs import FigSetup, AxionPhoton
except ImportError:
    print("PlotFuncs could not be imported. The asset download likely failed.")
    def AxionPhoton(*args): pass
    def FigSetup(*args, **kwargs): return plt.subplots()

# --- PHYSICS CONSTANTS ---
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
# --- DASHBOARD LOGIC ---
def create_dashboard():
    # 1. Static Matplotlib Backend
    plt.switch_backend('agg') 
    
    # Force LaTeX OFF globally
    plt.rcParams['text.usetex'] = False
    
    # 2. Widgets
    mmin = pn.widgets.FloatSlider(name='Min Mass (10^x eV)', start=-15, end=8, step=0.5, value=-12)
    mmax = pn.widgets.FloatSlider(name='Max Mass (10^x eV)', start=-15, end=8, step=0.5, value=-1)
    ymin = pn.widgets.FloatSlider(name='Min Coupling (10^x)', start=-30, end=-5, step=0.5, value=-20)
    ymax = pn.widgets.FloatSlider(name='Max Coupling (10^x)', start=-30, end=-5, step=0.5, value=-8)

    save_btn = pn.widgets.Button(name='Download PDF', button_type='success')
    
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
        b_all = pn.widgets.Button(name='All')
        b_no  = pn.widgets.Button(name='None')
        def make_callback(c_dict, state):
            return lambda e: [setattr(w, 'value', state) for w in c_dict.values()]
        b_all.on_click(make_callback(checks, True))
        b_no.on_click(make_callback(checks, False))
        cat_widgets[cat_name] = {"checks": checks, "items": items}
        tabs.append((cat_name, pn.Column(pn.Column(*checks.values(), height=300, scroll=True), pn.Row(b_all, b_no))))

    # 3. Plotting Function
    mpl_pane = pn.pane.Matplotlib(tight=True, dpi=140, format='png')

    def update_plot(*events):
        plt.close('all')
        
        # 1. Reset Styles to prevent PlotFuncs from loading sticky styles
        plt.style.use('default')
        plt.rcParams['text.usetex'] = False
        plt.rcParams['font.family'] = 'serif' 
        
        # 2. Call FigSetup
        # We pass mathpazo=False, but we don't trust it fully
        fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\gamma}|$ [GeV$^{-1}$]', mathpazo=False)
        
        # 3. --- NUCLEAR DE-LATEXING ---
        # This loop finds EVERY text object (titles, labels, ticks) and disables LaTeX
        import matplotlib.text
        for text_obj in fig.findobj(matplotlib.text.Text):
            text_obj.set_usetex(False)
            
        # Double check global param just in case
        plt.rcParams['text.usetex'] = False

        # 4. Setup Axes
        xlims = (10**mmin.value, 10**mmax.value)
        ylims = (10**ymin.value, 10**ymax.value)
        
        ax.set_xlim(*xlims)
        ax.set_ylim(*ylims)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel(r"$m_a$ [eV]")
        ax.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]")

        # 5. Plot Models
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

        # 6. Plot Bounds
        def _plot_bound(fn, kw):
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

        # 7. Final Cosmetics
        ax.grid(True, which='both', ls=':', alpha=0.4)
        ax.legend(loc='lower right', fontsize=8, frameon=False)
        ax.set_title("Axion–Photon Coupling vs Mass")
        
        # 8. One last check before rendering
        for text_obj in fig.findobj(matplotlib.text.Text):
            text_obj.set_usetex(False)

        mpl_pane.object = fig
        return mpl_pane

    watch_list = [mmin, mmax, ymin, ymax] 
    watch_list += list(model_checks.values())
    for c in cat_widgets.values():
        watch_list += list(c["checks"].values())

    pn.bind(update_plot, *watch_list, watch=True)

    def save_callback(event):
        # Only saving PNG works reliably in browser without extra JS hacks
        mpl_pane.object.savefig("AxionLimits.png")
        
    save_btn.on_click(save_callback)
    
    update_plot()
    controls = pn.Column(mmin, mmax, ymin, ymax, save_btn, width=320)
    return pn.Row(pn.Column(tabs, controls), mpl_pane)

# --- TEMPLATE ---
template = pn.template.MaterialTemplate(
    title="Axion Limits Explorer",
    main=[create_dashboard()],
)
template.servable()