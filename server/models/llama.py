import queue
import threading
import time
from typing import Callable, Any

from ctransformers.langchain import CTransformers
from langchain import ConversationChain, BasePromptTemplate
from langchain.memory import ConversationTokenBufferMemory

from models.interruptable_llama import InterruptableLlamaCpp


def streaming_answer_generator(fun: Callable[[str], None], q: queue.Queue, text_input: Any):
    """
    This takes every token and streams it back to the browser
    """
    thread = threading.Thread(target=fun, args=(text_input,))
    thread.start()

    compounded_answer = ""
    while True:
        # wait for an item from the queue
        try:
            item = q.get()  # type: str
        except IndexError:
            time.sleep(0.01)
            continue
        compounded_answer += item
        if compounded_answer.startswith(" "):  # Hack to get rid off the first space
            item = item.lstrip()
            compounded_answer = compounded_answer.lstrip()

        if item == "THIS IS THE END%^&*":
            break
        print(item, end="")
        yield item.encode()
    thread.join()


def create_conversation(model_path: str,
                        prompt: BasePromptTemplate,
                        stop=None,
                        n_ctx=4096,
                        max_token=1024,
                        temperature=0.5,
                        n_threads=8
                        ) -> ConversationChain:

    extra_args = {}
    import platform
    if 'arm64' in platform.platform() and 'macOS' in platform.platform():
        extra_args['n_gpu_layers'] = 1
        print('Using METAL')
        # n_ctx = 8192
        # extra_args['rope_freq_base'] = 57200
        # extra_args['rope_freq_scale'] = 0.25

    llm = InterruptableLlamaCpp(model_path=model_path,
                                temperature=temperature,
                                n_threads=n_threads,
                                n_ctx=n_ctx,
                                n_batch=512,
                                max_tokens=max_token,
                                **extra_args
                                )

    # llm.client.params.rope_freq_base = 57200
    # llm.client.params.rope_freq_scale = 0.25
    # llm.client._n_ctx = 8192

    if stop is not None:
        llm.stop = stop

    conversation_chain = ConversationChain(
        llm=llm,
        verbose=True,
        memory=ConversationTokenBufferMemory(llm=llm, max_token_limit=n_ctx - 1200),  # this one is limited
    )
    conversation_chain.prompt = prompt
    return conversation_chain
