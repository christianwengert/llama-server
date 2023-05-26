from typing import List

from dash import html
from dash import dcc
from dash_extensions import EventListener
from models import MODELS, SELECTED_MODEL


def make_header(app_name: str) -> List[html.Div]:
    return [
        html.Div([
            html.A([
                html.Strong(app_name),
                "GPT"
            ], href="/", id="logo-link")
        ], className='header-inner'),
        html.Div([
            html.Label("Model", htmlFor='model-change'),
            dcc.Dropdown(options=list(MODELS.keys()),
                         value=SELECTED_MODEL,
                         id='model-change',
                         placeholder="Select a city", className='header-dropdown'),
            html.A(
                html.Img(src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiA/PjwhRE9DVFlQRSBzdmcgIFBVQkxJQyAnLS8vVzNDLy9EVEQgU1ZHIDEuMS8vRU4nICAnaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkJz48c3ZnIGVuYWJsZS1iYWNrZ3JvdW5kPSJuZXcgMCAwIDQxIDM0IiBoZWlnaHQ9IjM0cHgiIGlkPSJMYXllcl8xIiB2ZXJzaW9uPSIxLjEiIHZpZXdCb3g9IjAgMCA0MSAzNCIgd2lkdGg9IjQxcHgiIHhtbDpzcGFjZT0icHJlc2VydmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiPjxwYXRoIGQ9Ik0zMy45NDksMTZDMzMuNDI5LDcuMDgsMjYuMDUxLDAsMTcsMEM3LjYxMSwwLDAsNy42MTEsMCwxN3M3LjYxMSwxNywxNywxN3YtNmMtNi4wNzUsMC0xMS00LjkyNS0xMS0xMSAgUzEwLjkyNSw2LDE3LDZjNS43MzcsMCwxMC40NDMsNC4zOTQsMTAuOTQ5LDEwaC02Ljg0OUwzMSwyNS44OTlMNDAuODk5LDE2SDMzLjk0OXoiIGZpbGw9IiMyMzFGMjAiLz48L3N2Zz4=",
                         alt="refresh",
                         width="16",
                         height="16"
                         ),
                href="#",
                id="reset-button",
            )
        ], className='header-inner')
    ]



def make_layout(app_name: str) -> html.Div:
    return html.Div([

        html.Div(make_header(app_name), id="header"),
        html.Div(id='chat'),
        html.Div(id='chat-hidden', hidden=True),
        make_footer(),
        html.Div(id='empty')
    ])


CHAT_INPUT_EVENT = {
    "event": "keypress",
    "props": [
        # "srcElement.className",
        "srcElement.innerText",
        "key",
        "shiftKey",
    ]
}


def make_footer() -> html.Div:
    return html.Div([
        html.Div([
            EventListener(
                # html.Div(id='chat-input', contentEditable="true"),
                dcc.Textarea(id='chat-input', rows=1, cols=80, wrap='hard', placeholder="Chat here (Shift+Enter for newline)"),
                events=[CHAT_INPUT_EVENT],
                logging=False,
                id="event-listener"
            )
        ], id='footer-inner')
    ], id='footer')
