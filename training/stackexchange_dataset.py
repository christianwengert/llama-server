import glob
import json
import os

DATADIR = '/Users/christianwengert/src/stackexchange-dataset/out/'

# Uses the output of pairer.py of https://github.com/EleutherAI/stackexchange-dataset
exchanges = [
    'crypto.stackexchange',
    'security.stackexchange'
]


dataset = []


for exchange in exchanges:
    directory = os.path.join(DATADIR, exchange)
    txt_files = glob.glob(os.path.join(directory, '*.txt'))
    for file in txt_files:
        with open(file, 'r') as f:
            content = f.read()
            start = content.find('Q:\n\nI')
            first_answer = content.find('A:\n\n')

            question = content[start+4:first_answer].strip()
            answers = []
            while True:
                next_answer = content.find('A:\n\n', first_answer + 1)
                answer = content[first_answer+4:next_answer].strip()
                answers.append(answer)
                if next_answer == -1:
                    break
                first_answer = next_answer
            dataset.append({
                'question': question,
                'answers': answers
            })
    print(2)
    with open(f'{exchange}.json', 'w') as f:
        json.dump(dict(train=dataset), f)

    # Now transform alpaca style
    #     {
    #         "instruction": "Give three tips for staying healthy.",
    #         "input": "",
    #         "output": "1. Eat a balanced diet and make sure to include plenty of fruits and vegetables. \n2. Exercise regularly to keep your body active and strong. \n3. Get enough sleep and maintain a consistent sleep schedule."
    #     },
    # Using alpaca_short template
    # alpaca_short = {
    #     "description": "A shorter template to experiment with.",
    #     "prompt_input": "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n",
    #     "prompt_no_input": "### Instruction:\n{instruction}\n\n### Response:\n",
    #     "response_split": "### Response:"
    # }

    alpaca_dataset = []
    for qa_pair in dataset:

        for answer in qa_pair['answers']:
            alpaca_dataset.append({
                'instruction': "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n".format(instruction=qa_pair['question'], input=''),
                'input': '',
                'output': answer
            })

    with open(f'{exchange}-alpaca-instruct.json', 'w') as f:
        s = json.dumps(alpaca_dataset)
        f.write(s)

#
# import datasets
#
# datasets.load_dataset(f'{exchange}-alpaca-instruct.json')
# datasets.utils.
#
#
#
#
# template = """{
#     "description": "Template used by Alpaca-LoRA.",
#     "prompt_input": "Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.\n\n### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n",
#     "prompt_no_input": "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction:\n{instruction}\n\n### Response:\n",
#     "response_split": "### Response:"
# }
# """
# json.loads('{}')