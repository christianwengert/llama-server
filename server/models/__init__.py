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
    # 'wizard-vicuna-13B.ggml.q5_0': [WIZARD_PROMPT, None, 2048],
    # 'wizard-mega-13B.ggml.q5_0': [WIZARD_PROMPT, ["</s>"], 2048],
    'Wizard-Vicuna-13B-Uncensored.ggml.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'WizardLM-30B-Uncensored.ggmlv3.q5_0': [WIZARD_PROMPT, None, 2048, 'llama'],
    'gpt4-alpaca-lora_mlp-65B.ggml.q5_0': [ALPACA_PROMPT, None, 2048, 'llama'],
    'starchat-alpha-ggml-q5_0': [ALPACA_PROMPT, None, 8192, 'starcoder'],
}

SELECTED_MODEL = 'Wizard-Vicuna-13B-Uncensored.ggml.q5_0'
MODEL_PATH = os.environ.get("MODEL_PATH", '/Users/christianwengert/Downloads/')
