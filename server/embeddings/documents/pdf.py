import os.path
from langchain import LlamaCpp
from langchain.chains import ConversationalRetrievalChain, LLMSummarizationCheckerChain
# from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings, HuggingFaceEmbeddings
from langchain.memory import ConversationTokenBufferMemory
from langchain.text_splitter import TokenTextSplitter
from embeddings import get_index
from models import MODEL_PATH, MODELS
from langchain.cache import InMemoryCache
import langchain
langchain.llm_cache = InMemoryCache()


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
        chunk_size=256,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=32,
        # length_function=len,
    )
    texts = text_splitter.split_documents(pages)
    print(f"Number of texts: {len(texts)}")

    # Create embeddings and store in vector DB

    embeddings = LlamaCppEmbeddings(model_path=os.path.join(MODEL_PATH, 'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0.bin'),
                                    n_threads=8,
                                    n_ctx=n_ctx,
                                    n_batch=512)
    # llama = LlamaCppEmbeddings(model_path="/path/to/model/ggml-model-q4_0.bin")
    # embeddings = HuggingFaceEmbeddings()
    # embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    db = get_index(embeddings, filename, model, project_name, texts)

    retriever = db.as_retriever()

    llm = LlamaCpp(model_path=model_path,
                   temperature=0.8,
                   n_threads=8,
                   n_ctx=n_ctx,
                   n_batch=512,
                   max_tokens=512,
                   )
    # 'refine' chain returns empty string?
    # chain = load_summarize_chain(llm, chain_type="map_reduce")
    # search = db.similarity_search(" ", k=4)

    # summary = chain.run(input_documents=search, question="Write a summary within 150 words.")
    # print(summary)

    qa = ConversationalRetrievalChain.from_llm(llm,
                                               retriever,
                                               chain_type="map_reduce",
                                               memory=ConversationTokenBufferMemory(llm=llm, max_token_limit=llm.n_ctx / 2),
                                               return_source_documents=True)
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

    # summarization
    # cc = LLMSummarizationCheckerChain(llm=llm, verbose=True, max_checks=2)
    # cc.run(arricel)


if __name__ == '__main__':
    model = "stable-vicuna-13B.ggml.q5_0"
    embed_pdf('testproject', '/Users/christianwengert/Downloads/234.pdf', model)
