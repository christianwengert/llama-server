import os.path
from langchain.document_loaders import TextLoader
from langchain.text_splitter import PythonCodeTextSplitter


def split_codebase(filepath: str, chunk_size: int, chunk_overlap: int):
    docs = []
    for dirpath, dirnames, filenames in os.walk(filepath):
        for file in filenames:
            if file.endswith('.py') and '/.venv/' not in dirpath:
                # noinspection PyBroadException
                try:
                    loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
                    docs.extend(loader.load_and_split())
                except Exception:
                    pass
    print(f'Number of files: {len(docs)}')
    text_splitter = PythonCodeTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    texts = text_splitter.split_documents(docs)
    return texts