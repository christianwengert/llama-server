import hashlib
import json
import os
import time
import urllib
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Union
from urllib.parse import urlparse, parse_qs

import requests
# noinspection PyPackageRequirements
import scipdf
from flask import Request
from langchain.text_splitter import TextSplitter, Language, RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document

from llama_cpp import get_llama_default_parameters, LLAMA_API

from utils.filesystem import list_directories, is_source_code_file, is_pdf, is_json, is_text_file, is_sqlite, \
    get_mime_type, is_importable


RAG_CHUNK_SIZE = 2048
RAG_DATA_DIR = os.path.dirname(__file__) + '/../../data'
RAG_RERANKING_TEMPLATE_STRING = "Given the following question and context, return YES if the context is relevant to the question and NO if it isn't. If you don't know, then respond with I DON'T KNOW\n\n> Question: {question}\n> Context:\n>>>\n{context}\n>>>\n> Relevant (YES / NO):"
RAG_RERANKING_YESNO_GRAMMAR = r'''
    root ::= answer
    answer ::= (complaint | yesno)        
    complaint ::= "I DON'T KNOW"
    yesno ::= ("YES" | "NO")
'''
RAG_NUM_DOCS = 5

RAG_MODEL = 'BAAI/bge-m3'
# RAG_MODEL = 'BAAI/bge-large-en-v1.5'
# RAG_MODEL = 'BAAI/bge-large-en-v1.5'
# RAG_MODEL = 'intfloat/multilingual-e5-large'
# Each input text should start with "query: " or "passage: ", even for non-English texts.
# For tasks other than retrieval, you can simply use the "query: " prefix.
# see also here: DO I need query: https://huggingface.co/intfloat/e5-large-v2

RAG_EMBEDDINGS = HuggingFaceEmbeddings(model_name=RAG_MODEL,
                                       encode_kwargs={'normalize_embeddings': True}  # set True to compute cosine similarity
                                       )


def rag_context(docs: List[Document]) -> Tuple[str, List[Dict]]:
    context = ""
    metadata = []
    for d in docs:
        context += "\n\nThis is one piece of context:\n" + d.page_content
        metadata.append(d.metadata)
    return context, metadata


def rag_contex_stackexchange(docs: List[Document]) -> str:
    context = []  # todo: add reference to metadata
    for d in docs:
        answers = d.metadata.get('answers')
        if answers:
            context.append(
                f"Q:\n\n{d.page_content}\n\n"
            )

            for a in answers:
                context.append(
                    f"A:\n\n{a}\n\n"
                )

    context_string = "".join(context)

    return context_string


def get_available_collections(username: str = None) -> Dict[str, List[str]]:
    common_dir = Path(RAG_DATA_DIR) / Path('common')

    collections = dict(common=[], user=[])

    for collection in list_directories(common_dir):
        # indices = find_files(common_dir / collection, '.faiss')
        collections['common'].append(collection)

    if username:
        user_dir = Path(RAG_DATA_DIR) / Path('user') / Path(username)
        if not os.path.exists(user_dir):
            os.mkdir(user_dir)
        for collection in list_directories(user_dir):
            collections['user'].append(collection)

    return collections


def create_or_open_collection(index_name: str, username: Optional[str], public: Optional[bool]) -> Tuple[FAISS, Path]:

    # Check if index exists already
    collections = get_available_collections(username)

    current_time = str(time.time_ns())  # Ensure uniqueness even with same filenames
    hashed_index_name = hashlib.sha256((index_name + current_time).encode()).hexdigest()[:32]

    if public:
        data_dir = Path(RAG_DATA_DIR) / Path('common')
        public_with_this_name_exists = index_name in collections['common']
        if public_with_this_name_exists:
            return FAISS.load_local(data_dir / index_name, RAG_EMBEDDINGS), data_dir / index_name
        # otherwise we will create a new DB
    else:
        data_dir = Path(RAG_DATA_DIR) / Path('user') / Path(username)
        private_with_this_name_exists = index_name in collections['user']
        if private_with_this_name_exists:
            return FAISS.load_local(data_dir / index_name, RAG_EMBEDDINGS), data_dir / index_name
        # otherwise we will create a new DB

    path = data_dir / index_name
    doc = Document(page_content="")  # We need to create a doc to initialize the docstore, then we gonna delete it again
    index = FAISS.from_documents([doc], RAG_EMBEDDINGS)
    # Todo: This is langchain stuff, too lazy to do it differently
    # noinspection PyProtectedMember,PyUnresolvedReferences
    index.delete([list(index.docstore._dict.keys())[0]])  # Empty again, this is
    index.save_local(path)

    with open(path / 'config.json', 'w') as f:
        json.dump(dict(model=RAG_MODEL, name=index_name, hashed_name=hashed_index_name), f)

    return index, path


