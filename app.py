import panel as pn
import sys
import os
import io
import re  # Required for clean_latex

# 1. Initialize Panel
pn.extension(sizing_mode="stretch_width") 

# --- CSS TWEAKS FOR LOGO SIZE ---
pn.config.raw_css.append("""
.pn-site-logo {
    height: 70px !important; 
    max-height: 70px !important;
    width: auto !important;
    margin-right: 15px;
}
.header-links {
    display: flex;
    gap: 15px;
    align-items: center;
}
""")

# --- WEB BROWSER DATA LOADING ---
if 'pyodide' in sys.modules:
    import pyodide_http
    pyodide_http.patch_all() 
    import requests
    import zipfile
    from js import window, URL

    if not os.path.exists('./PlotFuncs.py'):
        try:
            base_url = window.location.href
            assets_url = URL.new('./assets.zip', base_url).href
            response = requests.get(assets_url)
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    z.extractall('.')
        except Exception as e:
            print(f"Asset load failed: {e}")

# --- IMPORTS ---
import matplotlib.pyplot as plt
import matplotlib.text
import numpy as np

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
        {"name": "Low-Mass Astro",        "fn": AxionPhoton.LowMassAstroBounds},
        {"name": "White Dwarfs",          "fn": AxionPhoton.WhiteDwarfs},
        {"name": "Stellar Bounds",        "fn": AxionPhoton.StellarBounds},
        {"name": "Supernova 1987A",      "fn": AxionPhoton.SN1987A_gamma},
        {"name": "M82 Decay",             "fn": AxionPhoton.M82_decay},
        {"name": "Irreducible FreezeIn",  "fn": AxionPhoton.IrreducibleFreezeIn}
    ],
    "Helioscopes": [
        {"name": "Helioscopes", "fn": AxionPhoton.Helioscopes, "visible": True},
        {"name": "NuSTAR",      "fn": AxionPhoton.NuSTAR_Sun},
    ],
    "Dark Matter Axions": [
        {"name": "Haloscopes All",    "fn": AxionPhoton.Haloscopes},
        {"name": "Dark Matter Decay", "fn": AxionPhoton.DarkMatterDecay},
    ],
    "Next-Gen Resonators": [
        {"name": "ABRACADABRA",          "fn": AxionPhoton.ABRACADABRA},
        {"name": "DMRadio",              "fn": AxionPhoton.DMRadio},
        {"name": "SRF Cavities",         "fn": AxionPhoton.SRF},
        {"name": "WISPLC",               "fn": AxionPhoton.WISPLC},
        {"name": "Twisted Anyon Cavity", "fn": AxionPhoton.TwistedAnyonCavity},
    ],
    "Laboratory Bounds": [
        {"name": "LSW Experiments", "fn": AxionPhoton.LSW},
        {"name": "Collider Bounds", "fn": AxionPhoton.ColliderBounds},
    ],
}

def clean_latex(fig):
    for text_obj in fig.findobj(matplotlib.text.Text):
        s = text_obj.get_text()
        text_obj.set_usetex(False)
        if r"{\bf" in s:
            s_clean = re.sub(r'\{\\bf\s+(.*?)\}', r'\1', s)
            text_obj.set_text(s_clean)
            text_obj.set_weight('bold')

