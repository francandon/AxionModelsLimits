importScripts("https://cdn.jsdelivr.net/pyodide/v0.28.2/full/pyodide.js");

function sendPatch(patch, buffers, msg_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers
  })
}

async function startApplication() {
  console.log("Loading pyodide...");
  self.postMessage({type: 'status', msg: 'Loading pyodide'})
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  console.log("Loaded pyodide!");
  const data_archives = [];
  for (const archive of data_archives) {
    let zipResponse = await fetch(archive);
    let zipBinary = await zipResponse.arrayBuffer();
    self.postMessage({type: 'status', msg: `Unpacking ${archive}`})
    self.pyodide.unpackArchive(zipBinary, "zip");
  }
  await self.pyodide.loadPackage("micropip");
  self.postMessage({type: 'status', msg: `Installing environment`})
  try {
    await self.pyodide.runPythonAsync(`
      import micropip
      await micropip.install(['https://cdn.holoviz.org/panel/wheels/bokeh-3.8.1-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.8.3/dist/wheels/panel-1.8.3-py3-none-any.whl', 'pyodide-http', 'ipywidgets', 'ipympl', 'matplotlib', 'numpy', 'scipy', 'requests', 'pyodide-http', 'ipywidgets_bokeh']);
    `);
  } catch(e) {
    console.log(e)
    self.postMessage({
      type: 'status',
      msg: `Error while installing packages`
    });
  }
  console.log("Environment loaded!");
  self.postMessage({type: 'status', msg: 'Executing code'})
  try {
    const [docs_json, render_items, root_ids] = await self.pyodide.runPythonAsync(`\nimport asyncio\n\nfrom panel.io.pyodide import init_doc, write_doc\n\ninit_doc()\n\nimport panel as pn\nimport sys\nimport os\n\n# 1. Initialize Panel\npn.extension('ipywidgets', 'mathjax', sizing_mode="stretch_width")\n\n# --- WEB BROWSER DATA LOADING (Pyodide specific) ---\nif 'pyodide' in sys.modules:\n    import pyodide_http\n    pyodide_http.patch_all() \n    import requests\n    import zipfile\n    import io\n    \n    # Only download if not already extracted\n    if not os.path.exists('./PlotFuncs.py'):\n        print("Downloading assets...")\n        # 'assets.zip' must be in the same folder as index.html on the website\n        response = requests.get('./assets.zip')\n        \n        if response.status_code == 200:\n            print("Extracting assets...")\n            with zipfile.ZipFile(io.BytesIO(response.content)) as z:\n                z.extractall('.')\n        else:\n            print(f"Failed to load assets.zip (Status: {response.status_code})")\n\n# --- IMPORTS ---\nimport ipywidgets as widgets\nimport matplotlib.pyplot as plt\nimport numpy as np\nfrom IPython.display import display, clear_output\n\n# Import your custom library\n# Ensure PlotFuncs.py and limit_data/ are in the same folder (or extracted there)\ntry:\n    from PlotFuncs import FigSetup, AxionPhoton, MySaveFig, BlackHoleSpins, FilledLimit\nexcept ImportError:\n    # Fallback/Error handling if file not found locally during convert\n    print("Warning: PlotFuncs not found. This might crash unless running in browser with assets.zip.")\n    pass\n\n# --- PHYSICS CONSTANTS ---\nalpha = 1/137.035999084\nK = 5.70e6\npref = alpha/(2*np.pi)\n\ndef g_agamma(m_eV, C):\n    return np.abs(pref * C * (m_eV / K))\n\nmodels = [\n    {"name": "KSVZ", "Ndw": "1", "C": (-1.92, -1.92)},\n    {"name": "DFSZ-I", "Ndw": "6,3", "C": (0.75, 0.75)},\n    {"name": "DFSZ-II", "Ndw": "6,3", "C": (-1.25, -1.25)},\n    {"name": "Astrophobic QCD axion", "Ndw": "1,2", "C": (-6.59, 0.74)},\n    {"name": r"VISH$\\nu$", "Ndw": "1", "C": (0.75, 0.75)},\n    {"name": r"$\\nu$DFSZ", "Ndw": "6", "C": (0.75, 0.75)},\n    {"name": "Majoraxion", "Ndw": "\u2014", "C": (2.66, 2.66)},\n    {"name": "Composite Axion", "Ndw": "0/2/6", "C": (1.33, 2.66)},\n]\n\ncategories = {\n    "Astrophysical Bounds": [\n        {"name": "Helioscopes",     "fn": AxionPhoton.Helioscopes, "visible": True},\n        {"name": "White Dwarfs",   "fn": AxionPhoton.WhiteDwarfs},\n        {"name": "Stellar Bounds", "fn": AxionPhoton.StellarBounds}\n\n    ],\n    "Experimental Bounds": [\n        {"name": "Haloscopes",  "fn": AxionPhoton.Haloscopes},\n        {"name": "Solar Basin",  "fn": AxionPhoton.SolarBasin},\n        {"name": "StAB",         "fn": AxionPhoton.StAB}\n    ],\n    "Test QCD" : [\n        {"name": "QCD Axion",    "fn": AxionPhoton.QCDAxion}\n    ],\n}\n\n# --- DASHBOARD CREATION FUNCTION ---\ndef create_dashboard():\n    # 1. Setup Figure\n    plt.close('all')\n    # We use mathpazo=False to avoid font issues in browser unless fonts are loaded\n    fig, ax = FigSetup(Shape='Rectangular', ylab=r'$|g_{a\\gamma}|$ [GeV$^{-1}$]', mathpazo=False)\n    \n    # 2. Define Helper Functions\n    def html_label(html, width="160px"):\n        lab = widgets.HTML(value=html)\n        lab.layout.width = width\n        return lab\n\n    mmin_label = html_label("m<sub>a</sub><sup>min</sup> [eV]")\n    mmax_label = html_label("m<sub>a</sub><sup>max</sup> [eV]")\n    ymin_label = html_label("g<sub>a\u03b3</sub><sup>min</sup>")\n    ymax_label = html_label("g<sub>a\u03b3</sub><sup>max</sup>")\n\n    # 3. Define Widgets\n    mmin = widgets.FloatLogSlider(value=1e-12, base=10, min=-15, max=8, step=0.1, readout_format=".1e")\n    mmax = widgets.FloatLogSlider(value=1e-1,  base=10, min=-15, max=8, step=0.1, readout_format=".1e")\n    ymin = widgets.FloatLogSlider(value=1e-20, base=10, min=-30, max=-5, step=0.1, readout_format=".1e")\n    ymax = widgets.FloatLogSlider(value=1e-8,  base=10, min=-30, max=-5, step=0.1, readout_format=".1e")\n\n    mmin_box = widgets.HBox([mmin_label, mmin])\n    mmax_box = widgets.HBox([mmax_label, mmax])\n    ymin_box = widgets.HBox([ymin_label, ymin])\n    ymax_box = widgets.HBox([ymax_label, ymax])\n\n    mmin.layout.width = mmax.layout.width = ymin.layout.width = ymax.layout.width = "260px"\n    \n    # 4. Tab 0: Models\n    model_checks = [widgets.Checkbox(value=True, description=m["name"]) for m in models]\n    sel_all_models  = widgets.Button(description='Seleccionar todo')\n    sel_none_models = widgets.Button(description='Deseleccionar todo')\n\n    modelos_panel = widgets.VBox([\n        widgets.VBox(model_checks, layout=widgets.Layout(min_width='260px', max_height='350px', overflow='auto')),\n        widgets.HBox([sel_all_models, sel_none_models]),\n    ])\n\n    tabs_children = [modelos_panel]\n    tab_titles = ['Modelos']\n    cat_checkgroups = {}\n\n    if categories:\n        for tab_name, items in categories.items():\n            checks = [widgets.Checkbox(value=bool(it.get("visible", False)), description=it["name"]) for it in items]\n            sel_all_btn  = widgets.Button(description='Seleccionar todo')\n            sel_none_btn = widgets.Button(description='Deseleccionar todo')\n\n            panel = widgets.VBox([\n                widgets.VBox(checks, layout=widgets.Layout(min_width='260px', max_height='350px', overflow='auto')),\n                widgets.HBox([sel_all_btn, sel_none_btn]),\n            ])\n\n            tabs_children.append(panel)\n            tab_titles.append(tab_name)\n            cat_checkgroups[tab_name] = {"checks": checks, "items": items,\n                                        "sel_all": sel_all_btn, "sel_none": sel_none_btn}\n\n    tabs = widgets.Tab(children=tabs_children)\n    for i, t in enumerate(tab_titles):\n        tabs.set_title(i, t)\n\n    # 5. Right Panel & UI Assembly\n    save_btn = widgets.Button(description='Guardar figura', button_style='success')\n    right = widgets.VBox([mmin_box, mmax_box, ymin_box, ymax_box, save_btn])\n    \n    # --- HERE IS THE DEFINITION OF UI ---\n    ui = widgets.HBox([tabs, right])\n\n    # 6. Output Widget (The Plot)\n    out = widgets.Output()\n\n    # 7. Redraw Logic\n    def redraw(*_):\n        # We must clear the axis and redraw everything\n        ax.cla()\n        ax.set_xscale('log'); ax.set_yscale('log')\n        ax.set_xlabel(r"$m_a$ [eV]")\n        ax.set_ylabel(r"$|g_{a\\gamma}|$ [GeV$^{-1}$]")\n        \n        xlims = (mmin.value, mmax.value)\n        ylims = (ymin.value, ymax.value)\n        ax.set_xlim(*xlims); ax.set_ylim(*ylims)\n\n        # -- Models --\n        m_grid = np.logspace(np.log10(xlims[0]), np.log10(xlims[1]), 600)\n        for chk, md in zip(model_checks, models):\n            if not chk.value: continue\n            cmin, cmax = md["C"]\n            ndw = md.get("Ndw", "\u2014")\n            if np.isclose(cmin, cmax):\n                yy = g_agamma(m_grid, cmin)\n                ax.plot(m_grid, yy, lw=2, alpha=0.95, label=rf"{md['name']} ($N_{{\\rm dw}}$={ndw})")\n            else:\n                y1 = g_agamma(m_grid, cmin); y2 = g_agamma(m_grid, cmax)\n                ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)\n                ax.fill_between(m_grid, ylo, yhi, alpha=0.25)\n                ax.plot(m_grid, np.sqrt(ylo*yhi), lw=1.5, alpha=0.85, label=rf"{md['name']} ($N_{{\\rm dw}}$={ndw})")\n\n        # -- Bounds helper --\n        def _call_on_ax(name, fn, ax, kwargs):\n            # Safe wrapper to call PlotFuncs on our specific axis\n            xlim = ax.get_xlim(); ylim = ax.get_ylim()\n            was_auto = ax.get_autoscale_on(); ax.set_autoscale_on(False)\n            try:\n                try: fn(ax, **(kwargs or {}))\n                except TypeError: fn(ax=ax, **(kwargs or {}))\n            except Exception as e:\n                print(f"Error plotting {name}: {e}")\n            finally:\n                ax.set_xlim(xlim); ax.set_ylim(ylim); ax.set_autoscale_on(was_auto)\n\n        # -- Plot Bounds --\n        if categories:\n            for tab_name, grp in cat_checkgroups.items():\n                for chk, it in zip(grp["checks"], grp["items"]):\n                    if chk.value:\n                        _call_on_ax(it["name"], it["fn"], ax, it.get("kwargs", {}))\n\n        # Cosmetics\n        ax.grid(True, which='both', ls=':', alpha=0.4)\n        ax.legend(loc='lower right', fontsize=9, frameon=False)\n        ax.set_title("Axion\u2013Photon Coupling vs Mass", pad=8)\n\n        # Force Update in the Output Widget\n        with out:\n            clear_output(wait=True)\n            display(fig)\n\n    # 8. Event Handlers\n    def on_save(_):\n        # Saving in browser downloads the file to the browser's download folder\n        fig.savefig("AxionPhoton_Dashboard.pdf", bbox_inches='tight')\n        fig.savefig("AxionPhoton_Dashboard.png", dpi=300, bbox_inches='tight')\n    \n    save_btn.on_click(on_save)\n\n    sel_all_models.on_click(lambda _: [setattr(c, "value", True)  for c in model_checks])\n    sel_none_models.on_click(lambda _: [setattr(c, "value", False) for c in model_checks])\n    \n    for grp in cat_checkgroups.values():\n        grp["sel_all"].on_click(lambda _, g=grp: [setattr(c, "value", True)  for c in g["checks"]])\n        grp["sel_none"].on_click(lambda _, g=grp: [setattr(c, "value", False) for c in g["checks"]])\n\n    for w in (mmin, mmax, ymin, ymax): w.observe(redraw, names='value')\n    for chk in model_checks: chk.observe(redraw, names='value')\n    for grp in cat_checkgroups.values():\n        for chk in grp["checks"]: chk.observe(redraw, names='value')\n\n    # Initial Draw\n    redraw()\n\n    # 9. Return the combined layout (Controls + Plot)\n    # We stack them vertically so the plot appears below the controls\n    return widgets.VBox([ui, out])\n\n# --- TEMPLATE SETUP ---\nintro_text = """\n# Axion Limits\nInteractive dashboard for Axion-Photon coupling.\nSelect models and bounds to visualize.\n"""\n\ntemplate = pn.template.MaterialTemplate(\n    title="Axion Limits Explorer",\n    sidebar=[intro_text],\n    main=[pn.panel(create_dashboard(), sizing_mode="scale_width")],\n)\n\ntemplate.servable()\n\nawait write_doc()`)
    self.postMessage({
      type: 'render',
      docs_json: docs_json,
      render_items: render_items,
      root_ids: root_ids
    })
  } catch(e) {
    const traceback = `${e}`
    const tblines = traceback.split('\n')
    self.postMessage({
      type: 'status',
      msg: tblines[tblines.length-2]
    });
    throw e
  }
}

self.onmessage = async (event) => {
  const msg = event.data
  if (msg.type === 'rendered') {
    self.pyodide.runPythonAsync(`
    from panel.io.state import state
    from panel.io.pyodide import _link_docs_worker

    _link_docs_worker(state.curdoc, sendPatch, setter='js')
    `)
  } else if (msg.type === 'patch') {
    self.pyodide.globals.set('patch', msg.patch)
    self.pyodide.runPythonAsync(`
    from panel.io.pyodide import _convert_json_patch
    state.curdoc.apply_json_patch(_convert_json_patch(patch), setter='js')
    `)
    self.postMessage({type: 'idle'})
  } else if (msg.type === 'location') {
    self.pyodide.globals.set('location', msg.location)
    self.pyodide.runPythonAsync(`
    import json
    from panel.io.state import state
    from panel.util import edit_readonly
    if state.location:
        loc_data = json.loads(location)
        with edit_readonly(state.location):
            state.location.param.update({
                k: v for k, v in loc_data.items() if k in state.location.param
            })
    `)
  }
}

startApplication()