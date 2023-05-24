import os.path
from langchain import LlamaCpp, FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT
from langchain.chains.conversational_retrieval.base import BaseConversationalRetrievalChain
from langchain.embeddings import LlamaCppEmbeddings, HuggingFaceEmbeddings
from langchain.memory import ConversationTokenBufferMemory
from embeddings import get_index
from embeddings.documents import split_pdf
from models import MODEL_PATH, MODELS


EMBEDDINGS_MODEL = 'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0.bin'
USE_HUGGING = True


def embed_pdf(project_name: str, filepath: str, model: str, run_test=False) -> BaseConversationalRetrievalChain:

    prompt, stop, n_ctx = MODELS[model]

    model_path = os.path.join(MODEL_PATH, f'{model}.bin')

    filename = os.path.basename(filepath)
    texts = split_pdf(filepath, chunk_size=1024, chunk_overlap=16)
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

    retriever.search_kwargs['distance_metric'] = 'cos'
    retriever.search_kwargs['fetch_k'] = 100
    retriever.search_kwargs['maximal_marginal_relevance'] = True
    retriever.search_kwargs['k'] = 3
    retriever.search_kwargs['reduce_k_below_max_tokens'] = True
    retriever.search_kwargs['max_tokens_limit'] = 1024

    llm = LlamaCpp(model_path=model_path,
                   temperature=0.0,
                   n_threads=8,
                   n_ctx=n_ctx,
                   n_batch=512,
                   max_tokens=256,
                   )

    chain_type = "stuff"
    return_source_documents = chain_type != 'stuff'
    qa = ConversationalRetrievalChain.from_llm(llm,
                                               retriever,
                                               condense_question_prompt=CONDENSE_QUESTION_PROMPT,
                                               chain_type=chain_type,
                                               memory=ConversationTokenBufferMemory(llm=llm, memory_key="chat_history", return_messages=True, max_token_limit=1024),
                                               return_source_documents=return_source_documents,
                                               max_tokens_limit=1500)

    if run_test:

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

    return qa


if __name__ == '__main__':
    model = "wizard-mega-13B.ggml.q5_0"  # "Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0"
    # embed_pdf('testproject', '/Users/christianwengert/Downloads/234.pdf', model)
    embed_pdf('testproject', '/Users/christianwengert/Downloads/2014-070.pdf', model, run_test=True)
