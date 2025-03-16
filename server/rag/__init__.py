import hashlib
import json
import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from urllib.parse import urlparse, parse_qs
from flask import Request
from langchain.text_splitter import TextSplitter, Language, RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document
from utils.filesystem import list_directories, is_source_code_file, is_pdf, is_json, is_text_file, is_sqlite, \
    get_mime_type, is_importable
# noinspection PyPackageRequirements
from marker.converters.pdf import PdfConverter
# noinspection PyPackageRequirements
from marker.models import create_model_dict
# noinspection PyPackageRequirements
from marker.output import text_from_rendered

RAG_CHUNK_SIZE = 2048
RAG_DATA_DIR = os.path.abspath(os.path.dirname(__file__) + '/../../data')
RAG_NUM_DOCS = 5

RAG_DEFAULT_MODEL = 'BAAI/bge-m3'


def get_embeddings(model_name: str) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name,
                                 encode_kwargs={
                                     'normalize_embeddings': True  # set True to compute cosine similarity
                                 },
                                 model_kwargs={'device': 'cpu'})


def rag_context(docs: List[Document]) -> Tuple[str, List[Dict]]:
    context = ""
    metadata = []
    for d in docs:
        context += "\n\nThis is one piece of context:\n" + d.page_content
        metadata.append(d.metadata)
    return context, metadata


def get_available_collections(username: str = None) -> Dict[str, List[Dict[str, str]]]:
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

            # noinspection PyBroadException
            try:  # Load meta data
                config_file = user_dir / collection / 'config.json'
                if not config_file.exists():
                    continue
                with open(config_file, 'r') as f:
                    data = json.load(f)
                if collection == data.get('hashed_name'):
                    collections['user'].append(data)  # just get all metadata at once
            except Exception as _e:
                pass

    return collections


def create_or_open_collection(index_name: str, username: Optional[str], public: Optional[bool]) -> Tuple[FAISS, Path, str]:

    # Check if index exists already
    collections = get_available_collections(username)

    # current_time = str(time.time_ns())  # Ensure uniqueness even with same filenames
    hashed_index_name = hashlib.sha256(index_name.encode()).hexdigest()[:32]

    if public:
        data_dir = Path(RAG_DATA_DIR) / Path('common')
        for item in collections['user']:
            if hashed_index_name == item.get('hashed_name'):
                embeddings = get_embeddings(item.get('model'))
                return FAISS.load_local(data_dir / hashed_index_name, embeddings), data_dir / hashed_index_name, hashed_index_name
        # otherwise we will create a new DB
    else:
        data_dir = Path(RAG_DATA_DIR) / Path('user') / Path(username)
        for item in collections['user']:
            if hashed_index_name == item.get('hashed_name'):
                embeddings = get_embeddings(item.get('model'))
                return FAISS.load_local(data_dir / hashed_index_name, embeddings), data_dir / hashed_index_name, hashed_index_name

        # otherwise we will create a new DB

    path = data_dir / hashed_index_name
    doc = Document(page_content="")  # We need to create a doc to initialize the docstore, then we gonna delete it again
    index = FAISS.from_documents([doc], get_embeddings(RAG_DEFAULT_MODEL))
    # Todo: This is langchain stuff, too lazy to do it differently
    # noinspection PyProtectedMember,PyUnresolvedReferences
    index.delete([list(index.docstore._dict.keys())[0]])  # Empty again, this is
    index.save_local(path)

    with open(path / 'config.json', 'w') as f:
        json.dump(dict(model=RAG_DEFAULT_MODEL, name=index_name, hashed_name=hashed_index_name), f)

    return index, path, hashed_index_name


def load_collection(collection: str, username: str) -> Optional[FAISS]:
    collections = get_available_collections(username)

    for key in ['user', 'common']:  # first check for same name user!
        for item in collections[key]:
            if collection == item.get('hashed_name'):
                data_dir = RAG_DATA_DIR / Path(key)
                if key == 'user':
                    data_dir = data_dir / Path(username)

                # noinspection PyBroadException
                try:
                    with open(data_dir / Path(collection) / 'config.json', 'r') as f:
                        data = json.load(f)
                    embeddings = get_embeddings(data.get('model'))
                    return FAISS.load_local(data_dir / Path(collection), embeddings)
                except Exception as _e:
                    logging.warning(f'Found a problem loading the collection: {_e}')
                    return None
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
        text_splitter = RecursiveCharacterTextSplitter.from_language(
            language=language, chunk_size=RAG_CHUNK_SIZE, chunk_overlap=0
        )
        return text_splitter
    if extension in ['.md', '.pdf']:  # marker results in markdown
        text_splitter = MarkdownTextSplitter(
            chunk_size=RAG_CHUNK_SIZE, chunk_overlap=0
        )
        return text_splitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE, chunk_overlap=0
    )
    return text_splitter


def extract_contents(destination: str) -> Tuple[str, Dict[str, str]]:
    contents = None
    # parsed_pdf_document = None  # special handling for pdfs
    error = None
    if is_pdf(destination):
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # For some reason, transformers decided to use .isin for a simple op, which is not supported on MPS
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
        rendered = converter(destination)
        markdown, _, images = text_from_rendered(rendered)
        # parsed_pdf_document = parse_pdf_with_grobid(destination)
        # contents = make_pdf_prompt(markdown)
        contents = markdown

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
    return contents, error


# def make_pdf_prompt(article: str):
#     prompt_text = "The following is an article on which I will ask questions. After processing this article, acknowledge the following with OK."
#     prompt_text += "\n<article>\n"
#     prompt_text += article
#     prompt_text += "\n</article>\n"
#     return prompt_text


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
    else:
        logging.warning('no flashrank available')
        docs = vector_store.similarity_search(query, k=num_docs)  #
        return docs
