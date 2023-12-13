import os
from pathlib import Path
from typing import List, Tuple, Literal, Optional
from urllib.parse import urlparse, parse_qs

from flask import Request
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document

from utils.filesystem import list_directories, find_files

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


def rag_prompt(docs: List[Document], question: str) -> str:
    context = []
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

    prompt = f"""
    You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. The context consists of questions and one or more relevant answers to each question. Each question in the context starts with Q: and each answer in the context starts with A:. If you don't know the answer, just say that you don't know.

    Context: 
    {context_string}

    Question:
    {question}

    Answer:
    """

    return prompt


def get_available_collections(username: str = None) -> List[Tuple[Literal['common', 'user'], str]]:
    common_dir = Path(RAG_DATA_DIR) / Path('common')

    common_collections = list_directories(common_dir)

    collections = []

    for collection in common_collections:
        # indices = find_files(common_dir / collection, '.faiss')
        collections.append(('common', collection))

    if username:
        user_dir = Path(RAG_DATA_DIR) / Path('user') / Path(username)
        _user_collections = list_directories(user_dir)
        # TODO
    return collections


def load_collection(collection: str) -> Optional[FAISS]:
    collections = get_available_collections()
    db = None
    for corpus, name in collections:
        if name == collection:
            indices = find_files(RAG_DATA_DIR / Path(corpus) / Path(name), '.faiss')

            db = None
            for index in indices:
                tmp = FAISS.load_local(os.path.dirname(index), RAG_EMBEDDINGS)
                if db:
                    db.merge_from(tmp)
                else:
                    db = tmp

    return db


def get_collection_from_query(request: Request) -> str:
    collection = None
    if request.referrer:
        parsed_url = urlparse(request.referrer)
        query_params = parse_qs(parsed_url.query)
        collections = query_params.get('collection')  # Returns a vector....
        if collections and len(collections) == 1:
            collection = collections[0]  # Just take one, there should not be more
    return collection
