from dash import html, dcc
import dash_bootstrap_components as dbc


def create_ingredient_header(is_planner=False):
    """
    Creates a descriptive header for the ingredient input columns.
    Args:
        is_planner (bool): If True, hides the 'Optimized g' column.
    """
    ing_width = 5 if is_planner else 5

    cols = [
        dbc.Col(html.Label("Amount"), width=2, className="px-1"),
        dbc.Col(html.Label("Ingredient"), width=ing_width, className="px-1"),
        dbc.Col(html.Label("Priority"), width=1, className="px-1"),
    ]

    if not is_planner:
        cols.append(dbc.Col(html.Label("Optimized g"),
                    width=2, className="text-end px-1"))

    return dbc.Row(
        cols,
        align="center",
        className="mb-2 text-muted small g-0"
    )


def create_ingredient_row(recipe_id, row_id, ingredient_options=None, is_planner=False, initial_data=None):
    """
    Creates a Dash Bootstrap component row for a single ingredient.

    Args:
        recipe_id: ID of the recipe this row belongs to (for MATCH pattern)
        row_id: Unique ID for this specific row (for ALL pattern filtering)
        ingredient_options: List of dicts [{'label': 'Chicken', 'value': 'chicken'}, ...]
        is_planner (bool): If True, hides the 'Optimized g' column.
        initial_data (dict): Dictionary containing initial values (amount, name, priority, locked, pkg_locked).
    """
    if ingredient_options is None:
        ingredient_options = []

    if initial_data is None:
        initial_data = {}

    amount = initial_data.get('amount')
    name = initial_data.get('name')
    priority = initial_data.get('priority', 1)
    locked = initial_data.get('locked', False)
    pkg_locked = initial_data.get('pkg_locked', False)

    # Helper for lock buttons
    def lock_style(is_locked):
        return ("primary", False) if is_locked else ("secondary", True)

    lock_color, lock_outline = lock_style(locked)
    pkg_color, pkg_outline = lock_style(pkg_locked)

    # Common ID pattern for this row's components
    def make_id(type_name):
        return {
            'type': type_name,
            'recipe_id': recipe_id,
            'row_id': row_id
        }

    ing_width = 5 if is_planner else 5

    cols = [
        dbc.Col(
            dbc.InputGroup([
                dbc.Input(placeholder="g", type="number", value=amount,
                          id=make_id('ingredient-amount'), className="height-match-dropdown"),
                dbc.Button(html.I(className="fa fa-lock"), id=make_id('ingredient-lock'), color=lock_color,
                           outline=lock_outline, size="sm", className="square-btn joined-middle-btn"),
                dbc.Button(html.I(className="fa fa-cubes"), id=make_id('package-lock'), color=pkg_color,
                           outline=pkg_outline, size="sm", className="square-btn joined-end-btn"),
            ], size="sm"),
            width=2, className="px-1"
        ),
        dbc.Col(
            dbc.InputGroup([
                dcc.Dropdown(
                    id=make_id('ingredient-name'),
                    options=ingredient_options,
                    value=name,
                    placeholder="Search ingredient...",
                    searchable=True,
                    clearable=False,
                    className="ingredient-dropdown joined-dropdown",
                    style={'flex': '1'}
                ),
                dbc.Button(html.I(className="fa fa-times"), id=make_id('remove-ingredient'), color="secondary",
                           outline=True, size="sm", className="square-btn joined-end-btn delete-btn-hover"),
            ], size="sm", className="d-flex w-100"),
            width=ing_width,
            className="px-1"
        ),
        dbc.Col(dbc.Input(placeholder="Prio", type="number", id=make_id(
            'ingredient-priority'), value=priority, min=0, className="height-match-dropdown"), width=1, className="px-1"),
    ]

    if not is_planner:
        cols.append(
            dbc.Col(dbc.Input(type="number", id=make_id(
                'optimized-value'), disabled=True), width=2, className="px-1")
        )

    return dbc.Row(
        cols,
        align="center",
        className="mb-2 g-0",
        id=make_id('ingredient-row')
    )
