import os
from typing import Tuple, List

from dash import html
from dash.dcc import Dropdown

from models import MODELS, SELECTED_MODEL

APP_NAME = os.environ.get("CHAT_NAME", "local")


def header() -> List[html.Div]:
    return [
        html.Div([
            html.A([
                html.Strong(APP_NAME),
                "GPT"
            ], href="/", id="logo-link")
        ], className='header-inner'),
        html.Div([
            html.Label("Model", htmlFor='model-change'),
            Dropdown(options=list(MODELS.keys()),
                     value=SELECTED_MODEL,
                     id='model-change',
                     placeholder="Select a city", className='header-dropdown')
        ], className='header-inner')
    ]


def create_layout() -> html.Div:
    return html.Div([
        html.Div(header(),
                 id="header")
    ])
