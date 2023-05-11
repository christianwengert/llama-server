import os
import queue
import secrets
from flask import Flask, render_template, request, session, abort, Response
from streaming import StreamingLlamaHandler
from models.vicuna import PROMPT
from models.llama import streaming_answer_generator
from models.llama import create_conversation


MODEL_PATH = os.environ.get("MODEL_PATH", '/Users/christianwengert/Downloads/')


app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
)

CONVERSATIONS = {}


@app.route("/about")
def about():

    html = """
    <br><br>
    <div>
        <strong>Questions?</strong><br>
        Ask <a href="mailto:wengert@yoda.cry">wengert@yoda.cry</a>
    </div>
    <br><br>
    <div>
        <strong>News</strong>
        <ul>
            <li>10.5.2023   Simple chronosGPT online</li>
        </ul>
    </div>
    <br><br>
    <div>
        <strong>Coming up next</strong>
        <ul>
            <li>Make text generation cancellable</li>            
            <li>Document embedding (i.e. ask your PDF)</li>
            <li>Source code embedding (i.e. ask your code)</li>
            <li>More models</li>
        </ul>
    </div>
    <br><br>
    <div>
        <strong>Questions?</strong><br>
        Ask <a href="mailto:wengert@yoda.cry">wengert@yoda.cry</a>
    </div>
    """
    return render_template('index.html', extra_content=html)


@app.route("/")
def index():
    token = session.get('llm', None)
    set_model = session.get('model', None)
    # check if model is set
    model = request.args.get('model', 'wizard-vicuna-13B.ggml.q5_0')
    model_path = os.path.join(MODEL_PATH, f'{model}.bin')
    if token is None or model != set_model:
        token = secrets.token_hex(32)
        session['llm'] = token
        session['model'] = model
        q = queue.Queue()  # type: queue.Queue[str]

        CONVERSATIONS[token] = (create_conversation(model_path, PROMPT), q)
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
