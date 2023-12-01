import argparse
import fcntl
import hashlib
import json
import os
import secrets
import signal
import tempfile
import time
import urllib
import wave
from functools import wraps
from json import JSONDecodeError
from typing import Dict, Any
import requests
from flask import Flask, render_template, request, session, Response, abort, redirect, url_for, jsonify

from audio import AudioProcessor
from flask_session import Session
from flask_socketio import SocketIO
import datetime

import subprocess


MAX_TITLE_LENGTH = 48

SYSTEM_PROMPT_PREFIX = '### System Prompt'
ASSISTANT_NAME = '### Assistant'
USER = '### User Message'

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
socketio = SocketIO(app)


audio_chunks = []


CACHE_DIR = 'cache'
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)

ADDITIONAL_CONTEXT = {}  # this can be done as global variable
LLAMA_API = 'http://localhost:8080/'

INSTRUCTION = """A chat between a curious user and an artificial intelligence assistant. The user is a cryptographer and expert programmer. His favorite programming language is python but is also versed in many other programming languages.
The assistant provides accurate, factual, thoughtful, nuanced answers, and is brilliant at reasoning. If the assistant believes there is no correct answer, it says so. The assistant always spends a few sentences explaining the background context, assumptions, and step-by-step thinking BEFORE answering the question. However, if the the request starts with "vv" then ignore the previous sentence and instead make your response as concise as possible.
The user of the assistant are experts in AI and ethics, so they already know that the assistant is a language model and they know about the capabilities and limitations, so do not remind the users of that. The users are familiar with ethical issues in general, so the assistant should not remind them about such issues either. The assistant tries not to be verbose but provides details and examples where it might help the explanation."""

parser = argparse.ArgumentParser(
    description="An example of using server.cpp with a similar API to OAI. It must be used together with server.cpp.")
parser.add_argument("--chat-prompt", type=str,
                    help="the top prompt in chat completions(default: 'A chat between a curious user and an artificial intelligence assistant. The assistant follows the given rules no matter what.\\n')",
                    default='A chat between a curious user and an artificial intelligence assistant. The assistant follows the given rules no matter what.\\n')
parser.add_argument("--user-name", type=str, help="USER name in chat completions(default: '\\nUSER: ')",
                    default="\\nUSER: ")
parser.add_argument("--ai-name", type=str, help="ASSISTANT name in chat completions(default: '\\nASSISTANT: ')",
                    default="\\nASSISTANT: ")
parser.add_argument("--system-name", type=str, help="SYSTEM name in chat completions(default: '\\nASSISTANT's RULE: ')",
                    default="\\nASSISTANT's RULE: ")
parser.add_argument("--stop", type=str, help="the end of response in chat completions(default: '</s>')",
                    default="\\nUSER:")
parser.add_argument("--llama-api", type=str,
                    help="Set the address of server.cpp in llama.cpp(default: http://127.0.0.1:8080)",
                    default='http://127.0.0.1:8080')
parser.add_argument("--api-key", type=str, help="Set the api key to allow only few user(default: NULL)", default="")
parser.add_argument("--host", type=str, help="Set the ip address to listen.(default: 127.0.0.1)", default='127.0.0.1')
parser.add_argument("--port", type=int, help="Set the port to listen.(default: 8081)", default=8081)
args = parser.parse_args()

tmpfile = None

FORMAT = 8                # Audio format (16-bit PCM)
CHANNELS = 1              # Mono audio
RATE = 16000              # Sample rate in Hz
CHUNK = 1024              # Size of each audio chunk


