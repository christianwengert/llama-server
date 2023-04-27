import queue
import threading
from typing import Callable
from langchain import ConversationChain, LlamaCpp, BasePromptTemplate
from langchain.callbacks import CallbackManager
from langchain.memory import ConversationBufferMemory
from streaming import StreamingLlamaHandler


def streaming_answer_generator(fun: Callable[[str], None], q: queue.Queue, text_input: str):
    """
    This takes every token and streams it back to the browser
    """
    thread = threading.Thread(target=fun, args=(text_input,))
    thread.start()

    compounded_answer = ""
    while True:
        # wait for an item from the queue
        item = q.get()  # type: str
        compounded_answer += item
        if compounded_answer.startswith(" "):  # Hack to get rid off the first space
            item = item.lstrip()
            compounded_answer = compounded_answer.lstrip()

        if item == "THIS IS THE END%^&*":
            break
        print(item, end="")
        yield item.encode()
    thread.join()


def create_conversation(q: queue.Queue, model_path: str, prompt: BasePromptTemplate) -> ConversationChain:
    handler = StreamingLlamaHandler(q)
    llm = LlamaCpp(model_path=model_path,
                   temperature=0.8,
                   n_threads=8,
                   n_ctx=2048,
                   n_batch=512,
                   max_tokens=256,
                   callback_manager=CallbackManager([handler])
                   )

    conversation_chain = ConversationChain(
        llm=llm,
        verbose=True,
        memory=ConversationBufferMemory()
    )
    conversation_chain.prompt = prompt
    return conversation_chain
