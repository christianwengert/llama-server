from langchain import PromptTemplate


ALPACA_TEMPLATE = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

Current conversation:
{history}
Human: {input}
AI:"""


PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=ALPACA_TEMPLATE
)
