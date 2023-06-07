import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

model_id = "decapoda-research/llama-7b-hf"

# model_id = "bigscience/T0_3B"
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

tokenizer = AutoTokenizer.from_pretrained(model_id)

# model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config) #, device_map={"":0})

model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device=torch.device('cpu'))

a = 2