# --- DASHBOARD LOGIC ---
def create_dashboard():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 12,
        'axes.labelsize': 14,
        'axes.titlesize': 16,
        'axes.grid': False,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
        'xtick.direction': 'in', 'ytick.direction': 'in',
        'xtick.top': True, 'ytick.right': True,
    })
    
    # 1. Widgets & Labels
    # 1. Widgets (Compact)
    DEFAULTS = {'mmin': -8, 'mmax': 2, 'ymin': -16, 'ymax': -8}

    mmin = pn.widgets.FloatSlider(name='Min', start=-15, end=8, step=0.5, value=DEFAULTS['mmin'])
    mmax = pn.widgets.FloatSlider(name='Max', start=-15, end=8, step=0.5, value=DEFAULTS['mmax'])
    
    ymin = pn.widgets.FloatSlider(name='Min', start=-30, end=-5, step=0.5, value=DEFAULTS['ymin'])
    ymax = pn.widgets.FloatSlider(name='Max', start=-30, end=-5, step=0.5, value=DEFAULTS['ymax'])

    reset_btn = pn.widgets.Button(name='Reset to Defaults', button_type='warning', icon='refresh', sizing_mode='stretch_width')
    def reset_callback(event):
        mmin.value = DEFAULTS['mmin']; mmax.value = DEFAULTS['mmax']
        ymin.value = DEFAULTS['ymin']; ymax.value = DEFAULTS['ymax']
        for chk in model_checks.values(): chk.value = True
        for cat_name, cat in cat_widgets.items():
            for name, chk in cat["checks"].items():
                is_visible = False
                for item in categories[cat_name]:
                    if item["name"] == name and item.get("visible"): is_visible = True
                chk.value = is_visible
    reset_btn.on_click(reset_callback)

    # 2. Sidebar Sections
    model_checks = {m["name"]: pn.widgets.Checkbox(name=m["name"], value=True) for m in models}
    sel_all_mod = pn.widgets.Button(name='Select All', button_type='light', height=30, margin=5)
    sel_no_mod  = pn.widgets.Button(name='Select None', button_type='light', height=30, margin=5)
    
    def update_models(event, state):
        for chk in model_checks.values(): chk.value = state
    sel_all_mod.on_click(lambda e: update_models(e, True))
    sel_no_mod.on_click(lambda e: update_models(e, False))

    model_accordion = pn.Accordion(toggle=True)
    qcd_col = pn.Column(pn.Column(*model_checks.values(), scroll=True, height=180), pn.Row(sel_all_mod, sel_no_mod))
    model_accordion.append(("QCD & ALPs", qcd_col))

    cat_widgets = {}
    limit_accordion = pn.Accordion(toggle=True)
    for cat_name, items in categories.items():
        checks = {it["name"]: pn.widgets.Checkbox(name=it["name"], value=it.get("visible", False)) for it in items}
        b_all = pn.widgets.Button(name='All', button_type='light', height=30, margin=2)
        b_no  = pn.widgets.Button(name='None', button_type='light', height=30, margin=2)
        def make_callback(c_dict, state):
            return lambda e: [setattr(w, 'value', state) for w in c_dict.values()]
        b_all.on_click(make_callback(checks, True))
        b_no.on_click(make_callback(checks, False))
        cat_widgets[cat_name] = {"checks": checks, "items": items}
        col = pn.Column(pn.Column(*checks.values(), scroll=True, height=120), pn.Row(b_all, b_no))
        limit_accordion.append((cat_name, col))

    # 3. Plotting
    mpl_pane = pn.pane.Matplotlib(tight=True, dpi=200, format='png', sizing_mode='stretch_width', height=650)
    current_fig = [None] 

    def update_plot(mmin_val, mmax_val, ymin_val, ymax_val, *args):
        plt.close('all')
        fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\gamma}|$ [GeV$^{-1}$]', mathpazo=False)
        current_fig[0] = fig 
        
        xlims = (10**mmin_val, 10**mmax_val)
        ylims = (10**ymin_val, 10**ymax_val)
        ax.set_xlim(*xlims); ax.set_ylim(*ylims)
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel(r"$m_a$ [eV]", fontsize=23)
        ax.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]", fontsize=23)
        
        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']
        m_grid = np.logspace(np.log10(xlims[0]), np.log10(xlims[1]), 500)
        
        for i, m in enumerate(models):
            if model_checks[m["name"]].value:
                color = colors[i % len(colors)]
                cmin, cmax = m["C"]
                if np.isclose(cmin, cmax):
                    yy = g_agamma(m_grid, cmin)
                    ax.plot(m_grid, yy, lw=2, alpha=0.9, label=rf"{m['name']}", color=color)
                else:
                    y1 = g_agamma(m_grid, cmin); y2 = g_agamma(m_grid, cmax)
                    ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
                    ax.fill_between(m_grid, ylo, yhi, alpha=0.3, color=color)
                    ax.plot(m_grid, np.sqrt(ylo*yhi), lw=1.5, alpha=0.9, label=rf"{m['name']}", color=color)

        def _plot_bound(fn, kw):
            ox, oy = ax.get_xlim(), ax.get_ylim()
            try:
                try: fn(ax, **kw)
                except TypeError: fn(ax=ax, **kw)
            except Exception: pass
            ax.set_xlim(ox); ax.set_ylim(oy)

        for cat in cat_widgets.values():
            for it in cat["items"]:
                if cat["checks"][it["name"]].value:
                    _plot_bound(it["fn"], it.get("kwargs", {}))

        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=15, frameon=False, title="Models")
        #ax.set_title("Axion–Photon Coupling Space", fontweight="bold", pad=20, fontsize=22)
        clean_latex(fig)
        fig.tight_layout()
        mpl_pane.object = fig
        return mpl_pane

    triggers = [mmin.param.value_throttled, mmax.param.value_throttled, ymin.param.value_throttled, ymax.param.value_throttled]
    triggers += [c.param.value for c in model_checks.values()]
    for c in cat_widgets.values():
        triggers += [chk.param.value for chk in c["checks"].values()]
    pn.bind(update_plot, *triggers, watch=True)
    update_plot(mmin.value, mmax.value, ymin.value, ymax.value)

    # 4. DOWNLOAD BUTTON
    download_btn = pn.widgets.FileDownload(
        callback=lambda: (io.BytesIO(current_fig[0].savefig(io.BytesIO(), format='pdf', bbox_inches='tight') or io.BytesIO().getvalue()) if current_fig[0] else None),
        filename="AxionLimits.pdf", 
        button_type="success", 
        label="Download Figure", 
        height=40,
        icon="file-download",
        sizing_mode="fixed", width=180
    )
    
    # Action Bar: Sits right below the plot
    action_bar = pn.Row(
        pn.Spacer(), 
        pn.Column(
            pn.pane.Markdown(styles={'font-size': '12px', 'margin-bottom': '2px', 'text-align': 'right'}),
            download_btn
        ),
        margin=(0, 0, 0, 0)
    )

    # 5. FOOTER (Slim Banner)
    footer = pn.Row(
        pn.pane.Markdown(
            "© 2025 COSMIC WWISPers. The Axion Limits Explorer was created by Francisco Rodríguez Candón, Francesca Calore and Philip Sørensen. Data and plotting functions are adapted from **[Ciaran O'Hare / AxionLimits](https://github.com/cajohare/AxionLimits)**. More information about the models displayed can be found in the WISP dictionary.",
            styles={'color': '#555', 'font-size': '13px', 'padding-top': '8px'}
        ),
        # FIXED: Moved 'background' into 'styles'
        styles={'background': "#e6e6e6"},
        height=40,
        sizing_mode="stretch_width",
        align="end",
        margin=(20, 0, 0, 0)
    )

    sidebar_content = pn.Column(
        pn.pane.Markdown("## Controls"),
        pn.Card(mmin, mmax, title="Mass Range (mₐ) [log₁₀ eV]", collapsed=False),
        pn.Card(ymin, ymax, title="Coupling Range (|gₐᵧ|) [log₁₀ GeV⁻¹]", collapsed=False),
        reset_btn,
        pn.layout.Divider(),
        pn.pane.Markdown("## Theoretical Models"),
        model_accordion,
        pn.layout.Divider(),
        pn.pane.Markdown("## Experimental Limits"),
        limit_accordion,
        sizing_mode="stretch_width"
    )

    return sidebar_content, mpl_pane, action_bar, footer

