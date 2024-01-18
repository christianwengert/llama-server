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
from typing import Dict, Optional, Union, Tuple, List
import requests
import scipdf
from flask import Flask, render_template, request, session, Response, abort, redirect, url_for, jsonify, \
    stream_with_context
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document
from llama_cpp import get_llama_default_parameters, get_llama_parameters, ASSISTANT, USER
from flask_session import Session
from urllib.parse import urlparse
from rag import rag_context, RAG_NUM_DOCS, \
    get_available_collections, load_collection, get_collection_from_query, create_or_open_collection, RAG_CHUNK_SIZE
from utils.filesystem import is_archive, extract_archive, is_pdf, is_text_file, is_sqlite, is_source_code_file, \
    get_mime_type, is_json, is_importable
from utils.timestamp_formatter import categorize_timestamp

MAX_NUM_TOKENS_FOR_INLINE_CONTEXT = 20000


SEPARATOR = '~~~~'
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
                    help="Set the address of server.cpp in llama_cpp(default: http://127.0.0.1:8080)",
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

    username = session.get('username')
    collections = get_available_collections(username)
    # common_collections = [b for a, b in collections if a == 'common']

    return render_template('index.html',
                           collections=collections,
                           username=session.get('username', 'anonymous'),
                           name=os.environ.get("CHAT_NAME", "local"),
                           num_words=round(MAX_NUM_TOKENS_FOR_INLINE_CONTEXT * 0.7 / 1000) * 1000,  # show how many tokens we can add to the context
                           git=os.environ.get("CHAT_GIT", "https://github.com/christianwengert/llama-server"),
                           **data
                           )


