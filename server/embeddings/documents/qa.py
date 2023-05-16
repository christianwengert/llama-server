# from langchain.document_loaders import TextLoader
# loader = TextLoader("../../state_of_the_union.txt")
# documents = loader.load()
# text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# texts = text_splitter.split_documents(documents)
#
# embeddings = OpenAIEmbeddings()
# docsearch = Chroma.from_documents(texts, embeddings)
#
# # Running Chroma using direct local API.
# # Using DuckDB in-memory for database. Data will be transient.
#
# qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=docsearch.as_retriever())
#
# query = "What did the president say about Ketanji Brown Jackson"
# qa.run(query)
#
# #### combiner
#
# from langchain.chains.question_answering import load_qa_chain
# qa_chain = load_qa_chain(OpenAI(temperature=0), chain_type="stuff")
# qa = RetrievalQA(combine_documents_chain=qa_chain, retriever=docsearch.as_retriever())
#
# query = "What did the president say about Ketanji Brown Jackson"
# qa.run(query)
#


####
# Chat Over Documents with Chat History


from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import TextLoader
loader = TextLoader("../../state_of_the_union.txt")
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
documents = text_splitter.split_documents(documents)

embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embeddings)
from langchain.memory import ConversationBufferMemory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
qa = ConversationalRetrievalChain.from_llm(OpenAI(temperature=0), vectorstore.as_retriever(), memory=memory)

query = "What did the president say about Ketanji Brown Jackson"
result = qa({"question": query})

result["answer"]

chat_history = [(query, result["answer"])]
query = "Did he mention who she suceeded"
result = qa({"question": query, "chat_history": chat_history})



#Return Source Documents
qa = ConversationalRetrievalChain.from_llm(OpenAI(temperature=0), vectorstore.as_retriever(), return_source_documents=True)




