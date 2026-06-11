from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd


def create_results_layout(optimization_data, recipe_manager, data_manager):
    """
    Creates the Results page.
    Args:
        optimization_data (dict): From optimization-results-store. Contains 'updates' and 'selected_ids'.
        recipe_manager: Global recipe manager instance.
        data_manager: Global data manager instance.
    """
    if not optimization_data or 'updates' not in optimization_data:
        return dbc.Container(
            [
                html.H2("Recipe Details 📝", className="mb-4 mt-3"),
                dbc.Alert(
                    "No optimization results found. Run Optimization first.", color="warning")
            ],
            fluid=True
        )

    updates = optimization_data['updates']
    selected_ids = optimization_data.get('selected_ids', [])

    detailed_cards = []
    # Should use get_all_ingredients
    ingredient_db = data_manager.get_all_ingredients()

    # 1. Load Original Recipes ("current state")
    # We need the active state. If we rely on recipe_manager, we get the disk state.
    # The 'updates' keys are recipe IDs.

    for r_id in selected_ids:
        # We process all selected IDs, check if they were updated
        # If not, maybe just show them unchanged? Or show only changed?
        # Let's show all selected.

        r = recipe_manager.get_recipe(r_id)
        if not r:
            continue

        row_map = updates.get(r_id, {})

        # Build comparison
        ingredients = r.get('ingredients', [])
        recipe_rows = []

        r_cal_old = 0
        r_prot_old = 0
        r_cal_new = 0
        r_prot_new = 0

        portions = float(r.get('portions', 1))
        if portions <= 0:
            portions = 1

        for idx, ing in enumerate(ingredients):
            ing_name = ing.get('name')
            old_amount = float(ing.get('amount') or 0)

            # New amount from updates, or keep old if not in updates
            # Note: Solver returns ALL variables usually, but if 'row_map' is partial, we assume others are unchanged?
            # Actually solver returns all variable ingredients.
            # keys in JSON might be strings if stored?
            new_amount = row_map.get(str(idx))
            if new_amount is None:
                new_amount = row_map.get(idx, old_amount)  # Try int key

            # Comparison
            if old_amount > 0.1:
                ratio = new_amount / old_amount
                pct_change = (ratio - 1) * 100
            else:
                pct_change = 100 if new_amount > 0 else 0

            # Stats
            ing_info = ingredient_db.get(ing_name, {})
            c_d = ing_info.get('cal_d', 0)
            p_d = ing_info.get('prot_d', 0)

            c_contrib_old = (old_amount / 100.0 * c_d) / portions
            p_contrib_old = (old_amount / 100.0 * p_d) / portions

            c_contrib_new = (new_amount / 100.0 * c_d) / portions
            p_contrib_new = (new_amount / 100.0 * p_d) / portions

            r_cal_old += c_contrib_old
            r_prot_old += p_contrib_old
            r_cal_new += c_contrib_new
            r_prot_new += p_contrib_new

            # Styling
            style_color = 'white'
            if pct_change > 20:
                style_color = '#EF553B'  # Red
            elif pct_change < -20:
                style_color = '#EF553B'
            elif abs(pct_change) < 1:
                style_color = '#6c757d'  # Muted for no change

            recipe_rows.append(
                html.Tr([
                    html.Td(ing_name.title()),
                    html.Td(f"{old_amount:.1f}"),
                    html.Td(f"{new_amount:.1f}", style={
                            'fontWeight': 'bold', 'color': '#00cc96'}),
                    html.Td(f"{pct_change:+.0f}%",
                            style={'color': style_color})
                ])
            )

        # Card
        card = dbc.Card([
            dbc.CardHeader(html.H5(r.get('name', 'Unknown'), className="m-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.Div(
                         [html.Strong("Calories: "), f"{r_cal_old:.0f} -> {r_cal_new:.0f}"]), width=6),
                    dbc.Col(html.Div(
                        [html.Strong("Protein: "), f"{r_prot_old:.1f} -> {r_prot_new:.1f}"]), width=6),
                ], className="mb-2 small"),
                html.Table(
                    [html.Thead(html.Tr([html.Th("Ing"), html.Th("Old"), html.Th("New"), html.Th("%")]))] +
                    [html.Tbody(recipe_rows)],
                    className="table table-sm table-dark table-borderless small"
                )
            ])
        ], className="mb-3 shadow-sm")

        detailed_cards.append(dbc.Col(card, width=12, lg=6, xl=4))

    return dbc.Container(
        [
            html.H2("Recipe Details 📝", className="mb-4 mt-3"),
            dbc.Row(detailed_cards)
        ],
        fluid=True
    )
