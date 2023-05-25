import os

from dash import Dash
import pandas as pd

from react.callbacks import make_callbacks
from react.layout import make_layout


APP_NAME = os.environ.get("CHAT_NAME", "local")


external_stylesheets = [
    # 'https://codepen.io/chriddyp/pen/bWLwgP.css',
    # '/static/main.css',
    '/static/dash.css'
]

app = Dash(__name__,
           external_scripts=[],
           external_stylesheets=external_stylesheets,
           title='gpt'
           )
app.index_string = open('templates/dash.html').read()

app.layout = make_layout(APP_NAME)


make_callbacks(app)


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)