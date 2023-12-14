import hashlib
import json
import os
import secrets
import tempfile
import urllib
from functools import wraps
from json import JSONDecodeError
from typing import Dict, Any
import requests
from flask import Flask, render_template, request, session, Response, abort, redirect, url_for, jsonify, \
    stream_with_context, send_from_directory
from flask_session import Session
import datetime


MAX_TITLE_LENGTH = 48

SYSTEM = 'system'
ASSISTANT = 'assistant'
USER = 'user'

SEPARATOR = '~~~~'


def categorize_timestamp(timestamp: float):
    now = datetime.datetime.now()

    # for timestamp in timestamps:
    item_date = datetime.datetime.fromtimestamp(timestamp)

    if (now - item_date).days == 0:
        return "Today"
    elif (now - item_date).days == 1:
        return "Yesterday"
    elif (now - item_date).days <= 7:
        return "Last week"
    elif (now - item_date).days <= 30:
        return "Last month"
    else:
        return "Older"


app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=False,
    SESSION_COOKIE_SAMESITE='Strict',
)
app.config['SESSION_TYPE'] = 'filesystem'  # Filesystem-based sessions
app.config['SESSION_PERMANENT'] = True  # Persist sessions across restarts
app.config["PERMANENT_SESSION_LIFETIME"] = 30 * 24 * 60 * 60  # 30 days
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
Session(app)

CACHE_DIR = 'cache'
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)

ADDITIONAL_CONTEXT = {}  # this can be done as global variable
LLAMA_API = 'http://localhost:8080/'

INSTRUCTION = """A chat between a curious user and an artificial intelligence assistant. The user is a cryptographer and expert programmer. His favorite programming language is python but is also versed in many other programming languages.
The assistant provides accurate, factual, thoughtful, nuanced answers, and is brilliant at reasoning. If the assistant believes there is no correct answer, it says so. The assistant always spends a few sentences explaining the background context, assumptions, and step-by-step thinking BEFORE answering the question. However, if the the request starts with "vv" then ignore the previous sentence and instead make your response as concise as possible.
The user of the assistant are experts in AI and ethics, so they already know that the assistant is a language model and they know about the capabilities and limitations, so do not remind the users of that. The users are familiar with ethical issues in general, so the assistant should not remind them about such issues either. The assistant tries not to be verbose but provides details and examples where it might help the explanation."""


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['username'] = username
            return redirect(url_for('index'))

    return render_template('login.html',
                           name=os.environ.get("CHAT_NAME", "local")
                           )


@login_required
@app.route("/delete/history/<path:token>")
def remove(token):
    """
    Deletes a conversation from the history
    """
    username = session.get('username')
    hashed_username = hash_username(username)
    history_key = f'{hashed_username}-{token}-history'
    cache_key = f'{CACHE_DIR}/{history_key}.json'
    try:
        os.remove(cache_key)
    except FileNotFoundError:
        abort(400)
    return jsonify({})


@login_required
@app.route('/history')
@app.route('/history/<path:item>')
def history(item=None):
    """
    Returns a list of conversations from the history
    """
    username = hash_username(session.get('username'))

    history_items = []

    entries = os.listdir(CACHE_DIR)
    sorted_entries = sorted(entries, key=lambda x: os.path.getmtime(os.path.join(CACHE_DIR, x)), reverse=True)

    for d in sorted_entries:
        if d.startswith(username):
            with open(f'{CACHE_DIR}/{d}', 'r') as f:
                json_data = json.load(f)
            url = d.split('-')[1]
            history_items.append(dict(
                title=json_data["title"],
                url=url,
                items=json_data["items"] if item == url else [],
                age=categorize_timestamp(os.path.getmtime(os.path.join(CACHE_DIR, d)))
            ))
    return jsonify(history_items)


@login_required
@app.route("/settings/default")
def get_default_settings():
    data = get_llama_parameters()
    session['params'] = data
    return jsonify(data)


