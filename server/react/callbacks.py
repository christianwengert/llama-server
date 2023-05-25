import secrets
from typing import List

import dash
from dash import Output, Input, State, html, dcc


def make_callbacks(app):
    @app.callback(
        Output("chat-input", "children"),
        Output("chat", "children"),
        Input("event-listener", "n_events"),
        State("event-listener", "event"),
        State("chat", "children"))
    def chat_input(_n, event, existing_chat):
        if event and event['key'] == 'Enter' and event['shiftKey']:
            if existing_chat is None:
                existing_chat = []
            return "", [
                *existing_chat,
                make_message(event['srcElement.innerText'].strip(), 'me'),
                dcc.Loading(make_message("bla", 'them')),
            ]

        return dash.no_update, dash.no_update


def make_message(message: str, direction: str) -> html.Div:
    message_id = secrets.token_hex(8)
    return html.Div([
        html.Div(message, className="inner-message")
    ], className=f"message from-{direction}", id=f'message-{message_id}')
