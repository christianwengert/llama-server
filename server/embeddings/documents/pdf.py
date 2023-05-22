import os.path
from langchain import LlamaCpp, FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings, HuggingFaceEmbeddings
from langchain.memory import ConversationTokenBufferMemory
from langchain.text_splitter import TokenTextSplitter
from embeddings import get_index
from models import MODEL_PATH, MODELS


EMBEDDINGS_MODEL = 'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0.bin'
USE_HUGGING = True


def embed_pdf(project_name: str, filepath: str, model: str):

    try:
        prompt, stop, n_ctx = MODELS[model]
    except KeyError:
        raise KeyError

    model_path = os.path.join(MODEL_PATH, f'{model}.bin')

    # Load a PDF
    filename = os.path.basename(filepath)
    loader = PyPDFLoader(filepath)
    # Split into pages
    pages = loader.load_and_split()
    text_splitter = TokenTextSplitter(
        chunk_size=200,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=20,
        # length_function=len,
    )
    texts = text_splitter.split_documents(pages)
    print(f"Number of texts: {len(texts)}")

    if USE_HUGGING:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        db = FAISS.from_documents(texts, embeddings)
    else:
        # Create embeddings and store in vector DB
        embeddings = LlamaCppEmbeddings(model_path=os.path.join(MODEL_PATH, EMBEDDINGS_MODEL),
                                        n_threads=8,
                                        n_ctx=n_ctx,
                                        n_batch=512)
        db = get_index(embeddings, filename, EMBEDDINGS_MODEL, project_name, texts)
    print('index loaded')
    retriever = db.as_retriever()

    llm = LlamaCpp(model_path=model_path,
                   temperature=0.0,
                   n_threads=8,
                   n_ctx=n_ctx,
                   n_batch=512,
                   max_tokens=1024,
                   )
    # 'refine' chain returns empty string?
    # chain = load_summarize_chain(llm, chain_type="map_reduce")
    # search = db.similarity_search(" ", k=4)

    # from langchain.chains.question_answering import load_qa_chain
    # chain = load_qa_chain(llm, chain_type="map_reduce")

    # summary = chain.run(input_documents=search, question="Write a summary within 150 words.")
    # print(summary)

    chain_type = "stuff"
    return_source_documents = chain_type != 'stuff'
    qa = ConversationalRetrievalChain.from_llm(llm,
                                               retriever,
                                               condense_question_prompt=CONDENSE_QUESTION_PROMPT,
                                               chain_type=chain_type,
                                               memory=ConversationTokenBufferMemory(llm=llm, memory_key="chat_history", return_messages=True),
                                               return_source_documents=return_source_documents)
    # print(qa.llm_chain.template)  also chain.combine_chain.prompt

    questions = [
        "What is this paper about?",
        "Who are the authors?",
        "What primitives are supported?",
        "has TLS1.3 been formally verified?"
    ]

    chat_history = list()

    for question in questions:
        print(f"-> **Question**: {question} \n")
        result = qa({"question": question, "chat_history": chat_history})
        chat_history.append((question, result['answer']))
        print(f"**Answer**: {result['answer']} \n")
        # print(result['source_documents'])


if __name__ == '__main__':
    model = "wizard-mega-13B.ggml.q5_0"  # "Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0"
    embed_pdf('testproject', '/Users/christianwengert/Downloads/234.pdf', model)
