from dash import html, dcc
import dash_bootstrap_components as dbc


def create_optimizer_layout(settings_data=None):
    """
    Creates the Optimization page.
    Contains Settings, Run Button, and High-Level Charts.
    """
    if settings_data is None:
        settings_data = {}

    # Defaults
    def_prot = settings_data.get('prot', 160)
    def_cal = settings_data.get('cal', 2200)
    def_tol_prot = settings_data.get('tol_prot', 5)
    def_tol_cal = settings_data.get('tol_cal', 50)
    def_min_cal = settings_data.get('min_meal_cal', 300)
    def_max_cal = settings_data.get('max_meal_cal', 1000)
    def_include_cost = settings_data.get('include_cost', False)

    # Slider Defaults
    slider_data = settings_data.get('macro_slider', {})
    if isinstance(slider_data, dict):
        def_carbs = slider_data.get('carbs', 40)
        def_fat = slider_data.get('fat', 30)
    else:
        def_carbs = 40
        def_fat = 30

    return dbc.Container(
        [
            # Header Row with button on right
            dbc.Row([
                dbc.Col([
                    html.H2("Optimization ⚙️", className="mb-0 mt-3")
                ], width="auto"),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-magic me-2"),
                         "Run Optimization"],
                        id="run-optimization-btn",
                        color="success",
                        size="lg",
                        className="fw-bold mt-3"
                    )
                ], width="auto")
            ], className="mb-4 justify-content-between align-items-center"),

            dbc.Row([
                # Left Column: Inputs
                dbc.Col([
                    # 1. Daily Targets
                    dbc.Card([
                        dbc.CardHeader("Daily Targets"),
                        dbc.CardBody([

                            # Section A: Calories
                            html.Div([
                                html.H6(
                                    "Calories", className="text-secondary fw-bold mb-3"),
                                dbc.Row([
                                    # Left: Input controls
                                    dbc.Col([
                                        dbc.Row([
                                            dbc.Col(dbc.Label("Total Target"), width=3,
                                                    className="d-flex align-items-center"),
                                            dbc.Col(
                                                dbc.InputGroup([
                                                    dbc.Input(
                                                        id="target-calories", type="number", value=def_cal, step=10),
                                                    dbc.InputGroupText("±"),
                                                    dbc.Input(
                                                        id="tolerance-calories", type="number", value=def_tol_cal, step=10),
                                                ]), width=9
                                            )
                                        ])
                                    ], width=6),
                                    # Right: Chart container
                                    dbc.Col(
                                        html.Div(
                                            id="calories-chart-container",
                                            style={"overflow": "hidden",
                                                   "width": "100%"}
                                        ),
                                        width=6, className="d-flex align-items-center overflow-hidden"
                                    )
                                ], className="align-items-center g-0")
                            ], className="p-3 mb-3 border rounded border-light bg-black bg-opacity-25"),

                            # Section B: Macros
                            html.Div([
                                html.H6(
                                    "Macros", className="text-secondary fw-bold mb-3"),

                                # Protein (with chart on right)
                                dbc.Row([
                                    # Left: Input controls
                                    dbc.Col([
                                        dbc.Row([
                                            dbc.Col(dbc.Label("Protein (g)", style={"color": "#00cc96"}), width=3,
                                                    className="d-flex align-items-center"),
                                            dbc.Col(
                                                dbc.InputGroup([
                                                    dbc.Input(
                                                        id="target-protein", type="number", value=def_prot, step=1),
                                                    dbc.InputGroupText("±"),
                                                    dbc.Input(
                                                        id="tolerance-protein", type="number", value=def_tol_prot, step=1),
                                                ]), width=9
                                            )
                                        ])
                                    ], width=6),
                                    # Right: Chart container
                                    dbc.Col(
                                        html.Div(
                                            id="protein-chart-container",
                                            style={"overflow": "hidden",
                                                   "width": "100%"}
                                        ),
                                        width=6, className="d-flex align-items-center overflow-hidden"
                                    )
                                ], className="align-items-center mb-3 g-0"),

                                # Sliders row - sliders on left col, empty on right for alignment
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.Span("Carbs (%)", style={
                                                "color": "#AB63FA",
                                                "minWidth": "80px",
                                                "marginRight": "10px",
                                                "marginTop": "-15px"
                                            }),
                                            html.Div(
                                                dcc.Slider(
                                                    id='slider-carbs',
                                                    min=0, max=100, step=1,
                                                    value=def_carbs,
                                                    marks=None,
                                                    updatemode='drag',
                                                    className="slider-carbs"
                                                ),
                                                style={"flex": "1",
                                                       "marginTop": "10px"}
                                            )
                                        ], style={"display": "flex", "alignItems": "center", "marginBottom": "15px"}),

                                        html.Div([
                                            html.Span("Fat (%)", style={
                                                "color": "#FFA15A",
                                                "minWidth": "80px",
                                                "marginRight": "10px",
                                                "marginTop": "-20px"
                                            }),
                                            html.Div(
                                                dcc.Slider(
                                                    id='slider-fat',
                                                    min=0, max=100, step=1,
                                                    value=def_fat,
                                                    marks=None,
                                                    updatemode='drag',
                                                    className="slider-fat"
                                                ),
                                                style={"flex": "1",
                                                       "marginTop": "5px"}
                                            )
                                        ], style={"display": "flex", "alignItems": "center"})
                                    ], width=6),
                                    # Empty right column for alignment
                                    dbc.Col(width=6)
                                ], className="mb-3 g-0"),

                                # Distribution Bars - Target on left, Result on right
                                dbc.Row([
                                    dbc.Col(
                                        html.Div(
                                            id="macro-distribution-bar",
                                            style={
                                                "height": "30px",
                                                "backgroundColor": "#333",
                                                "borderRadius": "5px",
                                                "overflow": "hidden",
                                                "display": "flex",
                                                "flexDirection": "row"
                                            }
                                        ),
                                        width=6
                                    ),
                                    dbc.Col(
                                        html.Div(
                                            id="macro-result-bar",
                                            style={
                                                "height": "30px",
                                                "backgroundColor": "#333",
                                                "borderRadius": "5px",
                                                "overflow": "hidden",
                                                "display": "flex",
                                                "flexDirection": "row"
                                            }
                                        ),
                                        width=6
                                    )
                                ], className="g-0")
                            ], className="p-3 mb-3 border rounded border-light bg-black bg-opacity-25"),

                            # Section C: Micros
                            html.Div([
                                html.H6(
                                    "Micros", className="text-secondary fw-bold mb-2"),
                                html.Div(
                                    "Coming Soon", className="text-muted small fst-italic ms-1")
                            ], className="p-3 border rounded border-light bg-black bg-opacity-25")

                        ])
                    ], className="mb-4 shadow-sm"),

                    # 2. Settings
                    dbc.Card([
                        dbc.CardHeader("Settings"),
                        dbc.CardBody([
                            # Min/Max Kcal
                            dbc.Row([
                                dbc.Col(dbc.Label("Min Kcal/Meal"), width=6),
                                dbc.Col(dbc.Label("Max Kcal/Meal"), width=6),
                            ]),
                            dbc.Row([
                                dbc.Col(dbc.Input(
                                    id="min-meal-cal", type="number", value=def_min_cal, step=50), width=6),
                                dbc.Col(dbc.Input(
                                    id="max-meal-cal", type="number", value=def_max_cal, step=50), width=6),
                            ], className="mb-3"),

                            # Include Cost
                            dbc.Row([
                                dbc.Col(
                                    dbc.Switch(
                                        id="include-cost-toggle",
                                        label="Include Cost of Ingredients",
                                        value=def_include_cost,
                                    ), width=12
                                )
                            ]),
                        ])
                    ], className="mb-4 shadow-sm"),

                    # Status Alert
                    html.Div(id="optimization-status-output")

                ], width=12)
            ])
        ],
        fluid=True
    )
