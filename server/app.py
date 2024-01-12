import argparse
import hashlib
import json
import os
import secrets
import tempfile
import urllib
from functools import wraps
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
import requests
import scipdf
from flask import Flask, render_template, request, session, Response, abort, redirect, url_for, jsonify, \
    stream_with_context
from langchain_community.vectorstores.faiss import FAISS

from flask_session import Session
from urllib.parse import urlparse

from rag import rag_context, RAG_RERANKING_TEMPLATE_STRING, RAG_RERANKING_YESNO_GRAMMAR, RAG_NUM_DOCS, \
    get_available_collections, load_collection, get_collection_from_query
from utils.filesystem import is_archive, extract_archive, is_pdf, is_text_file, is_sqlite, is_source_code_file, \
    get_mime_type, is_json
from utils.timestamp_formatter import categorize_timestamp

MAX_NUM_TOKENS_FOR_INLINE_CONTEXT = 20000

SYSTEM = 'system'
ASSISTANT = 'assistant'
USER = 'user'

SEPARATOR = '~~~~'

# This is how to get rid off langchain
# from sentence_transformers import SentenceTransformer
# EMBEDDINGS = SentenceTransformer('BAAI/bge-large-en-v1.5')
#
# #Our sentences we like to encode
# sentences = ['This framework generates embeddings for each input sentence',
#     'Sentences are passed as a list of string.',
#     'The quick brown fox jumps over the lazy dog.']
#
# #Sentences are encoded by calling model.encode()
# embeddings = model.encode(sentences, normalize_embeddings=True)
# EMBEDDINGS.embed_documents(sentences)
#
# #Print the embeddings
# for sentence, embedding in zip(sentences, embeddings):
#     print("Sentence:", sentence)
#     print("Embedding:", embedding)
#     print("")


