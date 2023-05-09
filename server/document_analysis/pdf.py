import os.path

from langchain import FAISS, LlamaCpp
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter


MODEL_PATH = "/Users/christianwengert/Downloads/wizard-vicuna-13B.ggml.q5_0.bin"


# Load a PDF
loader = PyPDFLoader("/Users/christianwengert/Downloads/manual-1.pdf")
# Split into pages
pages = loader.load_and_split()

#
text_splitter = RecursiveCharacterTextSplitter(
    # Set a really small chunk size, just to show.
    chunk_size=2048,
    chunk_overlap=256,
    length_function=len,
)

texts = text_splitter.split_documents(pages)
print(f"Number of texts: {len(texts)}")

# Store in vector DB
embeddings = LlamaCppEmbeddings(model_path=MODEL_PATH, n_threads=8, n_ctx=2048, n_batch=512)

if os.path.exists('~/Downloads/verifpal-manual.faiss'):
    print('Loading existing index')
    db = FAISS.load_local('~/Downloads/verifpal-manual.faiss', embeddings, 'index')
else:
    print('Creating index')
    db = FAISS.from_documents(texts, embeddings)
    db.save_local('~/Downloads/verifpal-manual.faiss')

retriever = db.as_retriever()

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
    "What is this paper about?",
    "What primitives are supported?"
]

chat_history = list()

for question in questions:
    result = qa({"question": question, "chat_history": chat_history})
    chat_history.append((question, result['answer']))

    print(f"-> **Question**: {question} \n")
    print(f"**Answer**: {result['answer']} \n")
