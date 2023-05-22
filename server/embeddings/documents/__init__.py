from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import TokenTextSplitter


def split_pdf(filepath):
    # Load a PDF
    loader = PyPDFLoader(filepath)
    # Split into pages
    pages = loader.load_and_split()
    text_splitter = TokenTextSplitter(
        chunk_size=200,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=20,
        # length_function=len,
    )
    texts = text_splitter.split_documents(pages)
    return texts
