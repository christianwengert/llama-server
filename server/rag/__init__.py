import os
from pathlib import Path
from typing import List, Tuple, Literal, Optional, Dict
from urllib.parse import urlparse, parse_qs

from flask import Request
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document

from utils.filesystem import list_directories

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

RAG_EMBEDDINGS = HuggingFaceEmbeddings(model_name='BAAI/bge-large-en-v1.5',
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


def get_available_collections(username: str = None) -> Dict[Literal['common', 'user'], List[str]]:
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
    return index, path


def load_collection(collection: str, username: str) -> Optional[FAISS]:
    collections = get_available_collections()

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
