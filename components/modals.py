from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc


def create_editor_modal(data_for_table):
    """
    Builds the full-screen modal for editing nutrients.
    data_for_table: list of dicts from DataManager.
    """
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
        ],
        id="editor-modal",
        fullscreen=True,
        is_open=False,
    )
