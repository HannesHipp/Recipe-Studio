import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json
import os
from scipy.optimize import minimize, LinearConstraint
import numpy as np
from functools import partial

# For a nice, modern look, we'll use a Bootstrap theme and icons
# The CYBORG theme gives us a cool, dark "vibe code" aesthetic
app = dash.Dash(__name__, external_stylesheets=[
                dbc.themes.CYBORG, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"], suppress_callback_exceptions=True)

# =============================================================================
# Data Loading
# =============================================================================
INGREDIENTS_PATH = 'ingredients.json'
ingredient_db = {}


def load_and_prep_data():
    """Loads, lowercases, sorts, and re-saves the ingredients JSON."""
    global ingredient_db
    try:
        with open(INGREDIENTS_PATH, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        lowercase_data = {key.lower(): value for key, value in data.items()}
        ingredient_db = dict(sorted(lowercase_data.items()))
        with open(INGREDIENTS_PATH, 'w', encoding='utf-8-sig') as f_write:
            json.dump(ingredient_db, f_write, indent=4, ensure_ascii=False)
    except FileNotFoundError:
        print(
            f"WARNING: '{INGREDIENTS_PATH}' not found. Creating an empty database.")
        ingredient_db = {}
    except json.JSONDecodeError:
        print(
            f"WARNING: Could not decode JSON from '{INGREDIENTS_PATH}'. Using an empty database.")
        ingredient_db = {}


# Initial data load
load_and_prep_data()

# =============================================================================
# V1 Optimization Logic (Integrated into the script)
# =============================================================================


def get_nutrients_constraint(type, ingredients, orig_recipe, nutrients, num_portions):
    a = []
    for ingredient in orig_recipe:
        a.append(ingredients.get(ingredient, {}).get(f'{type}_d', 0) / 100.0)
    a = np.array(a)
    eps = nutrients[f'delta_{type}']
    b = nutrients[type] * num_portions
    return LinearConstraint(A=a, lb=b - eps, ub=b + eps)


def solve_optimization(recipe_vector, constraints, weights):
    result = minimize(
        partial(distance, recipe=recipe_vector, weights=weights),
        recipe_vector,
        method='SLSQP',
        constraints=constraints,
        bounds=[(0, None) for _ in recipe_vector]
    )
    if not result.success:
        print(f'Optimization failed: {result.message}')
        return None
    return result.x


def distance(x, recipe, weights):
    norm_recipe = np.linalg.norm(recipe)
    if norm_recipe == 0:
        return np.linalg.norm(np.sqrt(weights) * x)
    direction_norm = recipe / norm_recipe
    projection = np.dot(x, direction_norm) * direction_norm
    weighted_distance = np.linalg.norm(np.sqrt(weights) * (x - projection))
    return weighted_distance


def get_mass_constraint(constr_ingredient, orig_recipe, amount):
    a = []
    for ingredient in orig_recipe:
        a.append(1 if ingredient == constr_ingredient else 0)
    a = np.array(a)
    return LinearConstraint(A=a, lb=amount, ub=amount)

# =============================================================================
# UI Helper Functions & Layouts
# =============================================================================


def create_ingredient_row(index):
    """Creates a Dash Bootstrap component row for a single ingredient."""
    return dbc.Row(
        [
            dbc.Col(dbc.Button(html.I(className="fa fa-times"), id={'type': 'remove-ingredient', 'index': index}, color="danger",
                    outline=True, size="sm"), width=1, className="d-flex align-items-center justify-content-center px-1"),
            dbc.Col(dbc.Input(placeholder="g", type="number", id={
                    'type': 'ingredient-amount', 'index': index}), width=2, className="px-1"),
            dbc.Col(dbc.Input(placeholder="Name", type="text", id={
                    'type': 'ingredient-name', 'index': index}), width=4, className="px-1"),
            dbc.Col(dbc.Input(placeholder="Prio", type="number", id={
                    'type': 'ingredient-priority', 'index': index}, value=1, min=0), width=1, className="px-1"),
            dbc.Col(dbc.Button(html.I(className="fa fa-lock"), id={'type': 'ingredient-lock', 'index': index}, color="secondary",
                    outline=True, size="sm"), width=1, className="d-flex align-items-center justify-content-center px-1"),
            dbc.Col(dbc.Button(html.I(className="fa fa-cubes"), id={'type': 'package-lock', 'index': index}, color="secondary",
                    outline=True, size="sm"), width=1, className="d-flex align-items-center justify-content-center px-1"),
            dbc.Col(dbc.Input(type="number", id={
                    'type': 'optimized-value', 'index': index}, disabled=True), width=2, className="px-1"),
        ],
        align="center",
        className="mb-2 g-0",
        id={'type': 'ingredient-row', 'index': index}
    )


def create_ingredient_header():
    """Creates a descriptive header for the ingredient input columns."""
    return dbc.Row(
        [
            dbc.Col(width=1, className="px-1"),
            dbc.Col(html.Label("Amount"), width=2, className="px-1"),
            dbc.Col(html.Label("Ingredient"), width=4, className="px-1"),
            dbc.Col(html.Label("Priority"), width=1, className="px-1"),
            dbc.Col(html.Label("Lock"), width=1, className="text-center px-1"),
            dbc.Col(html.Label("Pkg"), width=1, className="text-center px-1"),
            dbc.Col(html.Label("Optimized g"), width=2,
                    className="text-end px-1"),
        ],
        align="center",
        className="mb-2 text-muted small g-0"
    )


def build_editor_modal():
    """Builds the full-screen modal for editing nutrients."""
    data_for_table = [{'name': key, **value}
                      for key, value in ingredient_db.items()]
    columns = [
        {'name': 'Ingredient', 'id': 'name', 'type': 'text'},
        {'name': 'Kcal/100g', 'id': 'cal_d', 'type': 'numeric'},
        {'name': 'Protein/100g', 'id': 'prot_d', 'type': 'numeric'},
        {'name': 'Fat/100g', 'id': 'fat_d', 'type': 'numeric'},
        {'name': 'Carbs/100g', 'id': 'carbs_d', 'type': 'numeric'},
        {'name': 'Price', 'id': 'price', 'type': 'numeric'},
        {'name': 'Package Size (g)', 'id': 'pack_size', 'type': 'numeric'},
    ]
    return dbc.Modal(
        [
            # MODIFIED: Moved buttons to the header
            dbc.ModalHeader(
                dbc.Row([
                    dbc.Col(dbc.ModalTitle("Nutrients Editor")),
                    dbc.Col(dbc.Button([html.I(className="fa fa-plus me-2"),
                            "Add Row"], id="add-row-btn", color="primary"), width="auto"),
                    dbc.Col(dbc.Button([html.I(className="fa fa-save me-2"), "Save & Close"],
                            id="save-changes-btn", color="success"), width="auto"),
                ], align="center")
            ),
            dbc.ModalBody(
                dash_table.DataTable(
                    id='nutrients-table',
                    columns=columns,
                    data=data_for_table,
                    editable=True,
                    row_deletable=True,
                    style_table={'height': '80vh', 'overflowY': 'auto'},
                    style_header={'backgroundColor': 'rgb(50, 50, 50)'},
                    style_cell={
                        'backgroundColor': 'rgb(70, 70, 70)', 'color': 'white'},
                )
            ),
            # MODIFIED: Removed the modal footer
        ],
        id="editor-modal",
        fullscreen=True,
        is_open=False,
    )


app.layout = dbc.Container(
    [
        dcc.Store(id='optimized-recipe-data-store'),
        build_editor_modal(),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4("Recipe Studio 🧪", className="mb-4"),
                        dbc.Row([
                            dbc.Col(html.Label("Number of Portions"), width=5),
                            dbc.Col(dbc.Input(id="portions-input",
                                    type="number", value=1, min=1)),
                        ], align="center", className="mb-3"),
                        dbc.Row([
                            dbc.Col(html.Label("Protein Goal (g)"), width=5),
                            dbc.Col(dbc.Input(id="protein-goal-input",
                                    type="number", placeholder="e.g., 30"), width=3),
                            dbc.Col(html.Span(
                                "±"), width="auto", className="d-flex align-items-center justify-content-center"),
                            dbc.Col(dbc.Input(id="protein-slack-input",
                                    type="number", placeholder="5"), width=3),
                        ], align="center", className="mb-3"),
                        dbc.Row([
                            dbc.Col(html.Label("Caloric Goal (kcal)"), width=5),
                            dbc.Col(dbc.Input(
                                id="caloric-goal-input", type="number", placeholder="e.g., 500"), width=3),
                            dbc.Col(html.Span(
                                "±"), width="auto", className="d-flex align-items-center justify-content-center"),
                            dbc.Col(dbc.Input(id="caloric-slack-input",
                                    type="number", placeholder="50"), width=3),
                        ], align="center", className="mb-4"),
                        html.Div(dcc.Graph(
                            id="nutrition-graph", style={'height': '100%'}), style={'flexGrow': 1, 'minHeight': 0}),
                    ],
                    md=4,
                    className="p-4",
                    style={'height': '100%', 'display': 'flex',
                           'flexDirection': 'column', 'overflow': 'hidden'}
                ),
                dbc.Col(
                    [
                        dbc.Row([
                            dbc.Col(dbc.Button([html.I(className="fa fa-plus me-2"), "Add New Ingredient"],
                                    id="add-ingredient-btn", color="primary", className="w-100"), width=4),
                            dbc.Col(dbc.Button([html.I(className="fa fa-magic-wand-sparkles me-2"),
                                    "Optimize Recipe"], id="optimize-btn", color="success", className="w-100"), width=4),
                            dbc.Col(dbc.Button([html.I(className="fa fa-external-link-alt me-2"), "Edit Nutrients Info"],
                                    id="edit-nutrients-btn", color="warning", className="w-100"), width=4)
                        ], className="mb-3"),
                        create_ingredient_header(),
                        html.Hr(className="mt-0"),
                        html.Div(
                            id="ingredient-list-container",
                            children=[],
                            className="scrollable-ingredients",
                            style={'overflowY': 'auto', 'flexGrow': 1}
                        ),
                        html.Div([
                            html.Hr(),
                            dbc.Row([
                                dbc.Col(html.Div([html.Span("Kcal ", style={'color': '#ff7f50'}), html.I(className="fa fa-fire me-2", style={
                                        'color': '#ff7f50'}), html.Span(id='total-kcal', children="0.0")]), className="text-center"),
                                dbc.Col(html.Div([html.Span("Protein ", style={'color': '#8B4513'}), html.I(className="fa fa-drumstick-bite me-2", style={
                                        'color': '#8B4513'}), html.Span(id='total-protein', children="0.0"), " g"]), className="text-center"),
                                dbc.Col(html.Div([html.Span("Fat ", style={'color': '#ffd700'}), html.I(className="fa fa-tint me-2", style={
                                        'color': '#ffd700'}), html.Span(id='total-fat', children="0.0"), " g"]), className="text-center"),
                                dbc.Col(html.Div([html.Span("Carbs ", style={'color': '#deb887'}), html.I(className="fa fa-bread-slice me-2", style={
                                        'color': '#deb887'}), html.Span(id='total-carbs', children="0.0"), " g"]), className="text-center"),
                                dbc.Col(html.Div([html.Span("Cost ", style={'color': '#90ee90'}), html.I(className="fa fa-euro-sign me-2", style={
                                        'color': '#90ee90'}), html.Span(id='total-cost', children="0.00")]), className="text-center"),
                            ])
                        ])
                    ],
                    md=8,
                    className="p-4",
                    style={'height': '100%', 'display': 'flex',
                           'flexDirection': 'column', 'overflow': 'hidden'}
                ),
            ],
            className="p-3",
            style={'flexGrow': 1, 'overflow': 'hidden'}
        ),
    ],
    fluid=True,
    style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column'}
)