LOADED_EMBEDDINGS = {}

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
The user of the assistant is an expert in AI and ethics, so he already knows that the assistant is a language model and he knows about the capabilities and limitations, so do not remind the users of that. The user is familiar with ethical issues in general, so the assistant should not remind him about such issues either. The assistant tries not to be verbose but provides details and examples where it might help the explanation."""
# todo remove all of this
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
    return jsonify(get_llama_parameters())


@login_required
@app.route("/c/<path:token>")
def c(token):
    session['token'] = token

    data = session.get('params', None)
    if not data:
        data = get_llama_parameters()
    if isinstance(data['stop'], list):
        data['stop'] = ','.join(data['stop'])

    collections = get_available_collections()
    common_collections = [b for a, b in collections if a == 'common']

    return render_template('index.html',
                           common_collections=common_collections,
                           username=session.get('username', 'anonymous'),
                           name=os.environ.get("CHAT_NAME", "local"),
                           num_words=round(MAX_NUM_TOKENS_FOR_INLINE_CONTEXT * 0.7 / 1000) * 1000,  # show how many tokens we can add to the context
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
    if isinstance(data['stop'], list):
        data['stop'] = ','.join(data['stop'])
    return data


def parse_pdf(filename: Union[str, Path]) -> Dict:
    if not os.path.exists(filename):
        raise FileNotFoundError()
    import time
    start = time.time()
    document = scipdf.parse_pdf_to_dict(filename)  # return dictionary
    end = time.time()
    print(f'Processed document in {end - start} seconds')
    return document


def make_pdf_prompt(article: Dict):
    prompt_text = "The following is an article on which I will ask questions. After processing this article, acknowledge the following with OK."
    prompt_text += f"# {article['title']}\n\n"
    prompt_text += f"## authors: {article['authors']}\n\n"
    prompt_text += f"## abstract: {article['abstract']}\n\n"

    for section in article['sections']:
        prompt_text += f"## {section['heading']}\n"
        prompt_text += section['text']
    return prompt_text


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
        abort(400)  # todo, maybe one day we will upload more files

    # destination = None
    base_folder = os.path.join(app.config['UPLOAD_FOLDER'], secrets.token_hex(8))
    for file in files:
        destination = os.path.join(base_folder, file.filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        file.save(destination)
        # contents = ""  # Set it to empty to avoid breaking if some garbage is uploaded
        if is_archive(destination):
            extract_archive(file.filename, destination)  # this will always be put into a collection?
            return jsonify({"error": "Archives are not supported yet. If you need this, open a Github Issue."})

        elif is_pdf(destination):
            document = parse_pdf(destination)
            contents = make_pdf_prompt(document)

        elif is_source_code_file(destination):
            with open(destination, 'r') as f:
                contents = f.read()

        elif is_json(destination):
            with open(destination, 'r') as f:
                contents = f.read()

        elif is_text_file(destination):
            with open(destination, 'r') as f:
                contents = f.read()

        elif is_sqlite(destination):
            return jsonify({"error": "sqlite Databases are not supported yet. If you need this, open a Github Issue."})

        else:
            mime_type = get_mime_type(destination)
            return jsonify({"error": f"Unknown file type {mime_type}. If you need this, open a Github Issue."})
        token = session.get('token')
        ADDITIONAL_CONTEXT[token] = dict(contents=contents, filename=file.filename)

        tokens = get_tokens(contents)

        n_tokens = len(tokens.get('tokens', []))  # todo: show this info to the user.
        if n_tokens > MAX_NUM_TOKENS_FOR_INLINE_CONTEXT:
            return jsonify({"error": f"Too many tokens: {n_tokens}. Maximum tokens allows: {MAX_NUM_TOKENS_FOR_INLINE_CONTEXT}"})

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
    #     executor.submit_stored(h, long_running_pdf_indexer, name, destination, model)
    #
    # if embedding_type == 'sql':
    #     executor.submit_stored(h, long_running_sql_indexer, name, destination, model)
    #
    # EMBEDDINGS[name] = None

    return jsonify({"status": "OK"})  # redirect done in JS


@login_required
@app.route('/embeddings', methods=["POST"])
def embeddings():
    # This returns the embeddings from the llama.cpp model, this is NOT the same as embeddings for RAG
    data = request.get_json()
    if 'content' not in data:
        abort(400)
    if len(data) > 1:
        abort(400)
    return get_llama_cpp_embeddings(data)


def get_llama_cpp_embeddings(data):
    # This returns the embeddings from the llama.cpp model, this is NOT the same as embeddings for RAG
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

    collection = get_collection_from_query(request)
    vector_store = None
    if collection:
        vector_store = LOADED_EMBEDDINGS.get(token)
        if vector_store is None:
            vector_store = load_collection(collection)
            LOADED_EMBEDDINGS[token] = vector_store

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

    # Add context if asked
    context, metadata = make_context(data, text, token, vector_store)
    if context:
        hist['items'].append(dict(role=USER, content=f'This is the context: {context}', metadata=metadata))
        hist['items'].append(dict(role=ASSISTANT, content='OK'))  # f'{assistant}: OK'
        ADDITIONAL_CONTEXT.pop(token, None)  # remove it, it is now part of the history

    if prune_history_index >= 0:  # remove items if required
        hist["items"] = hist["items"][:prune_history_index]

    prompt = make_prompt(hist, system_prompt, text, prompt_template)

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
        hist['items'].append(dict(role=USER, content=text))
        hist['items'].append(dict(role=ASSISTANT, content=output))
        with open(cache_key, 'w') as f:
            json.dump(hist, f)

    return Response(stream_with_context(generate()),
                    mimetype='text/event-stream',
                    direct_passthrough=False)


def make_context(data, query, token, vector_store) -> Tuple[Optional[str], Optional[Dict]]:
    # We add first the "generic" context from the collection and then the file.
    # The logic here is that if I added a file, it is probably more important
    context = ""
    context_from_rag, metadata = get_context_from_rag(data, query, vector_store)
    if context_from_rag:
        context_from_rag = context_from_rag.strip()
        # context += 'Here is some relevant text from the database:'
        context += context_from_rag

    context_from_file, metadata = get_context_from_upload(token)
    if context_from_file:
        # todo: Add n_keep correctly
        context_from_file = context_from_file.strip()
        # context += 'Here is some relevant text from the upload:'
        context += context_from_file

    return context, metadata


def get_context_from_upload(token: str) -> Tuple[Optional[str], Optional[Dict]]:
    context = ADDITIONAL_CONTEXT.get(token, {})
    if context is None:
        return None, None
    metadata = dict(filename=context.get('filename', None))
    contents = context.get('contents', None)
    return contents, metadata


def get_context_from_rag(data, query: str, vector_store: Optional[FAISS], num_docs=RAG_NUM_DOCS) -> Tuple[Optional[str], Optional[Dict]]:
    context = None
    metadata = None
    if vector_store:
        # retrieve documents
        reranked_docs = []
        docs = vector_store.similarity_search(query, k=num_docs)  #

        rerank_post_data = _get_llama_default_parameters(data)

        rerank_post_data['grammar'] = RAG_RERANKING_YESNO_GRAMMAR
        rerank_post_data['stream'] = False

        # re-rank documents
        for d in docs:
            formatted_prompt = RAG_RERANKING_TEMPLATE_STRING.format(question=query, context=d.page_content)

            rerank_post_data['prompt'] = formatted_prompt

            rr_data = requests.request(method="POST",
                                       url=urllib.parse.urljoin(args.llama_api, "/completion"),
                                       data=json.dumps(rerank_post_data),
                                       stream=False)

            rr_response = rr_data.json()
            print(rr_response.get('content'))
            # todo: Logic here
            if 'YES' == rr_response.get('content').strip():
                reranked_docs.append(d)
        # answer = test(llm, reranked_docs, question)
        # print(answer)
        if reranked_docs:
            context = rag_context(reranked_docs)
    return context, metadata


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


def _get_llama_default_parameters(params_from_post: Dict[str, Any]) -> Dict[str, Any]:
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
    params = dict(default_params)
    # 'slot_id': 0 or 1
    params.update(params_from_post)
    # ensure relevant parameters are not empty, this may lead to a crash otherwise on ./server
    for key in ['frequency_penalty',
                'min_p',
                'mirostat',
                'mirostat_tau',
                'mirostat_eta',
                'n_predict',
                'n_probs',
                'presence_penalty',
                'repeat_last_n',
                'repeat_penalty',
                'temperature',
                'tfs_z',
                'top_k',
                'top_p',
                'typical_p']:
        if params[key] == "" or type(params[key] == str):  # ensure int
            params[key] = default_params[key]
    return params


if __name__ == '__main__':
    app.run()
