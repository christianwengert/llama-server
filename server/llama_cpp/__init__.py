from typing import Dict, Any


def get_llama_default_parameters(params_from_post: Dict[str, Any]) -> Dict[str, Any]:
    default_params = {
        'cache_prompt': True,
        'frequency_penalty': 0,  # Repeat alpha frequency penalty (default: 0.0, 0.0 = disabled)
        'prompt_template': 'mixtral',
        'grammar': '',
        'min_p': 0.1,  # The minimum probability for a token to be considered, relative to the probability of the most likely token (default: 0.1, 0.0 = disabled)
        'image_data': [],
        'mirostat': 0,  # Enable Mirostat sampling, controlling perplexity during text generation (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0).
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'n_predict': 2048,
        'n_probs': 0,  #
        'presence_penalty': 0,  # Repeat alpha presence penalty (default: 0.0, 0.0 = disabled)
        'repeat_last_n': 256,  # Last n tokens to consider for penalizing repetition (default: 256, 0 = disabled, -1 = ctx-size)
        'repeat_penalty': 1.1,  # Control the repetition of token sequences in the generated text (default: 1.1, 1.0 = disabled)
        'stop': ['</s>', 'Llama:', 'User:', '<|endoftext|>', '<|im_end|>'],
        'stream': True,
        'temperature': 0.7,
        'tfs_z': 1,  # Enable tail free sampling with parameter z (default: 1.0, 1.0 = disabled).
        'top_k': 40,  # Limit the next token selection to the K most probable tokens (default: 40, 0 = disabled).
        'top_p': 0.5,  # Limit the next token selection to a subset of tokens with a cumulative probability above a threshold P (default: 0.9, 1.0 = disabled).
        'typical_p': 1,  # Enable locally typical sampling with parameter p (default: 1.0, 1.0 = disabled).
    }
    params = dict(default_params)
    # 'slot_id': 0 or 1
    params.update(params_from_post)
    # ensure relevant parameters are not empty, this may lead to a crash otherwise on ./server
    for key in ['frequency_penalty',
                'min_p',
                'mirostat',
                'mirostat_tau',
                'mirostat_eta',
                'n_predict',
                'n_probs',
                'presence_penalty',
                'repeat_last_n',
                'repeat_penalty',
                'temperature',
                'tfs_z',
                'top_k',
                'top_p',
                'typical_p']:
        if params[key] == "" or type(params[key] == str):  # ensure int
            params[key] = default_params[key]
    return params
