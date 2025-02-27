import hashlib
import json
import os
import secrets
import tempfile
import time
import urllib
from functools import wraps
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import requests
from flask import Flask, render_template, request, session, Response, abort, redirect, url_for, jsonify, \
    stream_with_context, send_from_directory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_cpp import get_llama_default_parameters, get_llama_parameters, ASSISTANT, USER, \
    get_default_props_from_llamacpp
from flask_session import Session
from urllib.parse import urlparse
from rag import get_available_collections, load_collection, get_collection_from_query, create_or_open_collection, \
    RAG_CHUNK_SIZE, \
    get_text_splitter, extract_contents, get_context_from_rag, RAG_DATA_DIR
from utils.filesystem import is_archive, extract_archive, find_files
from utils.timestamp_formatter import categorize_timestamp


MAX_NUM_TOKENS_FOR_INLINE_CONTEXT: int = 2**15
while True:
    # noinspection PyBroadException
    try:
        props = get_default_props_from_llamacpp()
        default_generation_settings = props.get('default_generation_settings', {})
        num_slots = props.get('total_slots', 1)
        n_ctx = default_generation_settings.get('n_ctx', MAX_NUM_TOKENS_FOR_INLINE_CONTEXT)
        MAX_NUM_TOKENS_FOR_INLINE_CONTEXT = n_ctx // num_slots
        break
    except Exception:
        print("Waiting for llama-server")
        time.sleep(1)
        continue


# SEPARATOR = '~~~~'
LOADED_EMBEDDINGS = {}
CACHE_DIR = 'cache'
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)
ADDITIONAL_CONTEXT = {}  # this can be done as global variable
LLAMA_API = 'http://localhost:8080/'


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
                           name=os.environ.get("CHAT_NAME", "local"),
                           name2=os.environ.get("CHAT_NAME_2", "GPT")
                           )


@login_required
@app.route("/delete/collection/<path:collection>")
def remove_collection(collection):
    username = session.get('username')
    collections = get_available_collections(username)

    for key in ['common', 'user']:
        for item in collections[key]:
            if item.get('hashed_name') == collection:

                path = Path(RAG_DATA_DIR) / Path(f'user/{username}' if key == 'user' else 'common') / Path(collection)
                path = os.path.normpath(path)
                if path.startswith(RAG_DATA_DIR) and os.path.exists(path):
                    os.remove(path + '/config.json')
                    os.remove(path + '/index.faiss')
                    os.remove(path + '/index.pkl')
                    os.rmdir(path)
                return jsonify({})
    abort(404)
    #


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
    return jsonify(get_llama_parameters())


