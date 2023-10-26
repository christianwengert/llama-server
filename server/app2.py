import argparse
import json
import os
import secrets
import tempfile
import urllib
from functools import wraps
from typing import Dict, Any
import requests
from flask import Flask, render_template, request, session, Response, abort, redirect, url_for

app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=False,
    SESSION_COOKIE_SAMESITE='Strict',
)
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 30 * 24 * 60 * 60  # 30 days
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()


HISTORY = {}
ADDITIONAL_CONTEXT = {}
LLAMA_API = 'http://localhost:8080/'


INSTRUCTION = """A chat between a curious user and an artificial intelligence assistant. The user is a cryptographer and expert programmer. His favorite programming language is python but is also versed in many other programming languages.
The assistant provides accurate, factual, thoughtful, nuanced answers, and is brilliant at reasoning. If the assistant believes there is no correct answer, it says so. The assistant always spends a few sentences explaining the background context, assumptions, and step-by-step thinking BEFORE answering the question. However, if the the request starts with "vv" the ignore the previous sentence and instead make your response as concise as possible.
The user of the assistant are experts in AI and ethics, so they already know that the assistant is a language model and they know about the capabilities and limitations, so do not remind the users of that. The users are familiar with ethical issues in general, so the assistant should not remind them about such issues either. The assistant tries not to be verbose but provides details and examples where it might help the explanation."""


parser = argparse.ArgumentParser(description="An example of using server.cpp with a similar API to OAI. It must be used together with server.cpp.")
parser.add_argument("--chat-prompt", type=str, help="the top prompt in chat completions(default: 'A chat between a curious user and an artificial intelligence assistant. The assistant follows the given rules no matter what.\\n')", default='A chat between a curious user and an artificial intelligence assistant. The assistant follows the given rules no matter what.\\n')
parser.add_argument("--user-name", type=str, help="USER name in chat completions(default: '\\nUSER: ')", default="\\nUSER: ")
parser.add_argument("--ai-name", type=str, help="ASSISTANT name in chat completions(default: '\\nASSISTANT: ')", default="\\nASSISTANT: ")
parser.add_argument("--system-name", type=str, help="SYSTEM name in chat completions(default: '\\nASSISTANT's RULE: ')", default="\\nASSISTANT's RULE: ")
parser.add_argument("--stop", type=str, help="the end of response in chat completions(default: '</s>')", default="\\nUSER:")
parser.add_argument("--llama-api", type=str, help="Set the address of server.cpp in llama.cpp(default: http://127.0.0.1:8080)", default='http://127.0.0.1:8080')
parser.add_argument("--api-key", type=str, help="Set the api key to allow only few user(default: NULL)", default="")
parser.add_argument("--host", type=str, help="Set the ip address to listen.(default: 127.0.0.1)", default='127.0.0.1')
parser.add_argument("--port", type=int, help="Set the port to listen.(default: 8081)", default=8081)

args = parser.parse_args()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['username'] = username
            return redirect(url_for('index'))
    return '''
    <form method="post">
        <label>Username:</label>
        <input type="text" name="username">
        <button type="submit">Login</button>
    </form>
    '''  # todo: make a site


@app.route("/")
@login_required
def index():
    token = session.get('token', None)
    if token is None:
        token = secrets.token_hex(32)
        session['token'] = token
    return render_template('index.html',
                           system_prompt=INSTRUCTION,
                           grammar='',
                           name=os.environ.get("CHAT_NAME", "local"),
                           git=os.environ.get("CHAT_GIT", "https://github.com/christianwengert/llama-server"),
                           )


@app.route('/reset')
def reset():
    token = session.get('token', None)
    if token is not None:
        session['token'] = None
        HISTORY[token] = []
    return ""


