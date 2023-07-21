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


ORCA_TEMPLATE = """
### Current conversation:
{history}

### System:
You are an AI assistant that follows instruction extremely well. Help as much as you can.

### User:
{input}

### Response:"
"""
ORCA_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=ORCA_TEMPLATE
)

LLAMA2_TEMPLATE = """
{history}
System: You are a helpful, respectful and honest assistant. Always answer as helpfully as possible. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.
User: {input}
Assistant:
"""
LLAMA2PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=LLAMA2_TEMPLATE
)


MODELS = {  # Prompt, Stop, Context
    'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'Wizard-Vicuna-13B-Uncensored.ggml.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'WizardCoder-15B-1.0.ggmlv3.q5_1': [STARCHAT_PROMPT, None, 8092, 'starcoder'],
    'WizardLM-30B-Uncensored.ggmlv3.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'wizardlm-30b.ggmlv3.q5_K_S': [WIZARD_PROMPT, None, 2048, 'llama'],
    'vicuna-33b-preview.ggmlv3.q5_K_S': [VICUNA_PROMPT, None, 2048, 'llama'],
    'guanaco-65B.ggmlv3.q4_0': [ALPACA_PROMPT, None, 2048, 'llama'],
    'llama-2-13b.ggmlv3.q5_K_M': [ALPACA_PROMPT, None, 4096, 'llama'],
}

SELECTED_MODEL = 'Wizard-Vicuna-13B-Uncensored.ggml.q5_0'
MODEL_PATH = os.environ.get("MODEL_PATH", '/Users/christianwengert/Downloads/')
