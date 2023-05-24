from langchain import HuggingFacePipeline, LLMChain, PromptTemplate

# bigcode/santacoder
llm = HuggingFacePipeline.from_model_id(model_id="HuggingFaceH4/starchat-alpha",
                                        task="text-generation",
                                        device=-1,
                                        # model_kwargs={"temperature": 0, "max_new_tokens": 5000}
                                        )



template = """Question: {question}

Answer: Let's think step by step."""
prompt = PromptTemplate(template=template, input_variables=["question"])

llm_chain = LLMChain(prompt=prompt, llm=llm)
question = "What is electroencephalography?"
print(llm_chain.run(question))

from transformers import AutoModelForCausalLM, AutoTokenizer

checkpoint = "bigcode/starcoderbase"
device = "cuda" # for GPU usage or "cpu" for CPU usage

tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForCausalLM.from_pretrained(checkpoint, trust_remote_code=True).to(device)

inputs = tokenizer.encode("def print_hello_world():", return_tensors="pt").to(device)
outputs = model.generate(inputs)
print(tokenizer.decode(outputs[0]))


#
# https://huggingface.co/HuggingFaceH4/starchat-alpha
#
# HuggingFaceH4/starchat-alpha   !!!!
#
# NeoDim/starcoder-GGML
