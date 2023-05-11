# WIP: Load entire PDF into an indexer

import os.path
from langchain import FAISS, LlamaCpp
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings
# from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

model = "wizard-vicuna-13B.ggml.q5_0.bin"
MODEL_PATH = f"/Users/christianwengert/Downloads/{model}"

project_name = "verifpal"
# Load a PDF
file_or_folder_name = "manual-1.pdf"
loader = PyPDFLoader(f"/Users/christianwengert/Downloads/{file_or_folder_name}")
# Split into pages
pages = loader.load_and_split()

#
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024,
    chunk_overlap=256,
    length_function=len,
)

texts = text_splitter.split_documents(pages)
print(f"Number of texts: {len(texts)}")

# Store in vector DB
embeddings = LlamaCppEmbeddings(model_path=MODEL_PATH, n_threads=8, n_ctx=2048, n_batch=512)

INDEX_NAME = "index"
index_file = os.path.join("/Users/christianwengert/Downloads/", f"{project_name}---{file_or_folder_name}---{model}.faiss")

if os.path.exists(index_file):  # todo: make the name dependeing on model and document
    print('Loading existing index')
    db = FAISS.load_local(index_file, embeddings, index_name=INDEX_NAME)
else:
    print('Creating index')
    db = FAISS.from_documents(texts, embeddings)
    db.save_local(index_file, index_name=INDEX_NAME)

retriever = db.as_retriever()

llm = LlamaCpp(model_path=MODEL_PATH,
               temperature=0.8,
               n_threads=8,
               n_ctx=2048,
               n_batch=512,
               max_tokens=256,
               )

# memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
# qa = ConversationalRetrievalChain.from_llm(llm, retriever, memory=memory, return_source_documents=True)
qa = ConversationalRetrievalChain.from_llm(llm, retriever, return_source_documents=True)
questions = [
    "What is this paper about?",
    "What primitives are supported?",
    "who is the evil man fighting verifgal"
]

#
# from langchain.text_splitter import CharacterTextSplitter
# CharacterTextSplitter.from_huggingface_tokenizer(...)
# CharacterTextSplitter.from_huggingface_tokenizer(...)
# from langchain.text_splitter import TokenTextSplitter
# from langchain.chains.conversational_retrieval.prompts import QA_PROMPT  todo
chat_history = list()

docs = retriever.get_relevant_documents("what did he say abotu ketanji brown jackson")

for question in questions:
    print(f"-> **Question**: {question} \n")
    result = qa({"question": question, "chat_history": chat_history})
    chat_history.append((question, result['answer']))

    print(f"**Answer**: {result['answer']} \n")
    print(result['source_documents'])
