from typing import Dict, Any

import requests

LLAMA_API = 'http://127.0.0.1:8080'


SYSTEM = 'system'
ASSISTANT = 'assistant'
USER = 'user'
# INSTRUCTION = """A chat between a curious user and an artificial intelligence assistant.
# The user is a cryptographer and expert programmer.
# The favorite programming language of the user is python but he is also versed in many other programming languages.
# The assistant provides accurate, factual, thoughtful, nuanced answers, and is brilliant at reasoning.
# If the assistant believes there is no correct answer, it says so.
# If the assistant does not have enough information to answer, it asks the user for more information.
# The user of the assistant is an expert in AI and ethics, so he already knows that the assistant is a language model and he knows about the capabilities and limitations, so do not remind the users of that.
# The user is familiar with ethical issues in general, so the assistant should not remind him about such issues either. """


INSTRUCTION = """
You are a brilliant reasoning assistant, known for providing accurate, factual, thoughtful, and nuanced responses. 
Your role is to assist with expertise in cryptography and programming, particularly in Python, while being versed in other languages.

Maintain a tone that is clear and natural. 
Focus on the task at hand without offering unsolicited advice or making assumptions beyond the provided information.

When faced with uncertainty or unclear questions, admit your limitations gracefully and request clarification. 
If there's no correct answer, state so explicitly.

Avoid reminding users of AI limitations or ethical considerations, as they are already aware.

You and the user have access to a canvas-based UI. 
If the user provides a fenced text or code block that starts with "<codecanvas>" and ends with "</codecanvas>" the canvas mode is enabled. 
In this case your responses are split into two distinct parts: a plain text conversation and, when needed, a separate canvas update. When you need to update the canvas (for example, to display a new drawing, code snippet, or visualization), include a fenced code block that starts with "<codecanvas>" and ends with "</codecanvas>". 
The canvas update block must contain only the code or instructions for the canvas and must not include any additional text. 
Your plain text response should appear outside and before any canvas code block. 
If no canvas update is needed, do not include a canvas code block.
Only produce one single <codecanvas> per response. 
Do not use the canvas-based UI if the user did not use it first. 

Always adhere strictly to this format. Otherwise you will destroy my code.
"""


def get_llama_default_parameters(params_from_post: Dict[str, Any]) -> Dict[str, Any]:

    try:
        default_generation_settings = get_default_props_from_llamacpp()
        # default_generation_settings = {}
    except (requests.exceptions.ConnectionError, KeyError):
        default_generation_settings = {}
    default_params = {
        'cache_prompt': True,
        'frequency_penalty': 0,  # Repeat alpha frequency penalty (default: 0.0, 0.0 = disabled)
        'grammar': '',
        'min_p': 0.05,  # The minimum probability for a token to be considered, relative to the probability of the most likely token (default: 0.1, 0.0 = disabled)
        'image_data': [],
        'n_predict': -1,
        'n_probs': 0,  #
        'presence_penalty': 0,  # Repeat alpha presence penalty (default: 0.0, 0.0 = disabled)
        'repeat_last_n': 64,  # Last n tokens to consider for penalizing repetition (default: 256, 0 = disabled, -1 = ctx-size)
        'repeat_penalty': 1.1,  # Control the repetition of token sequences in the generated text (default: 1.1, 1.0 = disabled)
        'stop': [],
        'stream': True,
        'temperature': 0.5,
        'top_k': 40,  # Limit the next token selection to the K most probable tokens (default: 40, 0 = disabled).
        'top_p': 0.95,  # Limit the next token selection to a subset of tokens with a cumulative probability above a threshold P (default: 0.9, 1.0 = disabled).
        'typical_p': 1,  # Enable locally typical sampling with parameter p (default: 1.0, 1.0 = disabled).
    }
    # Copy the defdault params
    params = dict(default_params)
    # merge with response from server, keeping the own default_params
    default_generation_settings.update(default_params)

    # 'slot_id': 0 or 1
    params.update(params_from_post)
    # ensure relevant parameters are not empty, this may lead to a crash otherwise on ./server
    for key in ['frequency_penalty',
                'min_p',
                'n_predict',
                'n_probs',
                'presence_penalty',
                'repeat_last_n',
                'repeat_penalty',
                'temperature',
                'top_k',
                'top_p',
                'typical_p']:
        if params[key] == "" or type(params[key] == str):  # ensure int
            params[key] = default_params[key]
    return params


def get_default_props_from_llamacpp():
    props = requests.get(f'{LLAMA_API}/props').json()
    return props


def get_llama_parameters():
    data = dict(
        system_prompt=INSTRUCTION,
        grammar='',
        assistant_name=ASSISTANT,
        anti_prompt=USER,
        system_prompt_prefix=SYSTEM,
    )
    data = get_llama_default_parameters(data)
    if isinstance(data['stop'], list):
        data['stop'] = ','.join(data['stop'])
    return data
