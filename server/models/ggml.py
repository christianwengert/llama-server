# from ctransformers import AutoModelForCausalLM
from langchain import LLMChain

from models import SELECTED_MODEL, MODEL_PATH, VICUNA_PROMPT
from ctransformers.langchain import CTransformers


model = f'{MODEL_PATH}/{SELECTED_MODEL}.bin'

# llm = AutoModelForCausalLM.from_pretrained(model, model_type='llama')

# print(llm('AI is going to'))




llm = CTransformers(model=model,
                    model_type='llama',
                    config=dict(
                        stream=True,
                        temperature=0.1,
                        batch_size=256,
                        threads=8,
                        context_length=2048
                    )
                    )

# print(llm('AI is going to'))






prompt = VICUNA_PROMPT

llm_chain = LLMChain(prompt=prompt, llm=llm)

print(llm_chain.run(dict(input='What is AI?', history=[])))
