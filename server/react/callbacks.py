import secrets
from math import ceil

import dash
from dash import Output, Input, State, html, dcc


def make_callbacks(app):
    @app.callback(
        Output("chat", "children"),
        Output("chat-input", "value"),
        Output("chat-hidden", "children"),
        Input("event-listener", "n_events"),
        State("event-listener", "event"),
        State("chat", "children"),
        State("chat-input", "value"))
    def chat_input(_n, event, existing_chat, chat_input):
        if event and event['key'] == 'Enter' and not event['shiftKey']:
            if existing_chat is None:
                existing_chat = []

            return [
                *existing_chat,
                make_message(chat_input.strip(), 'me'),
                dcc.Loading(make_message("bla", 'them')),
            ], ""

        return dash.no_update, dash.no_update, _n

    @app.callback(
        Output("chat-input", "rows"),
        Input("chat-hidden", "children"),
        State("chat-input", "value"),
        State("chat-input", "cols"),
        State("chat-input", "wrap"),
    )
    def grow_textarea(_x, text, cols, wrap):
        if not text:
            return 1

        nlines = 0
        for line in text.split('\n'):
            nlines += ceil(len(line) / cols)

        return nlines  # min(max(1, nlines), 10)


def make_message(message: str, direction: str) -> html.Div:
    message_id = secrets.token_hex(8)
    return html.Div([
        html.Div(message, className="inner-message")
    ], className=f"message from-{direction}", id=f'message-{message_id}')