def load_collection(collection: str, username: str) -> Optional[FAISS]:
    collections = get_available_collections(username)

    for key in ['user', 'common']:  # first check for same name user!
        for name in collections[key]:
            if name == collection:
                data_dir = RAG_DATA_DIR / Path(key)
                if key == 'user':
                    data_dir = data_dir / Path(username)
                return FAISS.load_local(data_dir / Path(collection), RAG_EMBEDDINGS)
    return None


def get_collection_from_query(request: Request) -> str:
    collection = None
    if request.referrer:
        parsed_url = urlparse(request.referrer)
        query_params = parse_qs(parsed_url.query)
        collections = query_params.get('collection')  # Returns a vector....
        if collections and len(collections) == 1:
            collection = collections[0]  # Just take one, there should not be more
    return collection


def get_text_splitter(destination: str) -> TextSplitter:
    _, extension = os.path.splitext(destination)
    if is_source_code_file(destination):
        # noinspection PyUnresolvedReferences
        language_dict = {f'.{member.value}': member.value for member in Language}
        language = language_dict.get(extension, Language.CPP.value)
        # RecursiveCharacterTextSplitter.get_separators_for_language(language)  # todo this is not very perfect
        text_splitter = RecursiveCharacterTextSplitter.from_language(
            language=language, chunk_size=RAG_CHUNK_SIZE, chunk_overlap=0
        )
        return text_splitter
    if extension == '.md':
        text_splitter = MarkdownTextSplitter(
            chunk_size=RAG_CHUNK_SIZE, chunk_overlap=0
        )
        return text_splitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE, chunk_overlap=0
    )
    return text_splitter


def extract_contents(destination: str) -> Tuple[str, Optional[Dict], Dict[str, str]]:
    contents = None
    parsed_pdf_document = None  # special handling for pdfs
    error = None
    if is_pdf(destination):
        parsed_pdf_document = parse_pdf_with_grobid(destination)
        contents = make_pdf_prompt(parsed_pdf_document)

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
        error = {"error": "sqlite Databases are not supported yet. If you need this, open a Github Issue. Or try the raw SQL text queries."}

    else:
        mime_type = get_mime_type(destination)
        error = {"error": f"Unknown file type {mime_type}. If you need this, open a Github Issue."}
    return contents, parsed_pdf_document, error


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


def get_context_from_rag(query: str, vector_store: Optional[FAISS], num_docs: int = RAG_NUM_DOCS) -> Tuple[Optional[str], List[Dict]]:
    context = None
    metadata = []
    if vector_store:
        # query = transform_query(query)  # Do not use, because it clears the cache and we have to process everything again
        docs = search_and_rerank_docs(num_docs, query, vector_store)
        context, metadata = rag_context(docs)
    return context, metadata


def search_and_rerank_docs(num_docs: int, query: str, vector_store: FAISS):
    if is_importable('flashrank') and False:
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
        return docs

    elif is_importable('FlagEmbedding'):
        from FlagEmbedding import FlagReranker
        reranker = FlagReranker('BAAI/bge-reranker-large')
        print('using flag reranker')
        rawdocs = vector_store.similarity_search(query, k=num_docs * 2)
        queries = []
        for d in rawdocs:
            queries.append([query, d.page_content])
        scores = reranker.compute_score(queries)
        sorted_docs = sorted(zip(scores, rawdocs), reverse=True)
        return [b for a, b in sorted_docs[:num_docs]]

    else:
        print('no flashrank available')
        docs = vector_store.similarity_search(query, k=num_docs)  #
        return docs


def transform_query(query: str, use_llm=False) -> str:
    if not use_llm:
        return query
    # This is called query transform, todo: The problem is: It will overwrite the llama.cpp cache
    query_gen_str = """Provide a better search query for a search engine to answer the given question. Question: {query}\nAnswer:"""
    post_data = get_llama_default_parameters({})
    post_data['stream'] = False
    post_data['prompt'] = query_gen_str.format(query=query)
    response = requests.request(method="POST",
                                url=urllib.parse.urljoin(LLAMA_API, "/completion"),
                                data=json.dumps(post_data),
                                stream=False)
    return response.json()['content'].strip()