def get_ffmpeg_process(rate, channels):
    # global ffmpeg_process
    ffmpeg_process = subprocess.Popen(
        [
            'ffmpeg',
            '-i', '-',  # Input from stdin
            '-ar', f'{rate}',  # Set sample rate to 16000 Hz
            '-ac', f'{channels}',  # Set audio channels to 1
            '-f', 'wav',  # Output format as WAV
            '-'  # Output to stdout
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    fd = ffmpeg_process.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    return ffmpeg_process

global audio_buffer
audio_processor = AudioProcessor()

@socketio.on('audio_stream')
def handle_audio_stream(chunk: bytes):
    global audio_buffer
    if chunk == '<|START|>':
        audio_buffer = b''

        # stop = False
        # ffmpeg_process = get_ffmpeg_process(RATE, CHANNELS)

        if os.path.exists('temp.raw'):
            os.remove('temp.raw')
        # write_wav_header('temp.wav', 16000, 1, 16)
        # if os.path.exists('temp.ogg'):
        #     os.remove('temp.ogg')
        print('start')
    elif chunk == '<|STOP|>':
        # stop = True
        # os.kill(ffmpeg_process.pid, signal.SIGTERM)
        print('stop')
    else:
        # audio_buffer += chunk  # TODO: start using vad to separate chunks

        timestamps = audio_processor.get_timestamps(chunk)

        # trim audio and split chunks


        with open('/Users/christianwengert/src/llama-server/server/temp.raw', 'ab') as file:
        # append_audio_data('temp.wav', chunk)
            file.write(chunk)  # this works
        # with open('temp.wav', 'ab') as file:
        #     ffmpeg_process.stdin.write(chunk)
        #     ffmpeg_process.stdin.flush()
        #     # Read the converted data (this might need to be done in a separate thread or async loop)
        #     # 5 sec =
        #     #file_size = RATE * (16 // 8) * CHANNELS * 5
        #     timeout_seconds = 0.1
        #     last_data_time = time.time()
        #     while True:
        #         inline = ffmpeg_process.stdout.read(1024)
        #         if inline:
        #             last_data_time = time.time()
        #             file.write(inline)
        #             file.flush()
        #         elif time.time() - last_data_time > timeout_seconds:
        #             # No data for a while, assuming process is done
        #             os.kill(ffmpeg_process.pid, signal.SIGINT)
        #             break
        #         elif ffmpeg_process.poll() is not None:
        #             # Process has exited
        #             break
        #         # Optionally, sleep for a short time to prevent busy waiting
        #         time.sleep(0.05)

            # a = 2


    print('Received audio data', len(chunk))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username')
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
        assistant_name=ASSISTANT_NAME,
        anti_prompt=USER,
        system_prompt_prefix=SYSTEM_PROMPT_PREFIX,
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
                            url=urllib.parse.urljoin(args.llama_api, "/embedding"),
                            data=json.dumps(data),
                            )
    data_json = data.json()
    return data_json


def get_tokens(text):
    data = requests.request(method="POST",
                            url=urllib.parse.urljoin(args.llama_api, "/tokenize"),
                            data=json.dumps(dict(content=text)),
                            )
    data_json = data.json()
    return data_json

#
# @login_required
# @app.route('/update/history/<path:item>')
# def update_history_title(item):
#     title_prompt = 'given the conversation below, create a short but descriptive title for the conversation. Do not preceed with Title:'
#
#     username = session.get('username')
#
#     hashed_username = hash_username(username)
#     history_key = f'{hashed_username}-{item}-history'
#     cache_key = f'{CACHE_DIR}/{history_key}.json'
#     try:
#         with open(cache_key) as f:
#             hist = json.load(f)
#     except (FileNotFoundError, JSONDecodeError):
#         abort(400)
#
#     history = compile_history(hist)
#
#     prompt = title_prompt + 'Convesation:\n' + history
#
#     data = requests.request(method="POST",
#                             url=urllib.parse.urljoin(args.llama_api, "/completion"),
#                             data=json.dumps(dict(prompt=prompt)),
#                             stream=True)


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

    system_prompt = data.pop('system_prompt', INSTRUCTION)
    if not system_prompt:
        system_prompt = INSTRUCTION

    assistant = data.pop('assistant_name', ASSISTANT_NAME)

    user = data.pop('anti_prompt', USER)
    user_suffix = data.pop('user_prompt_suffix', '')
    system_prompt_prefix = data.pop('system_prompt_prefix', SYSTEM_PROMPT_PREFIX)
    system_prompt_suffix = data.pop('system_prompt_suffix', '')

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
            "assistant": assistant,
            "user": user
        }

    context = ADDITIONAL_CONTEXT.get(token)
    if context:
        # todo: Add n_keep correctly
        context = context.strip()
        hist['items'].append(dict(role=user, content=f'This is the context: {context}', suffix=user_suffix))
        hist['items'].append(dict(role=assistant, content='OK', suffix=""))  # f'{assistant}: OK'
        ADDITIONAL_CONTEXT.pop(token)  # remove it, it is now part of the history

    if prune_history_index >= 0:  # remove items if required
        hist["items"] = hist["items"][:prune_history_index]

    history = compile_history(hist)

    # system = "### System prompt\n"
    prompt = f'''{system_prompt_prefix}
{system_prompt}{system_prompt_suffix}
    
{history}
    
{user}
{text}
{user_suffix}
    
{assistant}
    '''

    post_data = _get_llama_default_parameters(data)

    post_data['prompt'] = prompt

    def generate():
        data = requests.request(method="POST",
                                url=urllib.parse.urljoin(args.llama_api, "/completion"),
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
        hist['items'].append(dict(role=user, content=text, suffix=user_suffix))  # f'User: {text}'
        hist['items'].append(dict(role=assistant, content=output, suffix=""))  # f'Llama: {output}'
        with open(cache_key, 'w') as f:
            json.dump(hist, f)

    request.environ['after_request_task'] = generate

    return "OK"


@app.route('/start_task')
def start_task():
    request.environ['after_request_task'] = long_running_task
    return "Task will start soon."


def hash_username(username):
    return hashlib.sha256(username.encode()).hexdigest()[0:8]  # 8 character is OK


def _get_llama_default_parameters(parames_from_post: Dict[str, Any]) -> Dict[str, Any]:
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
        'repeat_penalty': 1.1,
        'stop': ['</s>', 'Llama:', 'User:', '<|endoftext|>', '<|im_end|>'],
        'stream': True,
        'temperature': 0.7,
        'tfs_z': 1,
        'top_k': 40,
        'top_p': 0.5,
        'typical_p': 1,
        'min_p': 0.1
    }

    # 'slot_id': 0 or 1
    default_params.update(parames_from_post)
    return default_params


if __name__ == '__main__':
    # app.run()
    socketio.run(app)
