from typing import List

from langchain.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain.text_splitter import TokenTextSplitter, RecursiveCharacterTextSplitter


def split_pdf(filepath: str, chunk_size: int, chunk_overlap: int) -> List[Document]:
    # Load a PDF
    loader = PyPDFLoader(filepath)
    # Split into pages
    pages = loader.load_and_split()
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=chunk_overlap,
        # length_function=len,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=chunk_overlap,
    )
    texts = text_splitter.split_documents(pages)
    return texts
