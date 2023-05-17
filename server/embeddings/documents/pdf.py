import os.path
from langchain import FAISS, LlamaCpp
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from models import MODEL_PATH

INDEX_DIR = "/Users/christianwengert/Downloads/"

INDEX_NAME = "index"


def embed_pdf(project_name: str, filepath: str, model: str):
    # Load a PDF
    filename = os.path.basename(filepath)
    loader = PyPDFLoader(filepath)
    # Split into pages
    pages = loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=256,
        length_function=len,
    )
    texts = text_splitter.split_documents(pages)
    print(f"Number of texts: {len(texts)}")

    # Create embeddings and store in vector DB
    embeddings = LlamaCppEmbeddings(model_path=os.path.join(MODEL_PATH, model),
                                    n_threads=8,
                                    n_ctx=2048,
                                    n_batch=512)

    # save, resp load if exists
    index_file = os.path.join(INDEX_DIR, f"{project_name}---{filename}---{model}.faiss")
    if os.path.exists(index_file):  # todo: make the name dependeing on model and document
        print('Loading existing index')
        db = FAISS.load_local(index_file, embeddings, index_name=INDEX_NAME)
    else:
        print('Creating index')
        db = FAISS.from_documents(texts, embeddings)
        db.save_local(index_file, index_name=INDEX_NAME)

    retriever = db.as_retriever()

    llm = LlamaCpp(model_path=os.path.join(MODEL_PATH, model),
                   temperature=0.8,
                   n_threads=8,
                   n_ctx=2048,
                   n_batch=512,
                   max_tokens=512,
                   )

    chain = load_summarize_chain(llm, chain_type="refine")
    search = db.similarity_search(" ", k=8)
    # docs = retriever.get_relevant_documents("this paper")  # equivalent to search?

    summary = chain.run(input_documents=search, question="Write a summary within 150 words.")
    print(summary)

    qa = ConversationalRetrievalChain.from_llm(llm, retriever, return_source_documents=True)
    questions = [
        "What is this paper about?",
        "What primitives are supported?",
        "has TLS1.3 been formally verified?"
    ]

    chat_history = list()

    for question in questions:
        print(f"-> **Question**: {question} \n")
        result = qa({"question": question, "chat_history": chat_history})
        chat_history.append((question, result['answer']))

        print(f"**Answer**: {result['answer']} \n")
        print(result['source_documents'])


if __name__ == '__main__':
    model = "wizard-vicuna-13B.ggml.q5_0.bin"
    embed_pdf('testproject', '/Users/christianwengert/Downloads/234.pdf', model)
