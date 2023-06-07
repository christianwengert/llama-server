# Train using QLORA
Using runpod.io so far and using `train-test-01.ipynb` file. This needs a GPU.


# Datasets?




# Inference with Llama.cpp

```./main -m ~/Downloads/llama-7b.ggmlv3.q5_1.bin --lora ~/Downloads/huggy7b-fine-tuned/huggy7b-fine-tuned/ggml-adapter-model.bin --lora-base ~/Downloads/ggml-model-f16.bin --threads 8 -i --interactive-first --instruct  -c 1024 -n 1024 --color  --repeat_penalty 1.0 --reverse-prompt "${USER_NAME}:"  -f prompts/wizardlm.txt --temp 0.5```
