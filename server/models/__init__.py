import os

from langchain import PromptTemplate


VICUNA_TEMPLATE = """A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.

Current conversation:
{history}
Human: {input}
AI:"""


VICUNA_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=VICUNA_TEMPLATE
)

STABLE_VICUNA_TEMPLATE = """
{history}
### Human: {input}
### Assistant:
"""

STABLE_VICUNA_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=STABLE_VICUNA_TEMPLATE
)


OPEN_ASSISTANT_TEMPLATE = """
{history}
<|prompter|> {input}
<|assistant|>:
"""

OPEN_ASSISTANT_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=OPEN_ASSISTANT_TEMPLATE
)



STARCHAT_TEMPLATE = """
<|system|> Below is a conversation between a human user and a helpful AI coding assistant. <|end|>
{history}
<|user|> {input} <|end|>
<|assistant|>
"""

STARCHAT_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=STARCHAT_TEMPLATE
)






ALPACA_TEMPLATE = """
{history}
### Instruction:
{input}
### Response:
"""

ALPACA_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=ALPACA_TEMPLATE
)


WIZARD_TEMPLATE = """
{history}
### Instruction:
{input}
### Response:
"""


WIZARD_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=WIZARD_TEMPLATE
)






CODE_TEMPLATE = """
You are an expert programmer.

You generate correct code.

You generate complete code.

You comment your code. 

Current conversation:
{history}
### Instruction:
{input}
### Response:
"""


CODE_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=CODE_TEMPLATE
)


MODELS = {  # Prompt, Stop, Context
    'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'Wizard-Vicuna-13B-Uncensored.ggml.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'WizardLM-30B-Uncensored.ggmlv3.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'wizardlm-30b.ggmlv3.q5_K_S': [WIZARD_PROMPT, None, 2048, 'llama'],
    'guanaco-65B.ggmlv3.q4_0': [ALPACA_PROMPT, None, 2048, 'llama'],
    'WizardCoder-15B-1.0.ggmlv3.q5_1': [ALPACA_PROMPT, None, 8092, 'starcoder'],
}

SELECTED_MODEL = 'Wizard-Vicuna-13B-Uncensored.ggml.q5_0'
MODEL_PATH = os.environ.get("MODEL_PATH", '/Users/christianwengert/Downloads/')
