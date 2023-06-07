# from ctransformers import AutoConfig, AutoModelForCausalLM
from ctransformers.langchain import CTransformers
from langchain import ConversationChain
# from langchain.llms import CTransformers
from langchain.memory import ConversationTokenBufferMemory
from models import MODEL_PATH, OPEN_ASSISTANT_TEMPLATE

if False:
    model = f'{MODEL_PATH}/starchat-alpha-ggml-q5_0.bin'


    # llm = AutoModelForCausalLM.from_pretrained('/Users/christianwengert/Downloads/starchat-alpha-ggml-q5_0.bin', model_type='starcoder')

    llm = CTransformers(
        model='NeoDim/starchat-alpha-GGML',
        model_file='/Users/christianwengert/Downloads/starchat-alpha-ggml-q5_0.bin',
        model_type="starcoder",
        config=dict(
            stream=True,
            temperature=0.1,
            batch_size=8,
            threads=8,
            context_length=8192,
            stop='<|end|>'  # \n<|user|>'
            # verbose=True
        ),
        lib="/Users/christianwengert/src/ctransformers/build/lib/libctransformers.dylib"
    )
else:
    model = f'{MODEL_PATH}/Wizard-Vicuna-30B-Uncensored.ggmlv3.q4_0.bin'
    llm = CTransformers(
        model='NeoDim/starchat-alpha-GGML',
        model_file=model,
        model_type="llama",
        config=dict(
            stream=True,
            temperature=0.1,
            batch_size=8,
            threads=8,
            context_length=8192,
            gpu_layers=1,
            stop='<|end|>'  # \n<|user|>'
            # verbose=True
        ),
        lib="/Users/christianwengert/src/ctransformers/build/lib/libctransformers.dylib"
    )
# print(llm("Hello"))
prompt = OPEN_ASSISTANT_TEMPLATE

memory = ConversationTokenBufferMemory(llm=llm, memory_key="history",
                                       return_messages=True,
                                       max_token_limit=4096)

conversation = ConversationChain(
    llm=llm,
    # prompt=prompt,
    verbose=True,
    memory=memory
)

questions = [
    # 'write a fibonacci function in Python and then a fizzbuzz',
    'write a bubble sort function in javascript',
    'create a short todo app using kotlin',
    # 'write a semgrep rule that finds the string x_or_y'
]

for question in questions:
    print(conversation.predict(input=question))
