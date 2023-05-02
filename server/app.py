import queue
import secrets
from flask import Flask, render_template, request, session, abort, Response
from models import setup_chat_model
from streaming import StreamingLlamaHandler


streaming_answer_generator, create_conversation = setup_chat_model("oast")


app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
)

CONVERSATIONS = {}


@app.route("/")
def index():
    token = session.get('llm', None)
    if token is None:
        token = secrets.token_hex(32)
        session['llm'] = token
        q = queue.Queue()  # type: queue.Queue[str]
        # q = collections.deque()
        CONVERSATIONS[token] = (create_conversation(q), q)
    if token not in CONVERSATIONS:
        abort(400)

    return render_template('index.html')


@app.route('/', methods=["POST"])
def get_input():
    token = session.get('llm', None)
    conversation, q = CONVERSATIONS.get(token, None)
    if not conversation:
        abort(400)
    binary = request.data
    text = binary.decode('utf8')
    # q = queue.Queue()

    # def run_as_thread(t, qq):
    #     """
    #     We run this as a thread to be able to get token by token so its cooler to wait
    #     """
    def fun(t):
        q.put(t)

    def run_as_thread(t):
        """
        We run this as a thread to be able to get token by token so its cooler to wait
        """
        handler = StreamingLlamaHandler(fun)
        _answer = conversation.predict(input=t, callbacks=[handler])

    return Response(streaming_answer_generator(run_as_thread, q, text), mimetype='text/plain;charset=UTF-8 ')


if __name__ == '__main__':
    app.run()
