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
                        n_ctx=2048,
                        model_type=None) -> ConversationChain:
    # model_type = 'starcoder'
    # model_path =
    if model_type != 'llama':
        llm = CTransformers(
            model='NeoDim/starchat-alpha-GGML',
            model_file=model_path,
            model_type=model_type,
            config=dict(
                stream=True,
                temperature=0.1,
                # batch_size=256,
                threads=8,
                context_length=n_ctx,
                stop='<|end|>',
                max_new_tokens=2048
                # verbose=True
            )
        )
    else:  # use llama.cpp if possible
        extra_args = {}
        import platform
        if 'arm64' in platform.platform() and 'macOS' in platform.platform() and \
           '.q5_0' not in model_path and '.q5_1' not in model_path:
            extra_args['n_gpu_layers'] = 1
            print('Using METAL')

        llm = InterruptableLlamaCpp(model_path=model_path,
                                    temperature=0.8,
                                    n_threads=8,
                                    n_ctx=n_ctx,
                                    n_batch=512,
                                    max_tokens=1024,
                                    **extra_args
                                    )

        if stop is not None:
            llm.stop = stop

    conversation_chain = ConversationChain(
        llm=llm,
        verbose=True,
        memory=ConversationTokenBufferMemory(llm=llm, max_token_limit=n_ctx / 2),  # this one is limited
    )
    conversation_chain.prompt = prompt
    return conversation_chain
