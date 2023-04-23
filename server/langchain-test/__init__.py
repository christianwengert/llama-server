from langchain.chat_models import ChatOpenAI
from langchain.llms import LlamaCpp
from langchain.embeddings import LlamaCppEmbeddings
# from langchain.chat_models import PromptLayerChatOpenAI

from langchain import PromptTemplate, LLMChain, LLMMathChain, ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
# template = """Question: {question}
#
# Answer: Let's think step by step."""
#
# prompt = PromptTemplate(template=template, input_variables=["question"])

llm = LlamaCpp(model_path="/Users/christianwengert/src/llama/alpaca.cpp-webui/bin/vicuna.ggml.bin",
               temperature=0.8, n_threads=8,
               n_ctx=2048,
               n_batch=512,
               max_tokens=256,
               )

# llm_chain = LLMChain(prompt=prompt, llm=llm)


template = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions."
system_message_prompt = SystemMessagePromptTemplate.from_template(template)
human_template="{text}"
human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

chain = LLMChain(llm=llm, prompt=chat_prompt)

# https://python.langchain.com/en/latest/modules/memory/getting_started.html
conversation = ConversationChain(
    llm=llm,
    verbose=True,
    memory=ConversationBufferMemory()
)

a = conversation.predict(input="write a python implementation of bubble sort")

b = conversation.predict(input="Remove the comments")

c = conversation.predict(input="Rename the function to sosort")



question = "What NFL team won the Super Bowl in the year Justin Bieber was born?"

a = conversation.predict(input=question)


llm_math = LLMMathChain(llm=llm, verbose=True)
a = llm_math.run("What is 13 raised to the .3432 power?")

conversation = ConversationChain(llm=llm, verbose=True)
from langchain.chains.conversation.memory import ConversationBufferWindowMemory

# We are going to set the memory to go back 4 turns
window_memory = ConversationBufferWindowMemory(k=4)
ChatOpenAI

conversation2 = ConversationChain(
    llm=llm,
    verbose=True,
    memory=window_memory
)




print(a)

