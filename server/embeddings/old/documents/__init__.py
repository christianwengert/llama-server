from typing import List

from langchain.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain.text_splitter import TokenTextSplitter, RecursiveCharacterTextSplitter, MarkdownTextSplitter, LatexTextSplitter, PythonCodeTextSplitter


def split_text(filepath: str, chunk_size: int, chunk_overlap: int) -> List[Document]:
    pass


def split_markdown(filepath: str, chunk_size: int, chunk_overlap: int) -> List[Document]:
    with open(filepath, 'r') as f:
        markdown_text = f.read()

    markdown_splitter = MarkdownTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = markdown_splitter.create_documents([markdown_text])
    return docs


def split_pdf(filepath: str, chunk_size: int, chunk_overlap: int) -> List[Document]:
    # Load a PDF
    loader = PyPDFLoader(filepath)
    # Split into pages
    pages = loader.load_and_split()
    # text_splitter = TokenTextSplitter(
    #     chunk_size=chunk_size,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
    #     chunk_overlap=chunk_overlap,
    #     # length_function=len,
    # )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=chunk_overlap,
    )
    texts = text_splitter.split_documents(pages)
    return texts
