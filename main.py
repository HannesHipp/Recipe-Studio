import dash
from dash import dcc, html, Input, Output, State, ALL, MATCH, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from data_manager import DataManager
from recipe_manager import RecipeManager
from components.navigation import create_sidebar
from components.cookbook import create_cookbook_layout
from components.planner import create_planner_layout, create_recipe_tab_content
from components.inputs import create_ingredient_row
from components.optimizer import create_optimizer_layout
from components.results import create_results_layout
from components.ingredients_editor import create_ingredients_editor_layout
from optimization import solve_global_plan
import uuid
# from components.layout import create_layout # Old single page layout

# =============================================================================
# App Initialization & Data Setup
# =============================================================================

data_manager = DataManager('ingredients.json')
recipe_manager = RecipeManager('recipes.json')

app = dash.Dash(__name__, external_stylesheets=[
                dbc.themes.CYBORG, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"], suppress_callback_exceptions=True)

# Helper for ingredients


def get_ingredient_options():
    ingredients = data_manager.get_all_ingredients()
    return [{'label': name.title(), 'value': name} for name in sorted(ingredients.keys())]


def get_colors(n):
    import plotly.colors as colors
    return colors.qualitative.Plotly * (n // len(colors.qualitative.Plotly) + 1)


# =============================================================================
# Main Layout (Shell)
# =============================================================================
sidebar = create_sidebar()
content_style = {
    "margin-left": "16rem",
    "margin-right": "0rem",
    "padding": "2rem 1rem",
}

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='selected-recipes-store', storage_type='session'),
    dcc.Store(id='settings-store', storage_type='local'),
    dcc.Store(id='optimization-results-store', storage_type='session'),
    dcc.Store(id='cookbook-refresh-trigger', data=0),

    sidebar,

    html.Div(id='page-content', style={
        "margin-left": "16rem",
        "padding": "2rem",
    })
])

# =============================================================================
# Page Routing Callback
# =============================================================================


@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'),
              Input('cookbook-refresh-trigger', 'data'),
              State('selected-recipes-store', 'data'),
              State('settings-store', 'data'),
              State('optimization-results-store', 'data'))
def display_page(pathname, _, selected_ids, settings_data, optimization_results):
    if pathname == '/planner':
        return create_planner_layout()
    elif pathname == '/optimizer':
        return create_optimizer_layout(settings_data)
    elif pathname == '/results':
        return create_results_layout(optimization_results, recipe_manager, data_manager)
    elif pathname == '/ingredients':
        return create_ingredients_editor_layout(data_manager)
    # Default to Cookbook
    return create_cookbook_layout(recipe_manager, selected_ids)


@app.callback(
    Output('settings-store', 'data'),
    Input('target-protein', 'value'),
    Input('target-calories', 'value'),
    Input('tolerance-protein', 'value'),
    Input('tolerance-calories', 'value'),
    Input('min-meal-cal', 'value'),
    Input('max-meal-cal', 'value'),
    Input('include-cost-toggle', 'value'),
    Input('slider-carbs', 'value'),
    Input('slider-fat', 'value'),
    prevent_initial_call=True
)
def save_settings(prot, cal, tol_prot, tol_cal, min_cal, max_cal, include_cost, carbs_val, fat_val):
    return {
        'prot': prot,
        'cal': cal,
        'tol_prot': tol_prot,
        'tol_cal': tol_cal,
        'min_meal_cal': min_cal,
        'max_meal_cal': max_cal,
        'include_cost': include_cost,
        'macro_slider': {'carbs': carbs_val, 'fat': fat_val}
    }


