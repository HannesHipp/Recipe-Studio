import dash_bootstrap_components as dbc
from dash import html


def create_sidebar():
    """
    Creates a detailed sidebar navigation.
    """
    sidebar_style = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#2b2b2b",
    }

    return html.Div(
        [
            html.H3("Meal Prep", className="display-6"),
            html.H3("Studio", className="display-6"),
            html.Hr(),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="fas fa-book-open me-2"), "Cookbook"],
                        href="/cookbook",
                        active="exact"
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-calendar-alt me-2"), "Planner"],
                        href="/planner",
                        active="exact"
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-sliders-h me-2"),
                         "Optimization"],
                        href="/optimizer",
                        active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-chart-pie me-2"), "Results"],
                        href="/results",
                        active="exact",
                        disabled=False
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-carrot me-2"), "Ingredients"],
                        href="/ingredients",
                        active="exact"
                    ),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        style=sidebar_style,
    )