# =============================================================================
# Callbacks
# =============================================================================

# Modal and Editor Callbacks
@app.callback(
    Output("editor-modal", "is_open"),
    # MODIFIED: Removed close button from inputs
    [Input("edit-nutrients-btn", "n_clicks"),
     Input("save-changes-btn", "n_clicks")],
    [State("editor-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output('nutrients-table', 'data'),
    Input('add-row-btn', 'n_clicks'),
    State('nutrients-table', 'data'),
    State('nutrients-table', 'columns'),
    prevent_initial_call=True
)
def add_row_to_table(n_clicks, rows, columns):
    if n_clicks:
        rows.append({c['id']: '' for c in columns})
    return rows


@app.callback(
    Output('edit-nutrients-btn', 'color'),  # Dummy output
    Input('save-changes-btn', 'n_clicks'),
    State('nutrients-table', 'data'),
    prevent_initial_call=True
)
def save_table_data(n_clicks, data):
    if n_clicks:
        new_db = {item['name']: {k: v for k, v in item.items() if k != 'name'}
                  for item in data if item.get('name')}
        with open(INGREDIENTS_PATH, 'w', encoding='utf-8-sig') as f:
            json.dump(new_db, f, indent=4, ensure_ascii=False)
        load_and_prep_data()
    return 'warning'

# Studio Callbacks


@app.callback(
    Output('ingredient-list-container', 'children'),
    Input('add-ingredient-btn', 'n_clicks'),
    Input({'type': 'remove-ingredient', 'index': ALL}, 'n_clicks'),
    State('ingredient-list-container', 'children'),
    prevent_initial_call=True
)
def update_ingredient_list(add_clicks, remove_clicks, current_rows):
    triggered_id = ctx.triggered_id
    if triggered_id == 'add-ingredient-btn':
        new_row_index = len(current_rows)
        new_row = create_ingredient_row(new_row_index)
        current_rows.append(new_row)
        return current_rows
    if isinstance(triggered_id, dict):
        index_to_remove = triggered_id['index']
        updated_rows = [row for row in current_rows if row.get(
            'props', {}).get('id', {}).get('index') != index_to_remove]
        return updated_rows
    return current_rows


@app.callback(
    Output({'type': 'ingredient-lock', 'index': ALL}, 'color'),
    Output({'type': 'ingredient-lock', 'index': ALL}, 'outline'),
    Input({'type': 'ingredient-lock', 'index': ALL}, 'n_clicks'),
    State({'type': 'ingredient-lock', 'index': ALL}, 'id'),
    State({'type': 'ingredient-lock', 'index': ALL}, 'color'),
    prevent_initial_call=True
)
def toggle_ingredient_locks(ing_clicks, ing_ids, ing_colors):
    triggered_id = ctx.triggered_id
    output = {id['index']: (color, color == "secondary")
              for id, color in zip(ing_ids, ing_colors)}
    def toggle(color): return (
        "primary", False) if color == "secondary" else ("secondary", True)
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'ingredient-lock':
        index = triggered_id['index']
        output[index] = toggle(output[index][0])
    ing_colors_out = [output[id['index']][0] for id in ing_ids]
    ing_outlines_out = [output[id['index']][1] for id in ing_ids]
    return ing_colors_out, ing_outlines_out


@app.callback(
    Output({'type': 'package-lock', 'index': ALL}, 'color'),
    Output({'type': 'package-lock', 'index': ALL}, 'outline'),
    Input({'type': 'package-lock', 'index': ALL}, 'n_clicks'),
    State({'type': 'package-lock', 'index': ALL}, 'id'),
    State({'type': 'package-lock', 'index': ALL}, 'color'),
    prevent_initial_call=True
)
def toggle_package_locks(pkg_clicks, pkg_ids, pkg_colors):
    triggered_id = ctx.triggered_id
    output = {id['index']: (color, color == "secondary")
              for id, color in zip(pkg_ids, pkg_colors)}
    def toggle(color): return (
        "primary", False) if color == "secondary" else ("secondary", True)
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'package-lock':
        index = triggered_id['index']
        output[index] = toggle(output[index][0])
    pkg_colors_out = [output[id['index']][0] for id in pkg_ids]
    pkg_outlines_out = [output[id['index']][1] for id in pkg_ids]
    return pkg_colors_out, pkg_outlines_out


@app.callback(
    Output({'type': 'ingredient-name', 'index': ALL}, 'className'),
    Input({'type': 'ingredient-name', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def validate_ingredient_names(names):
    class_names = []
    for name in names:
        if not name:
            class_names.append("")
            continue
        if name.lower() in ingredient_db:
            class_names.append("is-valid")
        else:
            class_names.append("is-invalid")
    return class_names


@app.callback(
    Output('nutrition-graph', 'figure'),
    Input({'type': 'ingredient-amount', 'index': ALL}, 'value'),
    Input({'type': 'ingredient-name', 'index': ALL}, 'value'),
    Input('protein-goal-input', 'value'),
    Input('caloric-goal-input', 'value'),
    Input('portions-input', 'value'),
    Input('protein-slack-input', 'value'),
    Input('caloric-slack-input', 'value'),
    Input('optimized-recipe-data-store', 'data'),
)
def update_graph(amounts, names, protein_goal, caloric_goal, portions, protein_slack, caloric_slack, optimized_data):
    total_protein, total_calories = 0, 0
    for amount, name in zip(amounts, names):
        if name and name.lower() in ingredient_db:
            try:
                info = ingredient_db[name.lower()]
                amount_f = float(amount or 0)
                total_calories += (amount_f / 100.0) * info['cal_d']
                total_protein += (amount_f / 100.0) * info['prot_d']
            except (ValueError, TypeError):
                continue

    try:
        num_portions = float(portions or 1)
        if num_portions <= 0:
            num_portions = 1
    except (ValueError, TypeError):
        num_portions = 1

    protein_per_portion = total_protein / num_portions if num_portions > 0 else 0
    calories_per_portion = total_calories / num_portions if num_portions > 0 else 0

    fig = go.Figure()
    p_goal_f, c_goal_f = float(protein_goal or 0), float(caloric_goal or 0)
    p_slack_f, c_slack_f = float(protein_slack or 0), float(caloric_slack or 0)

    fig.add_trace(go.Scatter(x=[p_goal_f - p_slack_f, p_goal_f + p_slack_f, p_goal_f + p_slack_f, p_goal_f - p_slack_f, p_goal_f - p_slack_f], y=[c_goal_f - c_slack_f, c_goal_f - c_slack_f,
                  c_goal_f + c_slack_f, c_goal_f + c_slack_f, c_goal_f - c_slack_f], fill="toself", fillcolor='rgba(255,215,0,0.2)', line=dict(color='rgba(255,255,255,0)'), hoverinfo="none", name='Goal Zone'))
    fig.add_trace(go.Scatter(x=[protein_per_portion], y=[calories_per_portion],
                  mode='markers', name='Current Recipe', marker=dict(color='cyan', size=15)))

    if optimized_data:
        fig.add_trace(go.Scatter(
            x=[optimized_data.get('protein')],
            y=[optimized_data.get('calories')],
            mode='markers',
            name='Optimized Recipe',
            marker=dict(color='#90ee90', size=15, symbol='star')
        ))

    max_x = max(p_goal_f + p_slack_f, protein_per_portion,
                optimized_data.get('protein', 0) if optimized_data else 0)
    max_y = max(c_goal_f + c_slack_f, calories_per_portion,
                optimized_data.get('calories', 0) if optimized_data else 0)

    range_x_max = max(max_x, 50) * 1.2
    range_y_max = max(max_y, 500) * 1.2

    fig.update_layout(
        title=None,
        xaxis_title="Protein (g)",
        yaxis_title="Calories (kcal)",
        template="plotly_dark",
        xaxis=dict(range=[0, range_x_max]),
        yaxis=dict(range=[0, range_y_max]),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=40, r=10, t=10, b=40)
    )

    return fig


@app.callback(
    Output({'type': 'optimized-value', 'index': ALL}, 'value'),
    Output('optimized-recipe-data-store', 'data'),
    Input('optimize-btn', 'n_clicks'),
    State({'type': 'ingredient-amount', 'index': ALL}, 'value'),
    State({'type': 'ingredient-name', 'index': ALL}, 'value'),
    State({'type': 'ingredient-priority', 'index': ALL}, 'value'),
    State('protein-goal-input', 'value'),
    State('caloric-goal-input', 'value'),
    State('protein-slack-input', 'value'),
    State('caloric-slack-input', 'value'),
    State('portions-input', 'value'),
    State({'type': 'ingredient-lock', 'index': ALL}, 'color'),
    State({'type': 'package-lock', 'index': ALL}, 'color'),
    prevent_initial_call=True
)
def optimize_recipe(n_clicks, amounts, names, priorities, protein_goal, caloric_goal, protein_slack, caloric_slack, portions, ing_lock_colors, pkg_lock_colors):
    valid_indices = [i for i, name in enumerate(
        names) if name and name.lower() in ingredient_db]
    if not valid_indices:
        return ["" for _ in names], None

    orig_recipe = {names[i].lower(): float(amounts[i] or 0)
                   for i in valid_indices}
    weights_dict = {names[i].lower(): float(priorities[i] or 1)
                    for i in valid_indices}

    nutrients = {
        'cal': float(caloric_goal or 0),
        'prot': float(protein_goal or 0),
        'delta_cal': float(caloric_slack or 0),
        'delta_prot': float(protein_slack or 0)
    }
    num_portions = float(portions or 1)

    recipe_vector = np.asarray(list(orig_recipe.values()), dtype=float)
    weights_vector = np.asarray(list(weights_dict.values()), dtype=float)
    cal_constr = get_nutrients_constraint(
        'cal', ingredient_db, orig_recipe, nutrients, num_portions)
    prot_constr = get_nutrients_constraint(
        'prot', ingredient_db, orig_recipe, nutrients, num_portions)
    constraints = [cal_constr, prot_constr]

    for i, (name, color) in enumerate(zip(names, ing_lock_colors)):
        if color == "primary" and name.lower() in orig_recipe:
            constraints.append(get_mass_constraint(
                name.lower(), orig_recipe, float(amounts[i] or 0)))

    sol = solve_optimization(recipe_vector, constraints, weights_vector)
    if sol is None:
        return ["" for _ in names], None

    consider_size = [names[i].lower()
                     for i in valid_indices if pkg_lock_colors[i] == "primary"]
    if consider_size:
        package_constraints = []
        for index, ingredient in enumerate(orig_recipe):
            if ingredient in consider_size:
                size = ingredient_db[ingredient].get('pack_size', 1)
                amount = round(sol[index] / size) * size
                package_constraints.append(
                    get_mass_constraint(ingredient, orig_recipe, amount))

        sol = solve_optimization(
            recipe_vector, constraints + package_constraints, weights_vector)
        if sol is None:
            return ["" for _ in names], None

    sol = np.round(sol)
    optimized_values_dict = {name: val for name,
                             val in zip(orig_recipe.keys(), sol)}

    final_optimized_values = [f"{optimized_values_dict.get(name.lower(), ''):.1f}" if name and name.lower(
    ) in optimized_values_dict else "" for name in names]

    opt_total_kcal, opt_total_protein = 0, 0
    for name, amount in optimized_values_dict.items():
        info = ingredient_db[name]
        opt_total_kcal += (amount / 100.0) * info['cal_d']
        opt_total_protein += (amount / 100.0) * info['prot_d']

    opt_kcal_per_portion = opt_total_kcal / num_portions if num_portions > 0 else 0
    opt_protein_per_portion = opt_total_protein / \
        num_portions if num_portions > 0 else 0

    optimized_data = {'calories': opt_kcal_per_portion,
                      'protein': opt_protein_per_portion}

    return final_optimized_values, optimized_data


@app.callback(
    Output('total-kcal', 'children'),
    Output('total-protein', 'children'),
    Output('total-fat', 'children'),
    Output('total-carbs', 'children'),
    Output('total-cost', 'children'),
    Input({'type': 'optimized-value', 'index': ALL}, 'value'),
    State({'type': 'ingredient-name', 'index': ALL}, 'value'),
    State('portions-input', 'value'),
)
def update_summary_bar(optimized_amounts, names, portions):
    total_kcal, total_protein, total_fat, total_carbs, total_cost = 0, 0, 0, 0, 0

    for amount, name in zip(optimized_amounts, names):
        if name and name.lower() in ingredient_db:
            try:
                info = ingredient_db[name.lower()]
                amount_f = float(amount or 0)

                total_kcal += (amount_f / 100.0) * info['cal_d']
                total_protein += (amount_f / 100.0) * info['prot_d']
                total_fat += (amount_f / 100.0) * info['fat_d']
                total_carbs += (amount_f / 100.0) * info['carbs_d']
                total_cost += (amount_f / info['pack_size']) * info['price']

            except (ValueError, TypeError, KeyError):
                continue

    try:
        num_portions = float(portions or 1)
        if num_portions <= 0:
            num_portions = 1
    except (ValueError, TypeError):
        num_portions = 1

    kcal_per_portion = total_kcal / num_portions if num_portions > 0 else 0
    protein_per_portion = total_protein / num_portions if num_portions > 0 else 0
    fat_per_portion = total_fat / num_portions if num_portions > 0 else 0
    carbs_per_portion = total_carbs / num_portions if num_portions > 0 else 0
    cost_per_portion = total_cost / num_portions if num_portions > 0 else 0

    return (
        f"{kcal_per_portion:.0f}",
        f"{protein_per_portion:.1f}",
        f"{fat_per_portion:.1f}",
        f"{carbs_per_portion:.1f}",
        f"{cost_per_portion:.2f}"
    )


@app.callback(
    Output('optimized-recipe-data-store', 'data', allow_duplicate=True),
    Input({'type': 'ingredient-amount', 'index': ALL}, 'value'),
    Input({'type': 'ingredient-name', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def clear_optimization_on_edit(amounts, names):
    return None


# =============================================================================
# Run the App
# =============================================================================
if __name__ == '__main__':
    app.run(debug=True)
