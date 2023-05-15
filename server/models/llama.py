import queue
import threading
import time
from typing import Callable
from langchain import ConversationChain, LlamaCpp, BasePromptTemplate
from langchain.memory import ConversationTokenBufferMemory


def streaming_answer_generator(fun: Callable[[str], None], q: queue.Queue, text_input: str):
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


def create_conversation(model_path: str, prompt: BasePromptTemplate, stop=None) -> ConversationChain:

    llm = LlamaCpp(model_path=model_path,
                   temperature=0.8,
                   n_threads=8,
                   n_ctx=2048,
                   n_batch=512,
                   max_tokens=512,
                   )

    if stop is not None:
        llm.stop = stop

    conversation_chain = ConversationChain(
        llm=llm,
        verbose=True,
        memory=ConversationTokenBufferMemory(llm=llm, max_token_limit=llm.n_ctx / 2),  # this one is limited
    )
    conversation_chain.prompt = prompt
    return conversation_chain
