from langchain import FAISS, LlamaCpp
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import LlamaCppEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import CharacterTextSplitter, PythonCodeTextSplitter, NLTKTextSplitter

MODEL_PATH = "/Users/christianwengert/Downloads/wizard-vicuna-13B.ggml.q5_0.bin"


from transformers import GPT2TokenizerFast
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")


loader = PyPDFLoader("/Users/christianwengert/Downloads/manual-1.pdf")



# splitter = CharacterTextSplitter.from_huggingface_tokenizer(tokenizer, chunk_size=200, chunk_overlap=100)

pages = loader.load_and_split()

#
# text_splitter = CharacterTextSplitter(
#     separator="\n",
#     chunk_size=1024,
#     chunk_overlap=256,
#     length_function=len,
# )


from langchain.text_splitter import RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter(
    # Set a really small chunk size, just to show.
    chunk_size=1024,
    chunk_overlap =256,
    length_function=len,
)


# text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0, separator='\n')
texts = text_splitter.split_documents(pages)
print(f"Number of texts: {len(texts)}")
# Make sure we do not have more than x tokens
# texts[0].page_content = texts[0].page_content[0:1000]

db = FAISS.from_documents(texts, LlamaCppEmbeddings(model_path=MODEL_PATH, n_threads=8, n_ctx=2048, n_batch=512))

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
]
chat_history = []

for question in questions:
    result = qa({"question": question, "chat_history": chat_history})

    chat_history.append((question, result['answer']))
    print(f"-> **Question**: {question} \n")
    print(f"**Answer**: {result['answer']} \n")