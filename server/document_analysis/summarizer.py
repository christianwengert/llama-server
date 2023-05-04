from langchain import LlamaCpp
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain


MODEL_PATH = "/Users/christianwengert/Downloads/OpenAssistant-30B-epoch7.ggml.q5_0.bin"

llm = LlamaCpp(model_path=MODEL_PATH,
               temperature=0.8,
               n_threads=8,
               n_ctx=2048,
               n_batch=512,
               max_tokens=256,
               )

loader = PyPDFLoader("/Users/christianwengert/Downloads/2012-688.pdf")
pages = loader.load_and_split()
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0, separator='\n')
texts = text_splitter.split_documents(pages)
print(f"Number of texts: {len(texts)}")


chain = load_summarize_chain(llm, chain_type="map_reduce")
output = chain.run(texts[0:5])  # chain.run(texts)
print(output)