@app.callback(
    Output('slider-carbs', 'value'),
    Output('slider-fat', 'value'),
    Output('macro-distribution-bar', 'children'),
    Input('slider-carbs', 'value'),
    Input('slider-fat', 'value'),
    Input('target-protein', 'value'),
    Input('target-calories', 'value')
)
def sync_sliders_and_graph(carbs_slider, fat_slider, prot_target, cal_target):
    """
    Sliders represent relative split of Carbs/Fat (out of 100%).
    They are inverses: if Carbs slider = 60, Fat slider = 40.

    Actual distribution:
    - Protein% = fixed from target inputs
    - remaining% = 100 - Protein%
    - Carbs% = carbs_slider / 100 * remaining%
    - Fat% = fat_slider / 100 * remaining%
    """
    # 1. Calculate Protein %
    if not cal_target or float(cal_target) <= 0:
        prot_pct = 0
    else:
        try:
            prot_cal = float(prot_target) * 4
            cal_target_val = float(cal_target)
            prot_pct = (prot_cal / cal_target_val) * 100
        except (TypeError, ValueError):
            prot_pct = 0

    # Cap Protein at 100
    if prot_pct > 100:
        prot_pct = 100

    remaining_pct = max(0, 100 - prot_pct)

    # 2. Handle slider sync (inverses of each other)
    trigger_id = ctx.triggered_id

    # Default values
    if carbs_slider is None:
        carbs_slider = 50
    if fat_slider is None:
        fat_slider = 50

    if trigger_id == 'slider-fat':
        # Fat slider changed -> Carbs is inverse
        carbs_slider = 100 - fat_slider
    else:
        # Carbs slider changed (or initial/protein change) -> Fat is inverse
        fat_slider = 100 - carbs_slider

    # 3. Calculate actual distribution percentages
    actual_carbs_pct = (carbs_slider / 100) * remaining_pct
    actual_fat_pct = (fat_slider / 100) * remaining_pct

    # 4. Create Visual Bar with white labels
    # Using html.Div to create custom colored segments since dbc.Progress color prop only accepts Bootstrap names
    def make_bar(val, bg_color, label_text):
        if val <= 0:
            return None
        return html.Div(
            label_text if val > 8 else "",  # Only show label if segment is wide enough
            style={
                "width": f"{val}%",
                "backgroundColor": bg_color,
                "height": "100%",
                "display": "inline-block",
                "textAlign": "center",
                "lineHeight": "30px",
                "fontSize": "0.85rem",
                "fontWeight": "bold",
                "color": "white"
            }
        )

    bar_children = [
        make_bar(prot_pct, "#00cc96", f"{prot_pct:.0f}%"),
        make_bar(actual_carbs_pct, "#AB63FA", f"{actual_carbs_pct:.0f}%"),
        make_bar(actual_fat_pct, "#FFA15A", f"{actual_fat_pct:.0f}%")
    ]
    # Filter out None values
    bar_children = [b for b in bar_children if b is not None]

    return carbs_slider, fat_slider, bar_children


# =============================================================================
# Target Range Charts (Calories & Protein)
# =============================================================================

@app.callback(
    Output('calories-chart-container', 'children'),
    Input('target-calories', 'value'),
    Input('tolerance-calories', 'value'),
    Input('optimization-results-store', 'data')
)
def update_calories_chart(target_cal, tol_cal, results_data):
    """Generate calories range chart with optional solution line."""
    if not target_cal or not tol_cal:
        return None

    target_cal = float(target_cal)
    tol_cal = float(tol_cal)

    # Get solution if available
    sol_cal = None
    if results_data and 'stats' in results_data:
        sol_cal = results_data['stats'].get('calories')

    # X-axis range: target range should be 90% of graph width
    range_start = target_cal - tol_cal
    range_end = target_cal + tol_cal
    range_width = range_end - range_start

    # Add 5% padding on each side so range spans 90% of graph
    padding = range_width * (0.05 / 0.9)
    min_x = range_start - padding
    max_x = range_end + padding

    # Extend if solution is outside range
    if sol_cal:
        if sol_cal < min_x:
            min_x = sol_cal - padding
        if sol_cal > max_x:
            max_x = sol_cal + padding

    fig = go.Figure()
    fig.add_trace(go.Bar(x=[0], y=[""], orientation='h',
                  marker_color='rgba(0,0,0,0)', showlegend=False))

    # Target Range
    fig.add_shape(type="rect",
                  x0=range_start, x1=range_end,
                  y0=-0.4, y1=0.4,
                  line=dict(width=0),
                  fillcolor="rgba(239, 85, 59, 0.3)")

    # Solution Line (if available)
    if sol_cal:
        fig.add_shape(type="line",
                      x0=sol_cal, x1=sol_cal,
                      y0=-0.4, y1=0.4,
                      line=dict(color="#EF553B", width=5))

    fig.update_layout(
        xaxis=dict(range=[min_x, max_x], showgrid=False),
        yaxis=dict(showticklabels=False),
        margin=dict(l=0, r=10, t=5, b=25),
        height=50,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "white"}
    )

    return dcc.Graph(figure=fig, config={'displayModeBar': False}, style={"height": "50px", "width": "100%"})