def parse_pdf_with_grobid(filename: Union[str, Path]) -> Dict:
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

    for _reference in article['references']:
        pass  # todo
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

    base_folder = os.path.join(app.config['UPLOAD_FOLDER'], secrets.token_hex(8))
    collection_selector = request.form.get('collection-selector', None)
    use_collection = collection_selector != ''
    return_args = {}

    for file in files:
        if not file.filename:
            return jsonify({"error": "You must provide a file."})
        destination = os.path.join(base_folder, file.filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        file.save(destination)
        # contents = ""  # Set it to empty to avoid breaking if some garbage is uploaded
        parsed_pdf_document = None
        # source_code_language = None

        if is_archive(destination):
            extract_archive(file.filename, destination)  # this will always be put into a collection?
            return jsonify({"error": "Archives are not supported yet. If you need this, open a Github Issue."})

        elif is_pdf(destination):
            parsed_pdf_document = parse_pdf_with_grobid(destination)
            contents = make_pdf_prompt(parsed_pdf_document)

        elif is_source_code_file(destination):
            with open(destination, 'r') as f:
                contents = f.read()
            # source_code_language = Language.PYTHON  # Todo

        elif is_json(destination):
            with open(destination, 'r') as f:
                contents = f.read()

        elif is_text_file(destination):
            with open(destination, 'r') as f:
                contents = f.read()

        elif is_sqlite(destination):
            return jsonify({"error": "sqlite Databases are not supported yet. If you need this, open a Github Issue. Or try the raw SQL text queries."})

        else:
            mime_type = get_mime_type(destination)
            return jsonify({"error": f"Unknown file type {mime_type}. If you need this, open a Github Issue."})

        tokens = get_tokens(contents)

        n_tokens = len(tokens.get('tokens', []))  # todo: show this info to the user.

        if use_collection:

            collection_name = request.form['collection-name']
            if not collection_name:
                return jsonify({"error": f"You just provide a name for the collection."})
            collection_visibility = request.form.get('collection-visibility', 'private')
            username = session.get('username')

            index, index_path = create_or_open_collection(collection_name, username, collection_visibility == "public")

            if parsed_pdf_document:  # already processed pdf, i.e. already split in abstract, sections etc.

                # Todo: Check if doc is already in the index
                # This is actually not that easy, so not done for the moment. Hey: You give me shit, I give you shit
                text_splitter = RecursiveCharacterTextSplitter(
                    separators=[r'(?<=[^A-Z].[.?]) +(?=[A-Z])'],
                    # Set a really small chunk size, just to show.
                    chunk_size=RAG_CHUNK_SIZE,
                    chunk_overlap=0,
                    length_function=len,
                    is_separator_regex=True,
                )
                # docs = [
                #     Document(page_content=f'{parsed_pdf_document["title"]}\n\n{parsed_pdf_document["authors"]}',
                #              metadatas = [dict(file=file.filename, position='header')]
                #     )
                # ]
                text = f"Title: {parsed_pdf_document['title']}\n\nAbstract:\n{parsed_pdf_document['abstract']}"
                docs = text_splitter.create_documents([text], metadatas=[dict(file=file.filename, position='abstract')])
                sections_with_titles = [section['heading'] + '\n\n' + section['text'] for section in parsed_pdf_document['sections']]
                docs.extend(text_splitter.create_documents(sections_with_titles, metadatas=[dict(file=file.filename, position='section')] * len(sections_with_titles)))
                # Ok now we have all docs and metadata
                index.add_documents(docs)
                index.save_local(index_path)
                return_args['collection-name'] = collection_name
                return_args['collection-visibility'] = collection_visibility

            else:

                # todo
                # from langchain.text_splitter import (
                #     Language,
                #     RecursiveCharacterTextSplitter,
                #
                # )
                # from langchain.text_splitter import MarkdownHeaderTextSplitter
                # You can also see the separators used for a given language
                # RecursiveCharacterTextSplitter.get_separators_for_language(Language.PYTHON)
                # python_splitter = RecursiveCharacterTextSplitter.from_language(
                #     language=Language.PYTHON, chunk_size=50, chunk_overlap=0
                # )
                # python_docs = python_splitter.create_documents([PYTHON_CODE])
                pass
        else:
            if n_tokens > MAX_NUM_TOKENS_FOR_INLINE_CONTEXT:
                return jsonify({"error": f"Too many tokens: {n_tokens}. Maximum tokens allows: {MAX_NUM_TOKENS_FOR_INLINE_CONTEXT}"})
            token = session.get('token')
            ADDITIONAL_CONTEXT[token] = dict(contents=contents, filename=file.filename)
    ret_val = {**{"status": "OK"}, **return_args}
    return jsonify(ret_val)  # redirect done in JS


# @login_required
# @app.route('/embeddings', methods=["POST"])
# def embeddings():
#     # This returns the embeddings from the llama_cpp model, this is NOT the same as embeddings for RAG
#     data = request.get_json()
#     if 'content' not in data:
#         abort(400)
#     if len(data) > 1:
#         abort(400)
#     return get_llama_cpp_embeddings(data)


# def get_llama_cpp_embeddings(data):
#     # This returns the embeddings from the llama_cpp model, this is NOT the same as embeddings for RAG
#     data = requests.request(method="POST",
#                             url=urllib.parse.urljoin(args.llama_api, "/embedding"),
#                             data=json.dumps(data),
#                             )
#     data_json = data.json()
#     return data_json


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
            vector_store = load_collection(collection, username)
            LOADED_EMBEDDINGS[token] = vector_store  # keep it for next time

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
    context, metadata = make_context(text, token, vector_store)
    if context:
        item = dict(role=USER, content=f'This is the context: {context}', metadata=metadata)
        if collection:
            item['collection'] = collection
        hist['items'].append(item)
        hist['items'].append(dict(role=ASSISTANT, content='OK'))  # f'{assistant}: OK'
        ADDITIONAL_CONTEXT.pop(token, None)  # remove it, it is now part of the history

    if prune_history_index >= 0:  # remove items if required
        hist["items"] = hist["items"][:prune_history_index]

    prompt = make_prompt(hist, system_prompt, text, prompt_template)

    post_data = get_llama_default_parameters(data)

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
        # todo: Add n_keep correctly
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


def transform_query(query: str, use_llm=False) -> str:
    if not use_llm:
        return query
    # This is called query transform, todo: The problem is: It will overwrite the llama.cpp cache
    query_gen_str = """Provide a better search query for a search engine to answer the given question. Question: {query}\nAnswer:"""
    post_data = get_llama_default_parameters({})
    post_data['stream'] = False
    post_data['prompt'] = query_gen_str.format(query=query)
    response = requests.request(method="POST",
                                url=urllib.parse.urljoin(args.llama_api, "/completion"),
                                data=json.dumps(post_data),
                                stream=False)
    return response.json()['content'].strip()


def get_context_from_rag(query: str, vector_store: Optional[FAISS], num_docs: int = RAG_NUM_DOCS) -> Tuple[Optional[str], List[Dict]]:
    context = None
    metadata = []
    if vector_store:
        query = transform_query(query)  # Do not use, because it clears the cache and we have to process everything again
        docs = search_and_rerank_docs(num_docs, query, vector_store)
        context, metadata = rag_context(docs)
    return context, metadata


def search_and_rerank_docs(num_docs: int, query: str, vector_store: FAISS):
    if is_importable('flashrank'):
        rawdocs = vector_store.similarity_search(query, k=num_docs * 2)  #
        # noinspection PyPackageRequirements
        from flashrank import RerankRequest, Ranker
        ranker = Ranker(model_name="ms-marco-MultiBERT-L-12")
        rerankrequest = RerankRequest(query=query,
                                      passages=[
                                          {"meta": d.metadata, "text": d.page_content} for d in rawdocs
                                      ])
        results = ranker.rerank(rerankrequest)
        docs = []
        for r in results[:num_docs]:
            docs.append(Document(page_content=r['text'], metadata=r['meta']))
    else:
        print('no flashrank available')
        docs = vector_store.similarity_search(query, k=num_docs)  #
    return docs
    # Other ideas:
    # HyDe
    # from langchain.chains import HypotheticalDocumentEmbedder
    #
    # Rerank with LLM
    #
    # if rerank:
    #     reranked_docs = []
    #     rerank_post_data = _get_llama_default_parameters(data)
    #
    #     rerank_post_data['grammar'] = RAG_RERANKING_YESNO_GRAMMAR
    #     rerank_post_data['stream'] = False
    #
    #     # re-rank documents
    #
    #     for d in docs:
    #         formatted_prompt = RAG_RERANKING_TEMPLATE_STRING.format(question=query, context=d.page_content)
    #
    #         rerank_post_data['prompt'] = formatted_prompt
    #
    #         rr_data = requests.request(method="POST",
    #                                    url=urllib.parse.urljoin(args.llama_api, "/completion"),
    #                                    data=json.dumps(rerank_post_data),
    #                                    stream=False)
    #
    #         rr_response = rr_data.json()
    #         print(rr_response.get('content'))
    #         # todo: Logic here
    #         if 'YES' == rr_response.get('content').strip():
    #             reranked_docs.append(d)
    #     # answer = test(llm, reranked_docs, question)
    #     # print(answer)
    #     if reranked_docs:
    #         context = rag_context(reranked_docs)
    # else:


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


if __name__ == '__main__':
    app.run()