@app.route('/upload', methods=["POST"])
def upload():
    if not request.files:
        abort(400)

    files = request.files.getlist('file')
    if len(files) != 1:
        abort(400)

    # file = files[0]

    # dest = None
    base_folder = os.path.join(app.config['UPLOAD_FOLDER'], secrets.token_hex(8))
    for file in files:
        dest = os.path.join(base_folder, file.filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file.save(dest)
        # const splitter = RecursiveCharacterTextSplitter.fromLanguage("js", {
        #   chunkSize: 32,
        #   chunkOverlap: 0,
        # });
        # texts = split_pdf(dest, 1024, 64)
        with open(dest, 'r') as f:
            contents = f.read()

        token = session.get('token')
        ADDITIONAL_CONTEXT[token] = contents

    # collection = request.form['collection-selector']  # todo

    # extract text fro document

    # name = request.files['collection-selector']
    # if not name:
    #     abort(400)

    # embedding_type = request.form.get('embedding')
    # if not embedding_type:
    #     abort(400)

    # h = hashlib.sha3_512(name.encode('utf8')).hexdigest()

    # model = session.get('model')
    # if not model:
    #     abort(400)

    # if embedding_type == 'code':
    #     executor.submit_stored(h, long_running_code_indexer, name, base_folder, model)
    #
    # if embedding_type == 'pdf':
    #     executor.submit_stored(h, long_running_pdf_indexer, name, dest, model)
    #
    # if embedding_type == 'sql':
    #     executor.submit_stored(h, long_running_sql_indexer, name, dest, model)
    #
    # EMBEDDINGS[name] = None

    return "OK"  # redirect done in JS


@app.route('/embeddings', methods=["POST"])
def embeddings():
    data = request.get_json()
    if 'content' not in data:
        abort(400)
    if len(data) > 1:
        abort(400)
    return get_embeddings(data)


def get_embeddings(data):
    data = requests.request(method="POST",
                            url=urllib.parse.urljoin(args.llama_api, "/embedding"),
                            data=json.dumps(data),
                            )
    data_json = data.json()
    return data_json


@app.route('/', methods=["POST"])
def get_input():
    token = session.get('token', None)
    if token not in HISTORY:
        HISTORY[token] = []

    data = request.get_json()  # todo remove 'model' from data and add other params
    text = data.pop('input')

    system_prompt = data.get('system_prompt', INSTRUCTION)
    if not system_prompt:
        system_prompt = INSTRUCTION
    _grammar = data.pop('grammar')  # todo: not ready yet

    assistant = 'Llama'
    user = 'User'

    context = ADDITIONAL_CONTEXT.get(token)
    if context:   # todo here this is not workong great!
        context = context.strip()
        HISTORY[token].append(f'{user}: This is the context: {context}')
        HISTORY[token].append(f'{assistant}: OK')
        ADDITIONAL_CONTEXT.pop(token)  # remove it, it is now part of the history

    history = '\n'.join(HISTORY[token])
    prompt = f'{system_prompt}\n\n{history}\nUser: {text}\n{assistant}:'

    post_data = get_llama_params(data)

    post_data['prompt'] = prompt
    post_data.pop('system_prompt')

    def generate():
        data = requests.request(method="POST",
                                url=urllib.parse.urljoin(args.llama_api, "/completion"),
                                data=json.dumps(post_data),
                                stream=True)

        responses = []
        for i, line in enumerate(data.iter_lines()):
            if line:
                decoded_line = line.decode('utf-8')
                response = json.loads(decoded_line[6:])

                if response.get("stop"):
                    # session['history'].append(responses)
                    pass
                else:
                    responses.append(json.dumps(response))

                yield json.dumps(response)

        output = "".join([json.loads(a)['content'] for a in responses if 'embedding' not in a]).strip()
        HISTORY[token].append(f'User: {text}')
        HISTORY[token].append(f'Llama: {output}')

    return Response(generate(), mimetype='text/event-stream')


def get_llama_params(parames_from_post: Dict[str, Any]) -> Dict[str, Any]:
    default_params = {
        'cache_prompt': True,
        'frequency_penalty': 0,
        'grammar': '',
        'image_data': [],
        'mirostat': 0,
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'n_predict': 2048,
        'n_probs': 0,
        'presence_penalty': 0,
        'repeat_last_n': 256,
        'repeat_penalty': 1.18,
        'stop': ['</s>', 'Llama:', 'User:'],
        'stream': True,
        'temperature': 0.7,
        'tfs_z': 1,
        'top_k': 40,
        'top_p': 0.5,
        'typical_p': 1,
    }

    # 'slot_id': 0 or 1
    default_params.update(parames_from_post)
    return default_params


if __name__ == '__main__':
    app.run()