# --- TEMPLATE ---
sidebar_content, main_plot, action_bar, footer = create_dashboard()

# Header Links
# Social Links for Header (Using Badge Style for clean look)
social_links = pn.Row(
    pn.pane.Markdown("[![GitHub](https://img.shields.io/badge/GitHub-Repo-black?style=flat&logo=github)](https://github.com/francandon/AxionModelsLimits)"),
    pn.pane.Markdown("[![Cosmic WISPs](https://img.shields.io/badge/Organization-Website-blue?style=flat&logo=google-chrome)](https://cosmicwispers.eu/)"),
    align="center", css_classes=['header-links']
)

# LOGO URL: Replace this string with your local image path, e.g., 'assets/logo.png'
# If running locally, ensure the file exists. If on web, use a URL.
ORGANIZATION_LOGO = "./assets/logo_WISP.jpg"  # Local path to logo image

template = pn.template.FastListTemplate(
    title="Axion Limits Explorer",
    logo=ORGANIZATION_LOGO, 
    header=[social_links],
    sidebar=[sidebar_content],
    main=[
        pn.Column(
            main_plot,  
            action_bar, 
            footer,
            sizing_mode="stretch_width"
        )
    ],
    accent_base_color="#1B3B5A",
    header_background="#FFFFFF",
    header_color="#1B3B5A",
    theme_toggle=False,
    font='Roboto, sans-serif',
)

template.servable()