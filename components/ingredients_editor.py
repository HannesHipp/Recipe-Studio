from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash import Input, Output, State


def create_ingredients_editor_layout(data_manager):
    """
    Creates the Ingredients Editor page.
    Features a DataTable to edit all ingredient properties.
    """
    df = data_manager.get_table_data()

    # Columns for DataTable
    # We want specific ordering
    columns = [
        {'name': 'Ingredient Name', 'id': 'name', 'editable': True},
        {'name': 'Calories (kcal/100g)', 'id': 'cal_d',
         'type': 'numeric', 'editable': True},
        {'name': 'Protein (g/100g)', 'id': 'prot_d',
         'type': 'numeric', 'editable': True},
        {'name': 'Carbs (g/100g)', 'id': 'carbs_d',
         'type': 'numeric', 'editable': True},
        {'name': 'Fat (g/100g)', 'id': 'fat_d',
         'type': 'numeric', 'editable': True},
        {'name': 'Price (€)', 'id': 'price',
         'type': 'numeric', 'editable': True},
        {'name': 'Pack Size (g)', 'id': 'pack_size',
         'type': 'numeric', 'editable': True},
    ]

    return dbc.Container(
        [
            html.H2("Ingredients Editor 🥕", className="mb-4 mt-3"),

            dbc.Alert("Edits are local until you click Save via the main callback (to be implemented if needed, but DataTable usually updates state).",
                      color="info", is_open=False),  # Hidden for now

            dbc.Row([
                dbc.Col([
                    dbc.Button("Add Row", id="add-ingredient-btn",
                               color="primary", className="me-2"),
                    dbc.Button("Save Changes",
                               id="save-ingredients-btn", color="success"),
                ], className="mb-3"),
                dbc.Col([
                    html.Div(id="ingredients-status-msg",
                             className="text-end fw-bold text-success mt-2")
                ])
            ]),

            dash_table.DataTable(
                id='ingredients-table',
                columns=columns,
                data=df,
                editable=True,
                row_deletable=True,
                page_action='none',  # Scrollable
                style_table={'height': '70vh', 'overflowY': 'auto'},
                style_header={
                    'backgroundColor': 'rgb(30, 30, 30)',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data={
                    'backgroundColor': 'rgb(50, 50, 50)',
                    'color': 'white'
                },
                style_filter={
                    'backgroundColor': 'rgb(40, 40, 40)',
                    'color': 'white'
                },
                # Fix headers
                fixed_rows={'headers': True}
            )
        ],
        fluid=True
    )
