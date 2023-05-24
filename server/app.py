import hashlib
import os
import queue
import secrets
import tempfile

from flask import Flask, render_template, request, session, abort, Response, redirect
from flask_executor import Executor
from langchain.chains.conversational_retrieval.base import BaseConversationalRetrievalChain

from embeddings.documents.pdf import embed_pdf
from models import MODELS, SELECTED_MODEL, MODEL_PATH
from streaming import StreamingLlamaHandler
from models.llama import streaming_answer_generator
from models.llama import create_conversation


app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=False,
    SESSION_COOKIE_SAMESITE='Strict',
)

executor = Executor(app)
executor.init_app(app)
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3 * 30 * 24 * 60 * 60  # 90 days
# app.config["SESSION_TYPE"] = "filesystem"
app.config['EXECUTOR_MAX_WORKERS'] = 8
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

CONVERSATIONS = {}  # per user conversation
ABORT = {}  # per user abort flag, not very nice, but works
EMBEDDINGS = {}


def long_running_pdf_indexer(name: str, file_or_path: str, model: str) -> BaseConversationalRetrievalChain:
    return embed_pdf(name, file_or_path, model)


@app.route('/check/<string:name>')
def check(name: str):
    h = hashlib.sha3_512(name.encode('utf8')).hexdigest()
    if not executor.futures.done(h):
        # noinspection PyProtectedMember
        return str(executor.futures._state(h))
    future = executor.futures.pop(h)
    qa = future.result()
    EMBEDDINGS[name] = qa, []
    return "OK"


@app.route('/embeddings/<string:name>')
def embeddings(name: str):
    if not EMBEDDINGS:
        return redirect('/')
    return render_template('index.html', selected_embedding=name, embeddings=EMBEDDINGS, models=MODELS, selected_model=SELECTED_MODEL, name=os.environ.get("CHAT_NAME", "local"))


@app.route('/upload', methods=['POST'])
def upload():
    if not request.files:
        abort(400)
    if len(request.files) != 1:
        abort(400)
    file = request.files.get('file', None)
    if not file:
        abort(400)

    name = request.form.get('name')
    if not name:
        abort(400)

    dest = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(dest)

    h = hashlib.sha3_512(name.encode('utf8')).hexdigest()

    model = session.get('model')
    if not model:
        abort(400)

    if os.path.splitext(dest)[1] != '.pdf':
        abort(400)

    # if not EMBEDDINGS:
    #     session['embeddings'] = {}

    executor.submit_stored(h, long_running_pdf_indexer, name, dest, model)

    # embeddings = session.get('embeddings', [])

    EMBEDDINGS[name] = None

    return "OK"  # todo: redirect to wait page.....


@app.route("/")
def index():
    token = session.get('llm', None)
    set_model = session.get('model', None)
    # check if model is set
    model = request.args.get('model', SELECTED_MODEL)
    model_path = os.path.join(MODEL_PATH, f'{model}.bin')
    if token is None or model != set_model:
        token = secrets.token_hex(32)
        session['llm'] = token
        session['model'] = model
        q = queue.Queue()  # type: queue.Queue[str]

        prompt, stop, n_ctx = MODELS[model]
        CONVERSATIONS[token] = (create_conversation(model_path, prompt, stop, n_ctx), q)
    if token not in CONVERSATIONS:
        abort(400)

    return render_template('index.html', models=MODELS, selected_model=SELECTED_MODEL, name=os.environ.get("CHAT_NAME", "local"))


@app.route('/reset')
def reset():
    if session.get('llm', None) is not None:
        session['llm'] = None
    return ""


@app.route('/cancel')
def cancel():
    token = session.get('llm', None)
    if token:
        ABORT[token] = True
    else:
        abort(400)
    return ""


@app.route('/', methods=["POST"])
def get_input():
    token = session.get('llm', None)
    conversation, q = CONVERSATIONS.get(token, None)
    if not conversation:
        abort(400)
    data = request.json
    text = data.get('input')
    input_dict = {"input": text}
    chat_history = None
    if data['model'] in EMBEDDINGS:
        conversation, chat_history = EMBEDDINGS[data['model']]
        input_dict = {"question": text, "chat_history": chat_history}

    def fun(t):
        q.put(t)

    def abortfn():
        result = ABORT.get(token, False)
        ABORT[token] = False
        return result

    def run_as_thread(t):
        """
        We run this as a thread to be able to get token by token so its cooler to wait
        """
        handler = StreamingLlamaHandler(fun, abortfn)
        # _answer = conversation.predict(input=t, callbacks=[handler])
        _answer = conversation(input_dict, callbacks=[handler])
        if chat_history is not None:
            chat_history.append((text, _answer['answer']))

    return Response(streaming_answer_generator(run_as_thread, q, text), mimetype='text/plain;charset=UTF-8 ')


if __name__ == '__main__':
    app.run()
