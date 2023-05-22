import os.path
from langchain import LlamaCpp, LLMChain
from langchain.chains import ConversationalRetrievalChain  # , LLMSummarizationCheckerChain
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT
# from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings  # , HuggingFaceEmbeddings
from langchain.memory import ConversationTokenBufferMemory, ConversationBufferMemory
from langchain.text_splitter import TokenTextSplitter
from embeddings import get_index
from models import MODEL_PATH, MODELS
# from langchain.cache import InMemoryCache
# import langchain
# langchain.llm_cache = InMemoryCache()


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

    EMBEDDINGS_MODEL = 'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0.bin'

    embeddings = LlamaCppEmbeddings(model_path=os.path.join(MODEL_PATH, EMBEDDINGS_MODEL),
                                    n_threads=8,
                                    n_ctx=n_ctx,
                                    n_batch=512)
    # llama = LlamaCppEmbeddings(model_path="/path/to/model/ggml-model-q4_0.bin")
    # embeddings = HuggingFaceEmbeddings()
    # embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    db = get_index(embeddings, filename, EMBEDDINGS_MODEL, project_name, texts)
    print('index loaded')
    retriever = db.as_retriever()

    llm = LlamaCpp(model_path=model_path,
                   temperature=0.8,
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

    qa = ConversationalRetrievalChain.from_llm(llm,
                                               retriever,
                                               condense_question_prompt=CONDENSE_QUESTION_PROMPT,
                                               chain_type="stuff",
                                               memory=ConversationTokenBufferMemory(llm=llm, memory_key="chat_history", return_messages=True),
                                               return_source_documents=False)
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

    # from langchain.chains.qa_with_sources import load_qa_with_sources_chain
    #
    # question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
    # doc_chain = load_qa_with_sources_chain(llm, chain_type="map_reduce")
    #
    # chain = ConversationalRetrievalChain(
    #     retriever=retriever,
    #     question_generator=question_generator,
    #     combine_docs_chain=doc_chain,
    # )
    #
    # query = "What is the biggest change in TLS 1.3"
    # result = chain({"question": query, "chat_history": chat_history})
    # print(result['answer'])

    # summarization
    # cc = LLMSummarizationCheckerChain(llm=llm, verbose=True, max_checks=2)
    # cc.run(arricel)


if __name__ == '__main__':
    model = "Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0"
    embed_pdf('testproject', '/Users/christianwengert/Downloads/234.pdf', model)
