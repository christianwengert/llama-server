import hashlib
import os
import queue
import secrets
import tempfile
import time

from flask import Flask, render_template, request, session, abort, Response, redirect
from flask_executor import Executor
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.base import Chain

from embeddings.code.codebase import embed_code
from embeddings.documents.pdf import embed_pdf
from embeddings.sql.sql import embed_sql
from embeddings.translation.translate import translate_file
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


def long_running_pdf_indexer(name: str, file_or_path: str, model: str) -> Chain:
    return embed_pdf(name, file_or_path, model)


def long_running_sql_indexer(name: str, file_or_path: str, model: str) -> Chain:
    return embed_sql(name, file_or_path, model)


def long_running_code_indexer(name: str, file_or_path: str, model: str) -> Chain:
    return embed_code(name, file_or_path, model)


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


@app.route('/embeddings/')
@app.route('/embeddings/<string:name>')
def embeddings(name: str = None):
    if name is not None and name not in EMBEDDINGS:
        return redirect('/')
    return render_template('index.html',
                           selected_embedding=name,
                           embeddings=EMBEDDINGS,
                           show_embeddings=True,
                           models=MODELS,
                           selected_model=SELECTED_MODEL,
                           name=os.environ.get("CHAT_NAME", "local"))


@app.route('/upload', methods=['POST'])
def upload():
    if not request.files:
        abort(400)

    files = request.files.getlist('file')

    name = request.form.get('name')
    if not name:
        abort(400)

    embedding_type = request.form.get('embedding')
    if not embedding_type:
        abort(400)

    dest = None
    base_folder = os.path.join(app.config['UPLOAD_FOLDER'], secrets.token_hex(8), name)
    for file in files:
        dest = os.path.join(base_folder, file.filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file.save(dest)

    h = hashlib.sha3_512(name.encode('utf8')).hexdigest()

    model = session.get('model')
    if not model:
        abort(400)

    if embedding_type == 'code':
        executor.submit_stored(h, long_running_code_indexer, name, base_folder, model)

    if embedding_type == 'pdf':
        executor.submit_stored(h, long_running_pdf_indexer, name, dest, model)

    if embedding_type == 'sql':
        executor.submit_stored(h, long_running_sql_indexer, name, dest, model)

    EMBEDDINGS[name] = None

    return "OK"  # redirect done in JS


@app.route("/translate", methods=['POST'])
# @app.route('/translate/<string:name>')
def translate():

    if not request.files:
        abort(400)

    files = request.files.getlist('file')
    if len(files) > 1:
        return 'upload only one file'

    model = session.get('model', SELECTED_MODEL)
    base_folder = os.path.join(app.config['UPLOAD_FOLDER'], secrets.token_hex(8), files[0].filename)

    file = files[0]
    dest = os.path.join(base_folder, file.filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file.save(dest)
    return translate_file(dest, model)


    # return Response(streaming_answer_generator(run_as_thread, q, text), mimetype='text/plain;charset=UTF-8 ')


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

        prompt, stop, n_ctx, model_type = MODELS[model]
        CONVERSATIONS[token] = (create_conversation(model_path, prompt, stop, n_ctx, model_type), q)
    if token not in CONVERSATIONS:
        abort(400)

    return render_template('index.html', models=MODELS,
                           selected_model=SELECTED_MODEL,
                           embeddings=EMBEDDINGS,
                           name=os.environ.get("CHAT_NAME", "local"))


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
    # chat_history = None
    if data['model'] in EMBEDDINGS:  # special case for embeddings

        conversation, chat_history = EMBEDDINGS[data['model']]
        if isinstance(conversation, ConversationalRetrievalChain):  # PDF + Code
            input_dict = {"question": text, "chat_history": chat_history}  # if we put in the chat history
        if conversation.__class__.__name__ == 'MyChain':  # SQL
            input_dict = {"query": text}
            # chat_history = None

    def fun(t):
        q.put(t)

    def abortfn():
        result = ABORT.get(token, False)
        ABORT[token] = False
        return result

    def run_as_thread(_t):
        """
        We run this as a thread to be able to get token by token so its cooler to wait
        """
        try:
            handler = StreamingLlamaHandler(fun, abortfn)
            _answer = conversation(input_dict, callbacks=[handler])
            # if chat_history is not None:
            #     chat_history.append((text, _answer['answer']))
        except Exception as _e:
            pass
        finally:
            time.sleep(1.0)  # ugly hack
            fun("THIS IS THE END%^&*")

    return Response(streaming_answer_generator(run_as_thread, q, text), mimetype='text/plain;charset=UTF-8 ')


if __name__ == '__main__':
    app.run()
