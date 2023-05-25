from dash import Dash
import pandas as pd

from react.layout import create_layout

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

external_stylesheets = [
    # 'https://codepen.io/chriddyp/pen/bWLwgP.css',
    # '/static/main.css',
    '/static/dash.css'
]

app = Dash(__name__,
           external_scripts=[],
           external_stylesheets=external_stylesheets,
           title='hhho'
           )
app.index_string = open('templates/dash.html').read()

app.layout = create_layout()


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)