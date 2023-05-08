from langchain import PromptTemplate


GPT4ALL_TEMPLATE = """
{history}
Question: {input}

Answer: Let's think step by step."""

GPT4ALL_PROMPT = PromptTemplate(template=GPT4ALL_TEMPLATE, input_variables=["input", "history"])
