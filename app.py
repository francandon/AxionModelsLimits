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
/* Style main collapsible cards (QCD Axion Models, Experimental Limits) */
.pn-card > .card > .card-header {
    background-color: #1B3B5A !important;
    color: white !important;
    font-weight: bold;
}
.pn-card > .card > .card-header button {
    color: white !important;
}
/* Style category accordion tabs inside cards - lighter background */
.card .nav-tabs .nav-link {
    background-color: #f5f5f5 !important;
    border-color: #ddd !important;
    color: #333 !important;
}
.card .nav-tabs .nav-link:hover {
    background-color: #e8e8e8 !important;
}
.card .nav-tabs .nav-link.active {
    background-color: #ffffff !important;
    border-color: #1B3B5A !important;
    border-bottom-color: #ffffff !important;
    color: #1B3B5A !important;
    font-weight: 500;
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
except Exception as _import_err:
    # Minimal safe fallbacks to avoid hard crashes during pyodide startup
    def AxionPhoton(*args, **kwargs):
        return None
    def FigSetup(*args, **kwargs):
        return plt.subplots()
    # Try to recover: if PlotFuncs was extracted after the first import attempt,
    # import it dynamically and pick up real implementations if available.
    try:
        import importlib
        PF = importlib.import_module('PlotFuncs')
        if hasattr(PF, 'AxionPhoton'):
            AxionPhoton = getattr(PF, 'AxionPhoton')
        if hasattr(PF, 'FigSetup'):
            FigSetup = getattr(PF, 'FigSetup')
    except Exception:
        # If recovery fails, keep the safe fallbacks and continue; detailed
        # errors will appear in the browser console for debugging.
        pass

# --- PHYSICS ---
alpha = 1/137.035999084
K = 5.70e6
pref = alpha/(2*np.pi)

def g_agamma(m_eV, C):
    return np.abs(pref * C * (m_eV / K))

models = [
    {"name": "KSVZ", "display_name": "KSVZ", "Ndw": "1", "C": (-1.92, -1.92), "category": "KSVZ-like"},
    {"name": "DFSZ-I", "display_name": "DFSZ-I", "Ndw": "6,3", "C": (0.75, 0.75), "category": "DFSZ-like"},
    {"name": "DFSZ-II", "display_name": "DFSZ-II", "Ndw": "6,3", "C": (-1.25, -1.25), "category": "DFSZ-like"},
    {"name": "Astrophobic QCD axion", "display_name": "Astrophobic QCD axion", "Ndw": "1,2", "C": (-6.59, 0.74), "category": "Strongly deviated"},
    {"name": r"VISH$\nu$", "display_name": "nu-VISH", "Ndw": "1", "C": (0.75, 0.75), "category": "Strongly deviated"},
    {"name": r"$\nu$DFSZ", "display_name": "nu-DFSZ", "Ndw": "6", "C": (0.75, 0.75), "category": "DFSZ-like"},
    {"name": "Majoraxion", "display_name": "Majoraxion", "Ndw": "—", "C": (2.66, 2.66), "category": "Strongly deviated"},
    {"name": "Composite Axion", "display_name": "Composite Axion", "Ndw": "0/2/6", "C": (1.33, 2.66), "category": "Strongly deviated"},
]

# Dynamic categorisation: keep main groups but auto-discover available AxionPhoton plotting methods
categories = {
    "Astrophysical Bounds": [
        {"name": "Low-Mass Astro",        "fn": AxionPhoton.LowMassAstroBounds},
        {"name": "White Dwarfs",          "fn": AxionPhoton.WhiteDwarfs},
        {"name": "Stellar Bounds",        "fn": AxionPhoton.StellarBounds},
        {"name": "Supernova 1987A",      "fn": AxionPhoton.SN1987A_gamma},
        {"name": "M82 Decay",             "fn": AxionPhoton.M82_decay},
        {"name": "Irreducible FreezeIn",  "fn": AxionPhoton.IrreducibleFreezeIn}
    ],
    "Experimental": [],
    "Cosmological": [
        {"name": "Dark Matter Decay", "fn": AxionPhoton.DarkMatterDecay},
    ],
    "Sensitivities": [
        {"name": "ABRACADABRA",          "fn": AxionPhoton.ABRACADABRA},
        {"name": "DMRadio",              "fn": AxionPhoton.DMRadio},
        {"name": "SRF Cavities",         "fn": AxionPhoton.SRF},
        {"name": "WISPLC",               "fn": AxionPhoton.WISPLC},
        {"name": "Twisted Anyon Cavity", "fn": AxionPhoton.TwistedAnyonCavity},
    ],
}

# Populate Experimental group by inspecting AxionPhoton for callable plotting methods
try:
    # collect public callables defined on the AxionPhoton class/object
    api_names = [n for n in dir(AxionPhoton) if not n.startswith('_')]
    api_callables = []
    for n in api_names:
        try:
            attr = getattr(AxionPhoton, n)
            if callable(attr):
                api_callables.append((n, attr))
        except Exception:
            continue

    # Keywords -> experimental subgroup mapping (simple heuristics)
    keyword_map = {
        'ADMX': 'Haloscopes', 'HAYSTAC': 'Haloscopes', 'RADES': 'Haloscopes', 'ORGAN': 'Haloscopes', 'CAPP': 'Haloscopes',
        'HALOSCOPE': 'Haloscopes', 'HALOSCOPES': 'Haloscopes',
        'ABRACADABRA': 'Laboratory', 'ABRACAD': 'Laboratory', 'LSW': 'Laboratory', 'PVLAS': 'Laboratory',
        'QUAX': 'Haloscopes', 'DMRadio': 'Laboratory', 'MADMAX': 'Laboratory', 'MAD': 'Laboratory',
        'CAST': 'Helioscopes', 'Helioscope': 'Helioscopes', 'Helioscopes': 'Helioscopes',
        'NuSTAR': 'Telescopes/X-ray', 'Fermi': 'Telescopes/Gamma', 'INTEGRAL': 'Telescopes/Gamma', 'XMM': 'Telescopes/X-ray', 'Chandra': 'Telescopes/X-ray',
        'SN': 'Supernovae', 'SN1987A': 'Supernovae', 'Supernova': 'Supernovae', 'M82': 'Astrophysical', 'NeutronStars': 'Astrophysical',
        'Collider': 'Collider', 'LEP': 'Collider', 'LHC': 'Collider', 'ATLAS': 'Collider', 'CMS': 'Collider', 'BaBar': 'Collider', 'Belle': 'Collider',
        'Projections': 'Projections', 'Projected': 'Projections'
    }

    # Human-readable name function
    def humanize(name):
        # Prefer keeping acronyms together and split CamelCase sensibly.
        s = name.replace('_', ' ')
        # If string is all caps (acronym-like) or digits, keep as-is (just normalize spaces)
        if re.match(r'^[A-Z0-9 \-]+$', name):
            return ' '.join(s.split())
        # Insert space between a lowercase/digit and uppercase letter (camelCase -> camel Case)
        s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', s)
        # Normalize multiple spaces
        s = ' '.join(s.split())
        return s.strip()

    # Already included names to avoid duplicates
    existing = set()
    for grp in categories.values():
        for item in grp:
            existing.add(item.get('name'))

    for n, fn in sorted(api_callables):
        # skip high-level helpers already in categories
        display = humanize(n)
        if display in existing:
            continue
        # decide target group
        target = None
        nl = n.lower()
        for k, grp in keyword_map.items():
            if k.lower() in nl:
                target = grp
                break
        if target is None:
            # default to Experimental
            target = 'Experimental'
        # append to corresponding categories key (create subgroup as needed)
        if target not in categories:
            categories[target] = []
        categories[target].append({'name': display, 'fn': fn})
except Exception:
    # If introspection fails (pyodide or import race), keep static list and continue
    pass

def clean_latex(fig):
    for text_obj in fig.findobj(matplotlib.text.Text):
        s = text_obj.get_text()
        text_obj.set_usetex(False)
        if r"{\bf" in s:
            s_clean = re.sub(r'\{\\bf\s+(.*?)\}', r'\1', s)
            text_obj.set_text(s_clean)
            text_obj.set_weight('bold')

# Remove text labels that fall outside the currently visible data limits.
# Many plotting routines call ax.text(...) directly; this helper attempts
# to map each Text object's position back into data coordinates and removes
# the label if it lies outside the current x/y limits.
def prune_out_of_bounds_labels(ax):
    try:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
    except Exception:
        return
    # Iterate over a copy because we may remove items while iterating
    for text_obj in list(ax.texts):
        try:
            pos = text_obj.get_position()
            trans = text_obj.get_transform()
            # Transform the text position into display coordinates, then into data coords
            display_coords = trans.transform(pos)
            data_coords = ax.transData.inverted().transform(display_coords)
            xdata, ydata = data_coords[0], data_coords[1]
        except Exception:
            # If transform mapping fails (non-data coordinates), keep the label
            continue
        # If outside visible range, remove the text object
        if (xdata < x0) or (xdata > x1) or (ydata < y0) or (ydata > y1):
            try:
                text_obj.remove()
            except Exception:
                pass

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
    model_checks = {m["name"]: pn.widgets.Checkbox(name=m.get("display_name", m["name"]), value=True) for m in models}
    sel_all_mod = pn.widgets.Button(name='Select All', button_type='light', height=30, margin=5)
    sel_no_mod  = pn.widgets.Button(name='Select None', button_type='light', height=30, margin=5)
    
    def update_models(event, state):
        for chk in model_checks.values(): chk.value = state
    sel_all_mod.on_click(lambda e: update_models(e, True))
    sel_no_mod.on_click(lambda e: update_models(e, False))

    # Group models by category
    model_categories = {}
    for m in models:
        cat = m.get("category", "Other")
        if cat not in model_categories:
            model_categories[cat] = []
        model_categories[cat].append(m["name"])
    
    # Create accordion for model categories
    model_accordion = pn.Accordion(toggle=True)
    for cat_name in ["KSVZ-like", "DFSZ-like", "Strongly deviated"]:
        if cat_name in model_categories:
            cat_checks = [model_checks[name] for name in model_categories[cat_name]]
            col = pn.Column(*cat_checks, scroll=True, height=100)
            model_accordion.append((cat_name, col))
    
    model_card = pn.Card(
        model_accordion,
        pn.Row(sel_all_mod, sel_no_mod),
        title="QCD Axion Models",
        collapsed=True
    )

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

    limit_card = pn.Card(
        limit_accordion,
        title="Experimental Limits",
        collapsed=True
    )

    # 3. Plotting
    mpl_pane = pn.pane.Matplotlib(tight=True, dpi=200, format='png', sizing_mode='stretch_width', height=650)
    current_fig = [None]  # Cache for figure reuse
    current_ax = [None]   # Cache for axis reuse
    fig_initialized = [False]  # Track if figure has been initialized

    def update_plot(mmin_val, mmax_val, ymin_val, ymax_val, *args):
        # Performance optimization: Reuse figure/axis instead of recreating
        # This avoids expensive plt.close('all') and FigSetup() on every update
        if not fig_initialized[0] or current_fig[0] is None:
            # First plot: Create figure
            fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\gamma}|$ [GeV$^{-1}$]', mathpazo=False)
            current_fig[0] = fig
            current_ax[0] = ax
            fig_initialized[0] = True
        else:
            # Subsequent plots: Reuse figure and clear axes
            fig = current_fig[0]
            ax = current_ax[0]
            ax.clear()
            # Reset axes properties after clearing
            ax.set_xscale('log'); ax.set_yscale('log')
        
        xlims = (10**mmin_val, 10**mmax_val)
        ylims = (10**ymin_val, 10**ymax_val)
        ax.set_xlim(*xlims); ax.set_ylim(*ylims)
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel(r"$m_a$ [eV]", fontsize=23)
        ax.set_ylabel(r"$|g_{a\gamma}|$ [GeV$^{-1}$]", fontsize=23)
        
        # Define color palettes and line styles for each category
        # Unified colorblind-friendly palette for all models
        # Extended palette with high contrast and colorblind compatibility
        unified_palette = [
            '#0173B2',  # Dark Blue
            '#DE8F05',  # Orange
            '#CC78BC',  # Magenta
            '#CA9161',  # Brown
            '#56B4E9',  # Sky Blue
            '#1B9E77',  # Teal/Green
            '#F0E442',  # Yellow
            '#E84C3D',  # Red
        ]
        
        # Define line styles for each category
        linestyle_map = {
            "KSVZ-like": '-',      # Solid
            "DFSZ-like": '--',     # Dashed
            "Strongly deviated": '-.',  # Dotted
        }
        
        linewidth_map = {
            "KSVZ-like": 2.0,
            "DFSZ-like": 2.0,
            "Strongly deviated": 2.2,
        }
        
        m_grid = np.logspace(np.log10(xlims[0]), np.log10(xlims[1]), 500)
        
        # Plot models grouped by category
        model_cat_order = ["KSVZ-like", "DFSZ-like", "Strongly deviated"]
        color_idx = 0
        for cat_idx, cat_name in enumerate(model_cat_order):
            models_in_cat = [m for m in models if m.get("category") == cat_name]
            cat_linestyle = linestyle_map[cat_name]
            cat_linewidth = linewidth_map[cat_name]
            
            # Add separator entry for category (invisible plot for spacing)
            if cat_idx > 0:
                ax.plot([], [], ' ', label='')
            
            # Add category header with a representative line style
            ax.plot([], [], linestyle=cat_linestyle, color='black', linewidth=cat_linewidth, label=cat_name)
            
            for m in models_in_cat:
                if model_checks[m["name"]].value:
                    color = unified_palette[color_idx % len(unified_palette)]
                    cmin, cmax = m["C"]
                    label_text = m['name']
                    
                    if np.isclose(cmin, cmax):
                        # Single value - plot as a line
                        yy = g_agamma(m_grid, cmin)
                        ax.plot(m_grid, yy, lw=cat_linewidth, alpha=0.9, label=label_text, 
                               color=color, linestyle=cat_linestyle)
                    else:
                        # Range of values - plot as a band without central line
                        y1 = g_agamma(m_grid, cmin); y2 = g_agamma(m_grid, cmax)
                        ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
                        ax.fill_between(m_grid, ylo, yhi, alpha=0.3, color=color)
                        # Add a thick line in legend to represent the band
                        ax.plot([], [], lw=cat_linewidth*3, alpha=0.5, label=label_text, 
                               color=color, linestyle=cat_linestyle)
                    color_idx += 1

        def _plot_bound(fn, kw):
            ox, oy = ax.get_xlim(), ax.get_ylim()
            existing_texts = set(ax.texts)
            try:
                try: fn(ax, **kw)
                except TypeError: fn(ax=ax, **kw)
            except Exception: pass
            for text_obj in list(ax.texts):
                if text_obj in existing_texts:
                    continue
                try:
                    x, y = text_obj.get_position()
                    x = float(x)
                    y = float(y)
                except (TypeError, ValueError):
                    continue
                if not (min(ox) <= x <= max(ox) and min(oy) <= y <= max(oy)):
                    text_obj.remove()
            ax.set_xlim(ox); ax.set_ylim(oy)

        for cat in cat_widgets.values():
            for it in cat["items"]:
                if cat["checks"][it["name"]].value:
                    _plot_bound(it["fn"], it.get("kwargs", {}))

        # Custom legend with better formatting
        leg = ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=13, 
                       frameon=False, title="Theoretical Models", title_fontsize=14)
        
        # Format legend: make category headers bold
        category_names = ["DFSZ-like", "KSVZ-like", "Strongly deviated"]
        for text in leg.get_texts():
            label_text = text.get_text()
            if label_text in category_names:
                # This is a category header - make it bold
                text.set_fontweight('bold')
                text.set_fontsize(13)
        #ax.set_title("Axion–Photon Coupling Space", fontweight="bold", pad=20, fontsize=22)
        # Remove labels that are outside the selected mass / coupling ranges
        prune_out_of_bounds_labels(ax)
        clean_latex(fig)
        fig.tight_layout()
        mpl_pane.object = fig
        return mpl_pane

    # Performance optimization: Use value_throttled for sliders to debounce rapid updates
    # For checkboxes, use a single debounced callback instead of watching each individually
    triggers = [mmin.param.value_throttled, mmax.param.value_throttled, ymin.param.value_throttled, ymax.param.value_throttled]
    pn.bind(update_plot, *triggers, watch=True)
    
    # Create a single debounced callback for all model and limit checkboxes
    # This prevents cascading update calls when user toggles multiple checkboxes
    def _checkbox_changed(event):
        update_plot(mmin.value, mmax.value, ymin.value, ymax.value)
    
    for c in model_checks.values():
        c.param.watch(_checkbox_changed, 'value')
    for c in cat_widgets.values():
        for chk in c["checks"].values():
            chk.param.watch(_checkbox_changed, 'value')
    
    update_plot(mmin.value, mmax.value, ymin.value, ymax.value)

    # 4. DOWNLOAD BUTTON
    def download_figure():
        if current_fig[0] is None:
            return None
        buffer = io.BytesIO()
        current_fig[0].savefig(buffer, format='pdf', bbox_inches='tight')
        buffer.seek(0)
        return buffer
    
    download_btn = pn.widgets.FileDownload(
        callback=download_figure,
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
            "© 2025 COSMIC WWISPers. The Axion Limits Explorer was created by Francisco Rodríguez Candón, Francesca Lecce and Philip Sørensen. Data and plotting functions are adapted from **[Ciaran O'Hare / AxionLimits](https://github.com/cajohare/AxionLimits)**. More information about the models displayed can be found in the WISP dictionary.",
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
        model_card,
        pn.layout.Divider(),
        limit_card,
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