@app.callback(
    Output('protein-chart-container', 'children'),
    Input('target-protein', 'value'),
    Input('tolerance-protein', 'value'),
    Input('optimization-results-store', 'data')
)
def update_protein_chart(target_prot, tol_prot, results_data):
    """Generate protein range chart with optional solution line."""
    if not target_prot or not tol_prot:
        return None

    target_prot = float(target_prot)
    tol_prot = float(tol_prot)

    # Get solution if available
    sol_prot = None
    if results_data and 'stats' in results_data:
        sol_prot = results_data['stats'].get('protein')

    # X-axis range: target range should be 90% of graph width
    range_start = target_prot - tol_prot
    range_end = target_prot + tol_prot
    range_width = range_end - range_start

    # Add 5% padding on each side so range spans 90% of graph
    padding = range_width * (0.05 / 0.9)
    min_x = range_start - padding
    max_x = range_end + padding

    # Extend if solution is outside range
    if sol_prot:
        if sol_prot < min_x:
            min_x = sol_prot - padding
        if sol_prot > max_x:
            max_x = sol_prot + padding

    fig = go.Figure()
    fig.add_trace(go.Bar(x=[0], y=[""], orientation='h',
                  marker_color='rgba(0,0,0,0)', showlegend=False))

    # Target Range
    fig.add_shape(type="rect",
                  x0=range_start, x1=range_end,
                  y0=-0.4, y1=0.4,
                  line=dict(width=0),
                  fillcolor="rgba(0, 204, 150, 0.3)")

    # Solution Line (if available)
    if sol_prot:
        fig.add_shape(type="line",
                      x0=sol_prot, x1=sol_prot,
                      y0=-0.4, y1=0.4,
                      line=dict(color="#00cc96", width=5))

    fig.update_layout(
        xaxis=dict(range=[min_x, max_x], showgrid=False),
        yaxis=dict(showticklabels=False),
        margin=dict(l=0, r=10, t=5, b=25),
        height=50,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "white"}
    )

    return dcc.Graph(figure=fig, config={'displayModeBar': False}, style={"height": "50px", "width": "100%"})


# =============================================================================
# Ingredients Editor Logic
# =============================================================================


@app.callback(
    Output('ingredients-table', 'data'),
    Input('add-ingredient-btn', 'n_clicks'),
    State('ingredients-table', 'data'),
    prevent_initial_call=True
)
def add_ingredient_row(n_clicks, rows):
    if not n_clicks:
        return dash.no_update
    if rows is None:
        rows = []
    # Add empty row with default values
    rows.insert(0, {
        'name': 'New Ingredient',
        'cal_d': 0, 'prot_d': 0, 'carbs_d': 0, 'fat_d': 0, 'price': 0, 'pack_size': 0
    })
    return rows


@app.callback(
    Output('ingredients-status-msg', 'children'),
    Input('save-ingredients-btn', 'n_clicks'),
    State('ingredients-table', 'data'),
    prevent_initial_call=True
)
def save_ingredients_changes(n_clicks, rows):
    if not n_clicks or not rows:
        return dash.no_update

    data_manager.update_database(rows)
    return "✅ Saved successfully!"


# =============================================================================
# Cookbook Actions (Add / Delete / Rename)
# =============================================================================

