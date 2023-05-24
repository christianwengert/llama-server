import os

from langchain import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.conversational_retrieval.base import BaseConversationalRetrievalChain
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.memory import ConversationTokenBufferMemory

from embeddings.code import split_codebase
from models import MODELS, MODEL_PATH
from models.interruptable_llama import InterruptableLlamaCpp

EMBEDDINGS_MODEL = 'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0.bin'
USE_HUGGING = True
ROOT_DIR = '/Users/christianwengert/src/filedrop/app'


def embed_code(project_name: str, filepath: str, model: str, run_test=False) -> BaseConversationalRetrievalChain:

    prompt, stop, n_ctx = MODELS[model]

    model_path = os.path.join(MODEL_PATH, f'{model}.bin')

    texts = split_codebase(filepath, chunk_size=1024, chunk_overlap=0)

    print(f"Number of texts: {len(texts)}")

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(texts, embeddings)
    retriever = db.as_retriever()

    llm = InterruptableLlamaCpp(model_path=model_path,
                                temperature=0.1,
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
                                               memory=ConversationTokenBufferMemory(llm=llm, memory_key="chat_history",
                                                                                    return_messages=True,
                                                                                    max_token_limit=1024),
                                               return_source_documents=return_source_documents,
                                               max_tokens_limit=1500)

    if run_test:
        questions = [
            "What is the class hierarchy?",
            "What one improvement do you propose in code in relation to the class herarchy for the Chain class?",
        ]
        chat_history = []

        for question in questions:
            result = qa({"question": question, "chat_history": chat_history})

            chat_history.append((question, result['answer']))
            print(f"-> **Question**: {question} \n")
            print(f"**Answer**: {result['answer']} \n")
    return qa


if __name__ == '__main__':
    model = "wizard-mega-13B.ggml.q5_0"  # "Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0"
    embed_code('test-code', ROOT_DIR, model, run_test=True)
