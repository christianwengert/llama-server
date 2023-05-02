import queue
from typing import Literal, Callable
from langchain import ConversationChain


def setup_chat_model(model: Literal["vicuna", "oast"]) -> [Callable[[str], None], ConversationChain]:
    if model == "vicuna":
        from models.llama import streaming_answer_generator
        from models.llama import create_conversation

        from models.vicuna import MODEL_PATH, PROMPT

        def wrapper(q: queue.Queue) -> ConversationChain:
            return create_conversation(q, MODEL_PATH, PROMPT)

        return streaming_answer_generator, wrapper

    if model == "oast":
        from models.llama import streaming_answer_generator
        from models.llama import create_conversation

        from models.oast import MODEL_PATH, PROMPT

        def wrapper(q: queue.Queue) -> ConversationChain:
            return create_conversation(q, MODEL_PATH, PROMPT)

        return streaming_answer_generator, wrapper

    raise NameError