# 1. Open/Close ADd Modal
@app.callback(
    Output("add-recipe-modal", "is_open"),
    Input("add-recipe-btn", "n_clicks"),
    Input("add-recipe-confirm", "n_clicks"),
    Input("add-recipe-cancel", "n_clicks"),
    State("add-recipe-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_add_modal(n1, n2, n3, is_open):
    if n1 or n2 or n3:
        return not is_open
    return is_open

# 2. Add Recipe Confirmation -> Refresh Page


@app.callback(
    # Trigger page reload by forcing simple refresh? Or just set pathname to same?
    Output('cookbook-refresh-trigger', 'data'),
    Input('add-recipe-confirm', 'n_clicks'),
    Input('rename-recipe-confirm', 'n_clicks'),
    Input({'type': 'delete-recipe-btn', 'index': ALL}, 'n_clicks'),
    State('new-recipe-name', 'value'),
    State('rename-recipe-input', 'value'),
    State('rename-recipe-id-store', 'data'),
    # Get current value to increment
    State('cookbook-refresh-trigger', 'data'),
    prevent_initial_call=True
)
def handle_cookbook_actions(add_clicks, rename_clicks, delete_clicks, new_name, rename_name, rename_id, current_refresh_data):
    if current_refresh_data is None:
        current_refresh_data = 0

    triggered_id = ctx.triggered_id
    if not triggered_id:
        return dash.no_update

    # ADD RECIPE
    if triggered_id == 'add-recipe-confirm':
        if not new_name:
            return dash.no_update

        # Create ID
        r_id = str(uuid.uuid4())[:8]
        new_recipe = {
            "name": new_name,
            "ingredients": [],
            "portions": 1
        }
        recipe_manager.add_recipe(r_id, new_recipe)
        return current_refresh_data + 1

    # RENAME RECIPE
    if triggered_id == 'rename-recipe-confirm':
        if rename_id and rename_name:
            r = recipe_manager.get_recipe(rename_id)
            if r:
                r['name'] = rename_name
                recipe_manager.add_recipe(rename_id, r)
                return current_refresh_data + 1

    # DELETE RECIPE
    # Check if delete button was clicked
    # triggered_id is a dict for pattern matched callbacks
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'delete-recipe-btn':
        # Check that value is not None (initial load)
        # We find the value in ctx.triggered for this specific ID
        # Dash sometimes minimizes spaces in prop_id, but safer to loop
        ids_prop_id = str(triggered_id).replace(" ", "")

        is_valid_click = False
        for t in ctx.triggered:
            # t['value'] is the n_clicks
            if t['value'] is not None and t['value'] > 0:
                is_valid_click = True
                break

        if not is_valid_click:
            return dash.no_update

        r_id = triggered_id.get('index')
        recipe_manager.delete_recipe(r_id)
        return current_refresh_data + 1

    return dash.no_update

# 3. Open Rename Modal


@app.callback(
    Output("rename-recipe-modal", "is_open"),
    Output("rename-recipe-input", "value"),
    Output("rename-recipe-id-store", "data"),
    Input({'type': 'rename-recipe-btn', 'index': ALL}, 'n_clicks'),
    Input("rename-recipe-confirm", "n_clicks"),
    Input("rename-recipe-cancel", "n_clicks"),
    State("rename-recipe-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_rename_modal(edit_clicks, save_clicks, cancel_clicks, is_open):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return dash.no_update

    # Reset/Close
    # triggered_id is string here
    if triggered_id == 'rename-recipe-confirm' or triggered_id == 'rename-recipe-cancel':
        return False, dash.no_update, dash.no_update

    # Open
    # triggered_id is dict here
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'rename-recipe-btn':
        r_id = triggered_id.get('index')
        r = recipe_manager.get_recipe(r_id)
        if r:
            return True, r.get('name', ''), r_id

    return dash.no_update

# Stores optimization results in memory (client-side store) so both pages can access
# We need a new store for this? Or just push to layout?
# The request asks to "display individual recipes in results page".
# Since optimization happens on the Optimizer page, we need to Store the results
# so the user can navigate to Results page and see them.


@app.callback(
    Output("macro-result-bar", "children"),
    Output("optimization-results-store", "data"),
    Output("optimization-status-output", "children"),
    Input("run-optimization-btn", "n_clicks"),
    State("settings-store", "data"),
    State("selected-recipes-store", "data"),
    prevent_initial_call=True
)
def run_global_optimization(n_clicks, settings_data, selected_ids):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update

    if not selected_ids:
        return dash.no_update, dash.no_update, dbc.Alert("No recipes selected! Go to Cookbook.", color="warning")

    # 1. Load Data
    active_recipes = []
    for r_id in selected_ids:
        r = recipe_manager.get_recipe(r_id)
        if r:
            # Inject ID for internal use without modifying persistent store
            r_with_id = r.copy()
            r_with_id['id'] = r_id
            active_recipes.append(r_with_id)

    if not active_recipes:
        return dash.no_update, dash.no_update, dbc.Alert("Selected recipes not found in DB.", color="danger")

    ingredient_db = data_manager.get_all_ingredients()

    # 2. Build Targets
    settings_data = settings_data or {}
    target_prot = settings_data.get('prot', 160)
    target_cal = settings_data.get('cal', 2200)
    tol_prot = settings_data.get('tol_prot', 5)
    tol_cal = settings_data.get('tol_cal', 50)
    min_meal_cal = settings_data.get('min_meal_cal', 300)
    max_meal_cal = settings_data.get('max_meal_cal', 1000)

    targets = {}

    # Store per-meal constraints
    targets['min_meal_cal'] = float(
        min_meal_cal) if min_meal_cal is not None else 300.0
    targets['max_meal_cal'] = float(
        max_meal_cal) if max_meal_cal is not None else 1000.0
    if target_cal:
        targets['cal'] = float(target_cal)
        targets['delta_cal'] = float(tol_cal or 50)
    if target_prot:
        targets['prot'] = float(target_prot)
        targets['delta_prot'] = float(tol_prot or 5)

    # 3. Run Solver
    # updates is {r_id: {row_idx: amount}}
    updates, stats = solve_global_plan(active_recipes, ingredient_db, targets)

    if updates is None and stats and 'error' in stats:
        return dash.no_update, dash.no_update, dbc.Alert(f"Optimization Failed: {stats['error']}", color="danger")

    # 4. Process Results for Charts & Storage
    recipe_breakdown = {}

    # We calculate the stats again later for the detailed view, but we need aggregated stats here for the charts
    # and we need to save the 'updates' to the store.

    # Re-calculate breakdown for charts
    old_recipes_map = {r['id']: r for r in active_recipes}

    for r_id, row_map in updates.items():
        old_r = old_recipes_map.get(r_id)
        if not old_r:
            continue

        old_ingredients = old_r.get('ingredients', [])

        for idx, new_amount in row_map.items():
            if idx < len(old_ingredients):
                ing_name = old_ingredients[idx].get('name')

                ing_info = ingredient_db.get(ing_name, {})
                c_d = ing_info.get('cal_d', 0)
                p_d = ing_info.get('prot_d', 0)
                portions = float(old_r.get('portions', 1))
                if portions <= 0:
                    portions = 1

                c_contrib_new = (new_amount / 100.0 * c_d) / portions
                p_contrib_new = (new_amount / 100.0 * p_d) / portions

                if r_id not in recipe_breakdown:
                    recipe_breakdown[r_id] = {
                        'name': old_r.get('name', 'Unknown'),
                        'cal': 0.0, 'prot': 0.0
                    }
                recipe_breakdown[r_id]['cal'] += c_contrib_new
                recipe_breakdown[r_id]['prot'] += p_contrib_new

    # Macros Distribution - HTML Div Bar (matching left side)
    prot_cals = stats.get('protein', 0) * 4
    carbs_cals = stats.get('carbs', 0) * 4
    fat_cals = stats.get('fat', 0) * 9

    # Calculate raw percentages
    total_macro_cals = prot_cals + carbs_cals + fat_cals
    if total_macro_cals > 0:
        s_p_pct = (prot_cals / total_macro_cals) * 100
        s_c_pct = (carbs_cals / total_macro_cals) * 100
        s_f_pct = (fat_cals / total_macro_cals) * 100
    else:
        s_p_pct = s_c_pct = s_f_pct = 0

    # Create HTML bar segments (like on left side)
    def make_result_bar(val, bg_color, label_text):
        if val <= 0:
            return None
        return html.Div(
            label_text if val > 8 else "",
            style={
                "width": f"{val}%",
                "backgroundColor": bg_color,
                "height": "100%",
                "display": "inline-block",
                "textAlign": "center",
                "lineHeight": "30px",
                "fontSize": "0.85rem",
                "fontWeight": "bold",
                "color": "white"
            }
        )

    macro_bar_children = [
        make_result_bar(s_p_pct, "#00cc96", f"{s_p_pct:.0f}%"),
        make_result_bar(s_c_pct, "#AB63FA", f"{s_c_pct:.0f}%"),
        make_result_bar(s_f_pct, "#FFA15A", f"{s_f_pct:.0f}%")
    ]
    macro_bar_children = [b for b in macro_bar_children if b is not None]

    # Package data for Store (include stats for chart updates)
    results_payload = {
        'updates': updates,
        'selected_ids': selected_ids,
        'stats': {
            'calories': stats.get('calories'),
            'protein': stats.get('protein'),
            'carbs': stats.get('carbs'),
            'fat': stats.get('fat')
        }
    }

    return macro_bar_children, results_payload, dbc.Alert("Optimization Calculated! (Now go to Results)", color="success", dismissable=True)


# =============================================================================
# State Management: Cookbook <-> Selected Store
# =============================================================================

# 1. Update Store when Checkboxes Change
@app.callback(
    Output('selected-recipes-store', 'data'),
    Input({'type': 'recipe-select', 'index': ALL}, 'value'),
    State({'type': 'recipe-select', 'index': ALL}, 'id'),
    State('selected-recipes-store', 'data'),
    prevent_initial_call=True
)
def update_selected_recipes(values, ids, current_data):
    if current_data is None:
        current_data = []

    selected_set = set(current_data)

    for val, comp_id in zip(values, ids):
        r_id = comp_id['index']
        if val:
            selected_set.add(r_id)
        elif r_id in selected_set:
            selected_set.remove(r_id)

    return list(selected_set)

# 2. Hydration handled in display_page via direct layout generation
# Old hydrate_checkboxes callback removed


# =============================================================================
# Planner Logic: Store -> Tabs
# =============================================================================
@app.callback(
    Output('planner-tabs-container', 'children'),
    Input('url', 'pathname'),
    State('selected-recipes-store', 'data')
)
def render_planner_tabs(pathname, selected_ids):
    if pathname != '/planner' or not selected_ids:
        if pathname == '/planner':
            return html.Div("No recipes selected. Go to Cookbook to add some!", className="text-center mt-5 text-muted")
        return dash.no_update

    tabs = []
    ign_opts = get_ingredient_options()

    # Sort to keep tab order consistent
    sorted_ids = sorted(selected_ids)

    for r_id in sorted_ids:
        recipe = recipe_manager.get_recipe(r_id)
        if not recipe:
            continue

        tab_content = create_recipe_tab_content(r_id, recipe, ign_opts)

        tabs.append(dbc.Tab(
            tab_content,
            label=recipe.get('name', 'Recipe'),
            tab_id=r_id,
            label_style={"color": "#fff"}
        ))

    return dbc.Tabs(tabs)


# =============================================================================
# Planner Interactivity (Add/Remove Ingredients)
# =============================================================================


@app.callback(
    Output({'type': 'recipe-tab-rows', 'recipe_id': MATCH}, 'children'),
    Input({'type': 'add-ing-btn', 'recipe_id': MATCH}, 'n_clicks'),
    Input({'type': 'remove-ingredient',
          'recipe_id': MATCH, 'row_id': ALL}, 'n_clicks'),
    State({'type': 'recipe-tab-rows', 'recipe_id': MATCH}, 'children'),
    prevent_initial_call=True
)
def update_recipe_tab_ingredients(add_click, remove_clicks, current_children):
    """
    Manages ingredients for a SINGLE recipe tab.
    Uses MATCH to isolate logic per recipe.
    Persists Add/Remove actions to disk immediately.
    """
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update

    if current_children is None:
        current_children = []

    recipe_id = triggered.get('recipe_id')

    # Load current recipe data from disk to ensure sync
    current_recipe = recipe_manager.get_recipe(recipe_id)
    if not current_recipe:
        # Should not happen ideally
        return dash.no_update

    current_ingredients = current_recipe.get('ingredients', [])

    if isinstance(triggered, dict) and triggered.get('type') == 'add-ing-btn':
        # Add a new row
        import uuid
        row_id = str(uuid.uuid4())[:8]  # Unique ID for the new row

        ign_opts = get_ingredient_options()
        new_row = create_ingredient_row(
            recipe_id, row_id, ign_opts, is_planner=True)

        # Add empty ingredient to DB
        new_ing_data = {
            "name": "",
            "amount": None,
            "priority": 1,
            "locked": False,
            "pkg_locked": False
        }
        current_ingredients.append(new_ing_data)
        current_recipe['ingredients'] = current_ingredients
        recipe_manager.add_recipe(recipe_id, current_recipe)

        return current_children + [new_row]

    elif isinstance(triggered, dict) and triggered.get('type') == 'remove-ingredient':
        target_row_id = triggered.get('row_id')

        new_children = []
        removed_index = -1

        for i, row in enumerate(current_children):
            try:
                row_props_id = row['props']['id']
                if row_props_id.get('row_id') == target_row_id:
                    removed_index = i
                    continue  # Skip adding this row to new_children
                new_children.append(row)
            except Exception:
                new_children.append(row)

        # Remove from DB if found
        if removed_index != -1 and removed_index < len(current_ingredients):
            current_ingredients.pop(removed_index)
            current_recipe['ingredients'] = current_ingredients
            recipe_manager.add_recipe(recipe_id, current_recipe)

        return new_children

    return dash.no_update


@app.callback(
    Output({'type': 'save-status', 'recipe_id': MATCH}, 'children'),
    Input({'type': 'ingredient-amount', 'recipe_id': MATCH, 'row_id': ALL}, 'value'),
    Input({'type': 'ingredient-name', 'recipe_id': MATCH, 'row_id': ALL}, 'value'),
    Input({'type': 'ingredient-priority',
          'recipe_id': MATCH, 'row_id': ALL}, 'value'),
    Input({'type': 'ingredient-lock', 'recipe_id': MATCH, 'row_id': ALL}, 'color'),
    Input({'type': 'package-lock', 'recipe_id': MATCH, 'row_id': ALL}, 'color'),
    Input({'type': 'recipe-portions', 'recipe_id': MATCH}, 'value'),
    prevent_initial_call=True
)
def save_recipe_changes(amounts, names, priorities, lock_colors, pkg_lock_colors, portions):
    """
    Auto-saves INDIVIDUAL INGREDIENT edits and PORTIONS to disk.
    Triggered whenever any ingredient input or portions input in the recipe tab changes.
    """
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update

    recipe_id = triggered.get('recipe_id')
    current_recipe = recipe_manager.get_recipe(recipe_id)

    if not current_recipe:
        return dash.no_update

    # Check if portions triggered the callback
    if triggered.get('type') == 'recipe-portions':
        if portions is None or portions == "":
            return dash.no_update

        try:
            new_portions = float(portions)
        except ValueError:
            new_portions = 1.0

        current_recipe['portions'] = new_portions
        recipe_manager.add_recipe(recipe_id, current_recipe)
        return f"Saved Portions: {new_portions}"

    # Ingredient update
    # Reconstruct ingredients list
    new_ingredients = []

    for amt, name, prio, l_col, p_col in zip(amounts, names, priorities, lock_colors, pkg_lock_colors):
        ing = {
            "name": name if name else "",
            "amount": amt if amt is not None else 0,
            "priority": prio if prio is not None else 1,
            "locked": (l_col == "primary"),
            "pkg_locked": (p_col == "primary")
        }
        new_ingredients.append(ing)

    current_recipe['ingredients'] = new_ingredients
    recipe_manager.add_recipe(recipe_id, current_recipe)

    return f"Last Saved: Items={len(new_ingredients)}"


# =============================================================================
# Lock Toggling Logic (Simplified with MATCH)
# =============================================================================


@app.callback(
    Output({'type': 'ingredient-lock', 'recipe_id': MATCH, 'row_id': MATCH}, 'color'),
    Output({'type': 'ingredient-lock', 'recipe_id': MATCH,
           'row_id': MATCH}, 'outline'),
    Input({'type': 'ingredient-lock', 'recipe_id': MATCH,
          'row_id': MATCH}, 'n_clicks'),
    State({'type': 'ingredient-lock', 'recipe_id': MATCH, 'row_id': MATCH}, 'color'),
    prevent_initial_call=True
)
def toggle_ingredient_lock(n_clicks, current_color):
    if not n_clicks:
        return dash.no_update

    if current_color == "secondary":
        return "primary", False
    return "secondary", True


@app.callback(
    Output({'type': 'package-lock', 'recipe_id': MATCH, 'row_id': MATCH}, 'color'),
    Output({'type': 'package-lock', 'recipe_id': MATCH,
           'row_id': MATCH}, 'outline'),
    Input({'type': 'package-lock', 'recipe_id': MATCH, 'row_id': MATCH}, 'n_clicks'),
    State({'type': 'package-lock', 'recipe_id': MATCH, 'row_id': MATCH}, 'color'),
    prevent_initial_call=True
)
def toggle_package_lock(n_clicks, current_color):
    if not n_clicks:
        return dash.no_update

    if current_color == "secondary":
        return "primary", False
    return "secondary", True


# =============================================================================
# Global Optimization
# =============================================================================


if __name__ == '__main__':
    app.run(debug=True)
