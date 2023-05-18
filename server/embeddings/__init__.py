import os
from typing import List
from langchain import FAISS
from langchain.embeddings import LlamaCppEmbeddings
from langchain.schema import Document
from langchain.vectorstores import VectorStore


INDEX_NAME = "index"
INDEX_DIR = "/Users/christianwengert/.cache/faiss/"


def get_index(embeddings: LlamaCppEmbeddings, filename: str, model: str, project_name: str, texts: List[Document]) -> VectorStore:
    # save, resp load if exists
    index_file = os.path.join(INDEX_DIR, f"{project_name}---{filename}---{model}.faiss")
    if os.path.exists(index_file):  # todo: make the name dependeing on model and document
        print('Loading existing index')
        db = FAISS.load_local(index_file, embeddings, index_name=INDEX_NAME)
    else:
        print('Creating index')
        db = FAISS.from_documents(texts, embeddings)
        db.save_local(index_file, index_name=INDEX_NAME)
    return db
