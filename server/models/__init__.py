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
### Response:"
"""

ALPACA_PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=ALPACA_TEMPLATE
)

MODELS = {
    'wizard-vicuna-13B.ggml.q5_0': [VICUNA_PROMPT, None],
    'Wizard-Vicuna-13B-Uncensored.ggml.q5_0': [VICUNA_PROMPT, None],
    'stable-vicuna-13B.ggml.q5_0': [STABLE_VICUNA_PROMPT, ["### Human:"]],
    'OpenAssistant-SFT-7-Llama-30B.ggml.q5_0': [OPEN_ASSISTANT_PROMPT, None],
    'gpt4-alpaca-lora_mlp-65B.ggml.q5_0': [ALPACA_PROMPT, None],
    'dromedary-lora-65B.ggml.q5_0': [ALPACA_PROMPT, None],
    'alpaca-lora-65B.ggml.q5_0': [ALPACA_PROMPT, ["Human: "]]
}

SELECTED_MODEL = 'Wizard-Vicuna-13B-Uncensored.ggml.q5_0'
MODEL_PATH = os.environ.get("MODEL_PATH", '/Users/christianwengert/Downloads/')
