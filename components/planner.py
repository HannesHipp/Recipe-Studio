from dash import html, dcc
import dash_bootstrap_components as dbc
from .inputs import create_ingredient_row, create_ingredient_header


def create_planner_layout():
    """
    Creates the Planner page shell.
    The actual tabs are populated via callback based on selected recipes.
    """
    return dbc.Container(
        [
            html.H2("Daily Planner 📅", className="mb-4 mt-3"),
            html.Div(id='planner-tabs-container')
        ],
        fluid=True
    )


def create_recipe_tab_content(recipe_id, recipe_data, ingredient_options):
    """
    Creates the content for a single recipe tab.
    Reuses the ingredient row component logic.
    """
    ingredients = recipe_data.get('ingredients', [])

    rows = []
    for i, ing in enumerate(ingredients):
        # We use a simple index for initial load, but new rows will need UUIDs
        # to ensure uniqueness when adding/removing dynamic rows.
        row_id = str(i)

        # Pass is_planner=True to hide optimized column
        # Now passing separate recipe_id and row_id
        # Pass ingredient data for initial value population
        row = create_ingredient_row(
            recipe_id, row_id, ingredient_options, is_planner=True, initial_data=ing)
        rows.append(row)

    portions = recipe_data.get('portions', 1)

    return dbc.Card(
        dbc.CardBody(
            [
                # Controls Row (Add Ingredient + Portions)
                dbc.Row(
                    [

                        dbc.Col(
                            dbc.Button([html.I(className="fa fa-plus me-2"), "Add Ingredient"],
                                       id={'type': 'add-ing-btn',
                                           'recipe_id': recipe_id},
                                       size="sm", color="secondary", className="height-match-dropdown"),
                            width="auto"
                        ),
                        dbc.Col(
                            html.Div([
                                html.Label(
                                    "Portions:", className="me-2 small text-muted", style={'line-height': '38px'}),
                                dbc.Input(
                                    id={'type': 'recipe-portions',
                                        'recipe_id': recipe_id},
                                    value=portions,
                                    type="number",
                                    className="height-match-dropdown",
                                    style={'width': '80px',
                                           'display': 'inline-block'}
                                ),
                            ], className="d-flex align-items-center"),
                            width="auto",
                            className="ms-auto"
                        )
                    ],
                    className="mb-2 align-items-center"
                ),

                # Pass is_planner=True to hide optimized header
                create_ingredient_header(is_planner=True),
                # We wrap the rows in a Div with a specific ID to target it for adding/removing
                # DANGER: The ID must be unique per tab!
                html.Div(rows, id={'type': 'recipe-tab-rows',
                         'recipe_id': recipe_id}, className="planner-ingredients-list"),

                # Hidden Div for Ingredient Auto-Save
                html.Div(id={'type': 'save-status',
                         'recipe_id': recipe_id}, style={'display': 'none'}),

            ]
        ),
        className="mt-3 border-0"
    )
