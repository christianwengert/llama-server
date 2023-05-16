import os
from langchain import LlamaCpp, FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import TextLoader
from langchain.embeddings.llamacpp import LlamaCppEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import CharacterTextSplitter, PythonCodeTextSplitter


# MODEL_PATH = "/Users/christianwengert/src/llama/alpaca.cpp-webui/bin/vicuna.ggml.bin"
MODEL_PATH = "/Users/christianwengert/Downloads/Wizard-Vicuna-13B-Uncensored.ggml.q5_0.bin"
ROOT_DIR = '/Users/christianwengert/src/filedrop/app/modules/'
# from langchain.text_splitter import PythonCodeTextSplitter

docs = []
for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
    for file in filenames:
        if file.endswith('.py') and '/.venv/' not in dirpath:
            # noinspection PyBroadException
            try:
                loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
                docs.extend(loader.load_and_split())
            except Exception as e:
                pass
print(f'Number of files: {len(docs)}')

text_splitter = PythonCodeTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(docs)
print(f"Number of texts: {len(texts)}")

embeddings = LlamaCppEmbeddings(model_path=MODEL_PATH, n_ctx=2048, n_threads=8)

db = FAISS.from_documents(texts, embeddings)
# db = Chroma.from_documents(texts, embeddings)
retriever = db.as_retriever()
# retriever.search_kwargs['distance_metric'] = 'cos'
# retriever.search_kwargs['fetch_k'] = 20
# retriever.search_kwargs['maximal_marginal_relevance'] = True
# retriever.search_kwargs['k'] = 20

llm = LlamaCpp(model_path=MODEL_PATH,
               temperature=0.8,
               n_threads=8,
               n_ctx=2048,
               n_batch=512,
               max_tokens=256,
               )

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
qa = ConversationalRetrievalChain.from_llm(llm, retriever, memory=memory)

questions = [
    "What is the class hierarchy?",
    # "What classes are derived from the Chain class?",
    # "What classes and functions in the ./langchain/utilities/ forlder are not covered by unit tests?",
    "What one improvement do you propose in code in relation to the class herarchy for the Chain class?",
]
chat_history = []

for question in questions:
    result = qa({"question": question, "chat_history": chat_history})

    chat_history.append((question, result['answer']))
    print(f"-> **Question**: {question} \n")
    print(f"**Answer**: {result['answer']} \n")


# chain = load_summarize_chain(llm, chain_type="map_reduce")
# chain.run(docs)
