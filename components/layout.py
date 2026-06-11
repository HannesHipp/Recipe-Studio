from dash import html, dcc
import dash_bootstrap_components as dbc
from .inputs import create_ingredient_header
from .graphs import create_summary_bar
from .modals import create_editor_modal


def create_layout(data_manager):
    """
    Assembles the main application layout.
    data_manager: Initialized DataManager instance.
    """

    # Pre-fetch data for the modal
    table_data = data_manager.get_table_data()

    return dbc.Container(
        [
            dcc.Store(id='optimized-recipe-data-store'),
            create_editor_modal(table_data),
            dbc.Row(
                [
                    # Left Column: Controls & Graphs
                    dbc.Col(
                        [
                            html.H4("Recipe Studio 🧪", className="mb-4"),

                            # Inputs Section
                            dbc.Row([
                                dbc.Col(html.Label(
                                    "Number of Portions"), width=5),
                                dbc.Col(dbc.Input(id="portions-input",
                                        type="number", value=1, min=1)),
                            ], align="center", className="mb-3"),

                            dbc.Row([
                                dbc.Col(html.Label(
                                    "Protein Goal (g)"), width=5),
                                dbc.Col(dbc.Input(
                                    id="protein-goal-input", type="number", placeholder="e.g., 30"), width=3),
                                dbc.Col(html.Span(
                                    "±"), width="auto", className="d-flex align-items-center justify-content-center"),
                                dbc.Col(dbc.Input(id="protein-slack-input",
                                        type="number", placeholder="5"), width=3),
                            ], align="center", className="mb-3"),

                            dbc.Row([
                                dbc.Col(html.Label(
                                    "Caloric Goal (kcal)"), width=5),
                                dbc.Col(dbc.Input(
                                    id="caloric-goal-input", type="number", placeholder="e.g., 500"), width=3),
                                dbc.Col(html.Span(
                                    "±"), width="auto", className="d-flex align-items-center justify-content-center"),
                                dbc.Col(dbc.Input(id="caloric-slack-input",
                                        type="number", placeholder="50"), width=3),
                            ], align="center", className="mb-4"),

                            # Graph Section
                            html.Div(dcc.Graph(
                                id="nutrition-graph", style={'height': '100%'}), style={'flexGrow': 1, 'minHeight': 0}),
                        ],
                        md=4,
                        className="p-4",
                        style={'height': '100%', 'display': 'flex',
                               'flexDirection': 'column', 'overflow': 'hidden'}
                    ),

                    # Right Column: Ingredient List
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

                            # Scrollable List
                            html.Div(
                                id="ingredient-list-container",
                                children=[],
                                className="scrollable-ingredients",
                                style={'overflowY': 'auto', 'flexGrow': 1}
                            ),

                            # Summary Footer
                            create_summary_bar()
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
