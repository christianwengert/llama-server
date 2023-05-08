from langchain import PromptTemplate


VICUNA_TEMPLATE = """A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.

Current conversation:
{history}
Human: {input}
AI:"""


PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=VICUNA_TEMPLATE
)