@login_required
@app.route("/c/<path:token>")
def c(token):

    # if token == 'vad.worklet.bundle.min.js':
    #     return send_from_directory('static', 'vad.worklet.bundle.min.js')

    if token == 'ort-wasm-simd.wasm':
        return send_from_directory('static', 'silero_vad.onnx')

    session['token'] = token

    data = session.get('params', None)
    if not data:
        data = get_llama_parameters()
    if type(data['stop']) == list:
        data['stop'] = ','.join(data['stop'])

    return render_template('index.html',
                           username=session.get('username', 'anonymous'),
                           name=os.environ.get("CHAT_NAME", "local"),
                           git=os.environ.get("CHAT_GIT", "https://github.com/christianwengert/llama-server"),
                           **data
                           )


def get_llama_parameters():
    data = dict(
        system_prompt=INSTRUCTION,
        grammar='',
        assistant_name=ASSISTANT,
        anti_prompt=USER,
        system_prompt_prefix=SYSTEM,
    )
    data = _get_llama_default_parameters(data)
    if type(data['stop']) == list:
        data['stop'] = ','.join(data['stop'])
    return data


@app.route("/")
@login_required
def index():
    # Just create a new session
    new_url = secrets.token_hex(16)
    return redirect(url_for('c', token=new_url))


@login_required
@app.route('/upload', methods=["POST"])
def upload():
    if not request.files:
        abort(400)

    files = request.files.getlist('file')
    if len(files) != 1:
        abort(400)

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

        tokens = get_tokens(contents)
        _n_tokens = len(tokens.get('tokens', []))  # todo: show this info to the user.

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


@login_required
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
                            url=urllib.parse.urljoin(LLAMA_API, "/embedding"),
                            data=json.dumps(data),
                            )
    data_json = data.json()
    return data_json


def get_tokens(text):
    data = requests.request(method="POST",
                            url=urllib.parse.urljoin(LLAMA_API, "/tokenize"),
                            data=json.dumps(dict(content=text)),
                            )
    data_json = data.json()
    return data_json


def compile_history(hist):
    lines = []
    for h in hist["items"]:
        suffix = h.get("suffix", "")
        if suffix:
            lines.append(f'{h["role"]}:\n{h["content"]}\n{suffix}\n')
        else:
            lines.append(f'{h["role"]}:\n{h["content"]}\n')
    return '\n'.join(lines)


@login_required
@app.route('/', methods=["POST"])
def get_input():
    token = session.get('token', None)
    username = session.get('username')

    data = request.get_json()
    text = data.pop('input')
    prune_history_index = data.pop('pruneHistoryIndex')

    session['params'] = dict(**data)  # must copy

    system_prompt = data.pop('system_prompt')

    prompt_template = data.pop('prompt_template', 'mixtral')

    hashed_username = hash_username(username)
    history_key = f'{hashed_username}-{token}-history'
    cache_key = f'{CACHE_DIR}/{history_key}.json'
    # load cache file
    try:
        with open(cache_key, 'r') as f:
            hist = json.load(f)
    except (FileNotFoundError, JSONDecodeError):
        hist = {
            "items": [],
            "title": text,
            "grammar": data.get('grammar'),
            "assistant": ASSISTANT,
            "user": USER
        }

    context = ADDITIONAL_CONTEXT.get(token)
    if context:
        # todo: Add n_keep correctly
        context = context.strip()
        hist['items'].append(dict(role=USER, content=f'This is the context: {context}'))
        hist['items'].append(dict(role=ASSISTANT, content='OK'))  # f'{assistant}: OK'
        ADDITIONAL_CONTEXT.pop(token)  # remove it, it is now part of the history

    if prune_history_index >= 0:  # remove items if required
        hist["items"] = hist["items"][:prune_history_index]

    # prompt_template = data.pop('prompt_template')

    prompt = make_prompt(hist, system_prompt, text, prompt_template)

    post_data = _get_llama_default_parameters(data)

    post_data['prompt'] = prompt
    # post_data['model'] = 'mixtral'
    # post_data['messages'] = prompt

    def generate():
        data = requests.request(method="POST",
                                url=urllib.parse.urljoin(LLAMA_API, "/completion"),
                                data=json.dumps(post_data),
                                stream=True)

        responses = []
        for i, line in enumerate(data.iter_lines()):
            if line:
                decoded_line = line.decode('utf-8')
                response = decoded_line[6:]
                responses.append(response)
                yield response + SEPARATOR

        output = "".join([json.loads(a)['content'] for a in responses if 'embedding' not in a]).strip()
        hist['items'].append(dict(role=USER, content=text))
        hist['items'].append(dict(role=ASSISTANT, content=output))
        with open(cache_key, 'w') as f:
            json.dump(hist, f)

    return Response(stream_with_context(generate()),
                    mimetype='text/event-stream',
                    direct_passthrough=False)