@login_required
@app.route("/c/<path:token>")
def c(token):

    if token == 'ort-wasm-simd.wasm':
        return send_from_directory('static', 'silero_vad.onnx')

    session['token'] = token

    data = session.get('params', None)
    if not data:
        data = get_llama_parameters()
    # if isinstance(data['stop'], list):
    #     data['stop'] = ','.join(data['stop'])

    username = session.get('username')
    collections = get_available_collections(username)

    return render_template('index.html',
                           collections=collections,
                           username=session.get('username', 'anonymous'),
                           name=os.environ.get("CHAT_NAME", "local"),
                           name2=os.environ.get("CHAT_NAME_2", "GPT"),
                           num_words=round(MAX_NUM_TOKENS_FOR_INLINE_CONTEXT * 0.7 / 1000) * 1000,  # show how many tokens we can add to the context
                           git=os.environ.get("CHAT_GIT", "https://github.com/christianwengert/llama-server"),
                           **data
                           )


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
        abort(400)  # maybe one day we will upload more files, now you can simply upload a zip

    base_folder = os.path.join(app.config['UPLOAD_FOLDER'], secrets.token_hex(8))
    collection_selector = request.form.get('collection-selector', None)
    use_collection = collection_selector != ''
    return_args = {}

    n_tokens = 0

    # first check if any of the files is an archive
    # if this is the case, append it to files
    error, files_to_process = prepare_files(base_folder, files)
    if error:
        return jsonify(error)

    contents = []
    # Now loop over the files and extract the contents
    for destination in files_to_process:
        # noinspection PyBroadException
        try:
            content, parsed_pdf_document, error = extract_contents(destination)
        except Exception:
            continue  # ignore this file
        if error:
            return jsonify(error)
        contents.append((destination, content, parsed_pdf_document))

    if use_collection:

        collection_name = request.form.get('collection-name')
        collection_selector = request.form.get('collection-selector')
        if not collection_name and not collection_selector:
            return jsonify({"error": f"You must provide a name for the collection."})
        if not collection_name:
            collection_name = collection_selector
        collection_visibility = request.form.get('collection-visibility', 'private')
        username = session.get('username')

        index, index_path, hashed_index_name = create_or_open_collection(collection_name, username, collection_visibility == "public")
        for destination, content, parsed_pdf_document in contents:
            filename = os.path.basename(destination)
            if parsed_pdf_document:  # already processed pdf, i.e. already split in abstract, sections etc.
                text_splitter = RecursiveCharacterTextSplitter(
                    separators=[r'(?<=[^A-Z].[.?]) +(?=[A-Z])'],
                    chunk_size=RAG_CHUNK_SIZE,
                    chunk_overlap=0,
                    length_function=len,
                    is_separator_regex=True,
                )
                text = f"Title: {parsed_pdf_document['title']}\n\nAbstract:\n{parsed_pdf_document['abstract']}"
                docs = text_splitter.create_documents([text], metadatas=[dict(file=filename, position='abstract')])
                sections_with_titles = [section['heading'] + '\n\n' + section['text'] for section in parsed_pdf_document['sections']]
                docs.extend(text_splitter.create_documents(sections_with_titles, metadatas=[dict(file=filename, position='section')] * len(sections_with_titles)))

            else:
                text_splitter = get_text_splitter(destination)
                docs = text_splitter.create_documents([content], metadatas=[dict(file=filename)])
            # Ok now we have all docs and metadata
            index.add_documents(docs)
            index.save_local(index_path)
            return_args['collection-name'] = collection_name
            return_args['collection-hashed-name'] = hashed_index_name
            return_args['collection-visibility'] = collection_visibility

    else:
        context = ""
        for _, content, _ in contents:
            tokens = get_tokens(content)
            n_tokens += len(tokens.get('tokens', []))
            context += f"{content}\n\n"
        if n_tokens > MAX_NUM_TOKENS_FOR_INLINE_CONTEXT:
            return jsonify(
                {"error": f"Too many tokens: {n_tokens}. Maximum tokens allows: {MAX_NUM_TOKENS_FOR_INLINE_CONTEXT}"})
        token = session.get('token')
        ADDITIONAL_CONTEXT[token] = dict(contents=context, filename=files[0].filename)

    ret_val = {**{"status": "OK"}, **return_args}
    return jsonify(ret_val)  # redirect done in JS


