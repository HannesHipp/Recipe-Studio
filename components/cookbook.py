from dash import html, dcc
import dash_bootstrap_components as dbc


def create_cookbook_layout(recipe_manager, selected_ids=None):
    """
    Creates the Cookbook page layout.
    Lists all available recipes with checkboxes to select them for planning.
    """
    if selected_ids is None:
        selected_ids = []
    selected_set = set(selected_ids)

    recipes = recipe_manager.get_all_recipes()

    # Create Cards for grid view
    cards = []
    # Sort for consistent order (important for matching checkbox indices)
    sorted_ids = sorted(recipes.keys())

    for r_id in sorted_ids:
        r_data = recipes[r_id]
        card = dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Row([
                        dbc.Col(
                            dbc.Checkbox(
                                id={'type': 'recipe-select', 'index': r_id},
                                label=r_data.get('name', 'Unknown'),
                                value=(r_id in selected_set),
                                style={'fontWeight': 'bold',
                                       'fontSize': '1.1rem'}
                            ),
                            width=8, className="d-flex align-items-center"
                        ),
                        dbc.Col(
                            html.Div([
                                dbc.Button(html.I(className="fas fa-edit"),
                                           id={'type': 'rename-recipe-btn',
                                               'index': r_id},
                                           color="link", size="sm", className="text-muted p-0 me-2"),
                                dbc.Button(html.I(className="fas fa-trash-alt"),
                                           id={'type': 'delete-recipe-btn',
                                               'index': r_id},
                                           color="link", size="sm", className="text-danger p-0")
                            ], className="d-flex justify-content-end"),
                            width=4
                        )
                    ])
                ),
                dbc.CardBody(
                    [
                        html.Small(
                            f"{len(r_data.get('ingredients', []))} Ingredients"),
                    ]
                )
            ],
            className="mb-3",
            style={"height": "100%"}
        )
        cards.append(dbc.Col(card, width=12, md=6, lg=4))

    return dbc.Container(
        [
            dbc.Row([
                dbc.Col(html.H2("Cookbook 📖", className="mt-3"), width=8),
                dbc.Col(dbc.Button([html.I(className="fas fa-plus me-2"), "Add Recipe"],
                                   id="add-recipe-btn", color="primary", className="mt-3 float-end"), width=4)
            ], className="mb-4"),

            html.P("Select recipes to add to your daily planner.",
                   className="text-muted mb-4"),

            dbc.Row(cards),

            # --- MODALS ---
            # 1. Add Recipe Modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Add New Recipe")),
                dbc.ModalBody(
                    dbc.Input(
                        id="new-recipe-name", placeholder="Recipe Name (e.g. Pasta)", autoFocus=True)
                ),
                dbc.ModalFooter([
                    dbc.Button("Cancel", id="add-recipe-cancel",
                               className="ms-auto", n_clicks=0),
                    dbc.Button("Create", id="add-recipe-confirm",
                               color="success", n_clicks=0)
                ])
            ], id="add-recipe-modal", is_open=False),

            # 2. Rename Recipe Modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Rename Recipe")),
                dbc.ModalBody([
                    dbc.Input(id="rename-recipe-input", autoFocus=True),
                    # Stores the ID of recipe being renamed
                    dcc.Store(id="rename-recipe-id-store")
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancel", id="rename-recipe-cancel",
                               className="ms-auto", n_clicks=0),
                    dbc.Button("Save", id="rename-recipe-confirm",
                               color="primary", n_clicks=0)
                ])
            ], id="rename-recipe-modal", is_open=False),


            # Helper store to trigger URL refresh
            # dcc.Store(id='cookbook-refresh-trigger') - Removed, now in main.py
        ],
        fluid=True
    )