def make_prompt(hist, system_prompt, text, prompt_template):

    if prompt_template == 'mixtral':
        # <s>[INST] ${prompt} [/INST] Model answer</s> [INST] Follow-up instruction [/INST]
        prompt = ''
        prompt += f' [INST] {system_prompt} [/INST] '
        for line in hist['items']:
            if line['role'] == USER:
                prompt += f' [INST] {line["content"]} [/INST] '
            if line['role'] == ASSISTANT:
                prompt += f'{line["content"]}</s>'
        prompt += f' [INST] {text} [/INST]'
        return prompt

    if prompt_template == 'chatml':
        # <|im_start|>system
        # {system_message}<|im_end|>
        # <|im_start|>user
        # {prompt}<|im_end|>
        # <|im_start|>assistant
        prompt = ''
        prompt += f'<|im_start|>system\n'
        prompt += f'{system_prompt}<|im_end|>\n'
        for line in hist['items']:
            if line['role'] == USER:
                prompt += f'<|im_start|>user\n{line["content"]}<|im_end|>\n'
            if line['role'] == ASSISTANT:
                prompt += f'<|im_start|>assistant\n{line["content"]}<|im_end|>'
        prompt += f'<|im_start|>user\n{text}<|im_end|>'
        prompt += f'<|im_start|>assistant'
        return prompt

    if prompt_template == 'alpaca':
        # "### Instruction", "### Response"
        prompt = ''

        prompt += f'{system_prompt}\n'
        for line in hist['items']:
            if line['role'] == USER:
                prompt += f'### User:\n{line["content"]}\n'
            if line['role'] == ASSISTANT:
                prompt += f'### Assistant:\n{line["content"]}'
        prompt += f'### User:\n{text}<|im_end|>'
        prompt += f'### Assistant:\n'
        return prompt


def hash_username(username):
    return hashlib.sha256(username.encode()).hexdigest()[0:8]  # 8 character is OK


def _get_llama_default_parameters(parames_from_post: Dict[str, Any]) -> Dict[str, Any]:
    default_params = {
        'cache_prompt': True,
        'frequency_penalty': 0,  # Repeat alpha frequency penalty (default: 0.0, 0.0 = disabled)
        'prompt_template': 'mixtral',
        'grammar': '',
        'min_p': 0.1,  # The minimum probability for a token to be considered, relative to the probability of the most likely token (default: 0.1, 0.0 = disabled)
        'image_data': [],
        'mirostat': 0,  # Enable Mirostat sampling, controlling perplexity during text generation (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0).
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'n_predict': 2048,
        'n_probs': 0,  #
        'presence_penalty': 0,  # Repeat alpha presence penalty (default: 0.0, 0.0 = disabled)
        'repeat_last_n': 256,  # Last n tokens to consider for penalizing repetition (default: 256, 0 = disabled, -1 = ctx-size)
        'repeat_penalty': 1.1,  # Control the repetition of token sequences in the generated text (default: 1.1, 1.0 = disabled)
        'stop': ['</s>', 'Llama:', 'User:', '<|endoftext|>', '<|im_end|>'],
        'stream': True,
        'temperature': 0.7,
        'tfs_z': 1,  # Enable tail free sampling with parameter z (default: 1.0, 1.0 = disabled).
        'top_k': 40,  # Limit the next token selection to the K most probable tokens (default: 40, 0 = disabled).
        'top_p': 0.5,  # Limit the next token selection to a subset of tokens with a cumulative probability above a threshold P (default: 0.9, 1.0 = disabled).
        'typical_p': 1,  # Enable locally typical sampling with parameter p (default: 1.0, 1.0 = disabled).
    }

    # 'slot_id': 0 or 1
    default_params.update(parames_from_post)
    return default_params


if __name__ == '__main__':
    app.run()
