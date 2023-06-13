from ctransformers.langchain import CTransformers
from langchain import ConversationChain
from langchain.memory import ConversationTokenBufferMemory
from models import MODEL_PATH, STARCHAT_PROMPT

model = f'{MODEL_PATH}/starchat-alpha-ggml-q5_0.bin'

llm = CTransformers(
    model='danforbes/santacoder-ggml-q4_1',
    model_file=model,
    model_type="starcoder",
    config=dict(
        stream=True,
        temperature=0.1,
        batch_size=8,
        threads=8,
        context_length=8192,
        stop='<|end|>'  # \n<|user|>'
    ),
    verbose=True
    # lib="/Users/christianwengert/src/ctransformers/build/lib/libctransformers.dylib"
)

prompt = STARCHAT_PROMPT

memory = ConversationTokenBufferMemory(llm=llm,
                                       memory_key="history",
                                       human_prefix='<|user|>',
                                       ai_prefix='<|assistant|>',
                                       return_messages=False,
                                       max_token_limit=4096)

conversation = ConversationChain(
    llm=llm,
    # prompt=prompt,
    verbose=True,
    memory=memory
)
conversation.prompt = prompt


questions = [
    'write an implementation of fizz buzz in Go',
    'write python code for bubble sort',
    'show me how to implement a calculation of the median value of an array of numbers in C',
]

for question in questions:
    a = conversation.predict(input=question)
    print(a)
