import json
import os

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.vectorstores import FAISS


def build_or_load_stackexchange_collection(path: str) -> FAISS:
    embeddings = HuggingFaceEmbeddings(model_name='BAAI/bge-large-en-v1.5',
                                       encode_kwargs={'normalize_embeddings': True},
                                       # set True to compute cosine similarity
                                       )

    db = None
    for folder in os.listdir(path):
        docs = []
        json_file = f'{path}/{folder}/data.json'
        if not os.path.exists(json_file):
            continue

        if os.path.exists(f'{folder}.faiss'):
            tmpdb = FAISS.load_local(f'{folder}.faiss', embeddings)
            if db:
                db.merge_from(tmpdb)
            else:
                db = tmpdb

            continue

        with open(json_file, 'r') as f:
            data = json.load(f)

        for element in data.values():
            answers = element.pop('answers')
            if not answers:
                continue
            title = element.pop('title')
            question = element.pop('question')
            d = Document(
                page_content=f'{title}\n\n{question}',
                metadata=dict(
                    answers=answers,
                    source=f'{path}{f}',
                    **element
                )
            )
            docs.append(d)

        tmpdb = FAISS.from_documents(docs, embeddings)
        tmpdb.save_local(f'{folder}.faiss')
        if db:
            db.merge_from(tmpdb)
        else:
            db = tmpdb
    return db
