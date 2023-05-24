from langchain import HuggingFacePipeline, LLMChain, PromptTemplate

llm = HuggingFacePipeline.from_model_id(model_id="databricks/dolly-v2-7b",
                                        task="text-generation",
                                        model_kwargs={"load_in_8bit": True,
                                                      'device_map': 'auto',
                                                      "temperature": 0, "max_length": 5000})
# {'load_in_8bit': True}
# chain = LLMChain(llm=llm, prompt=PROMPT, output_key="nda_1")


template = """Question: {question}

Answer: Let's think step by step."""
prompt = PromptTemplate(template=template, input_variables=["question"])

llm_chain = LLMChain(prompt=prompt, llm=llm)
question = "What is electroencephalography?"
answer = llm_chain.run(question)
print(answer)