def prepare_files(base_folder: str, files: List) -> Tuple[Dict[str, str], List[str]]:
    files_to_process = []
    error = None
    for file in files:
        if not file.filename:
            error = {"error": "You must provide a file."}
        destination = os.path.join(base_folder, file.filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        file.save(destination)
        if is_archive(destination):
            # add all
            filename = destination
            destination, _ = os.path.splitext(destination)
            if extract_archive(filename, destination):
                files = find_files(destination, '')
                files_to_process.extend(files)
        else:
            # add this file
            files_to_process.append(destination)
    return error, files_to_process


def get_tokens(text):
    data = requests.request(method="POST",
                            url=urllib.parse.urljoin(LLAMA_API, "/tokenize"),
                            data=json.dumps(dict(content=text)),
                            )
    data_json = data.json()
    return data_json


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
#     prompt = title_prompt + 'Conversation:\n' + history
#
#     data = requests.request(method="POST",
#                             url=urllib.parse.urljoin(LLAMA_API, "/completion"),
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

    collection = get_collection_from_query(request)
    vector_store = None
    if collection:
        vector_store = LOADED_EMBEDDINGS.get(token)
        if vector_store is None:
            vector_store = load_collection(collection, username)
            LOADED_EMBEDDINGS[token] = vector_store  # keep it for next time

    data = request.get_json()
    text = data.pop('input')
    prune_history_index = data.pop('pruneHistoryIndex')

    session['params'] = dict(**data)  # must copy

    system_prompt = data.pop('system_prompt')

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

    # Add context if asked
    context, metadata = make_context(text, token, vector_store)
    if context:
        item = dict(role=USER, content=f'<context>\n{context}\n</context>', metadata=metadata)
        if collection:
            item['collection'] = collection
        hist['items'].append(item)
        hist['items'].append(dict(role=ASSISTANT, content='The context which is in between the <context></context> tags is now available.'))  # f'{assistant}: OK'
        ADDITIONAL_CONTEXT.pop(token, None)  # remove it, it is now part of the history

    if prune_history_index >= 0:  # remove items if required
        hist["items"] = hist["items"][:prune_history_index]

    messages = make_prompt(hist, system_prompt, text)
    post_data = get_llama_default_parameters(data)
    url = urllib.parse.urljoin(LLAMA_API, "/v1/chat/completions")
    post_data['messages'] = messages

    def generate():
        data = requests.request(method="POST",
                                url=url,
                                data=json.dumps(post_data),
                                stream=True)

        responses = []
        for i, line in enumerate(data.iter_lines()):
            if line:
                decoded_line = line.decode('utf-8')
                response = decoded_line[6:]
                if response != '[DONE]':
                    responses.append(response)
                    yield response  # + SEPARATOR

        output = "".join([json.loads(a)['choices'][0]['delta'].get('content', '') for a in responses if 'embedding' not in a]).strip()
        hist['items'].append(dict(role=USER, content=text))
        hist['items'].append(dict(role=ASSISTANT, content=output))
        with open(cache_key, 'w') as f:
            json.dump(hist, f)

    return Response(stream_with_context(generate()),
                    mimetype='text/event-stream',
                    direct_passthrough=False)


def make_context(query, token, vector_store) -> Tuple[Optional[str], List[Dict]]:
    # We add first the "generic" context from the collection and then the file.
    # The logic here is that if I added a file, it is probably more important
    context = ""
    context_from_rag, metadata_rag = get_context_from_rag(query, vector_store)
    if context_from_rag:
        context_from_rag = context_from_rag.strip()
        # context += 'Here is some relevant text from the database:'
        context += context_from_rag

    context_from_file, metadata_direct = get_context_from_upload(token)
    if context_from_file:
        # solved: Add n_keep correctly, see below
        # n_keep: Specify the number of tokens from the prompt to retain when the context size is exceeded and tokens need to be discarded. By default, this value is set to 0 (meaning no tokens are kept). Use -1 to retain all tokens from the prompt.
        context_from_file = context_from_file.strip()
        # context += 'Here is some relevant text from the upload:'
        context += context_from_file

    return context, metadata_rag + metadata_direct


def get_context_from_upload(token: str) -> Tuple[Optional[str], List[Dict]]:
    context = ADDITIONAL_CONTEXT.get(token, {})
    if not context:
        return "", []
    metadata = dict(file=context.get('filename', None))
    contents = context.get('contents', None)
    return contents, [metadata]


def make_prompt(hist, system_prompt, text):
    messages = [{'role': 'system', 'content': system_prompt}]
    messages += hist['items']
    messages += [{'role': USER, 'content': text}]
    return messages


def hash_username(username):
    return hashlib.sha256(username.encode()).hexdigest()[0:8]  # 8 character is OK


if __name__ == '__main__':
    app.run()
