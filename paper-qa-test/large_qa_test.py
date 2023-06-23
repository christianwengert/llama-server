import json
import pickle

import tqdm
from langchain.embeddings import HuggingFaceEmbeddings
from paperqa import Docs

from models import MODEL_PATH
from models.interruptable_llama import InterruptableLlamaCpp
from training.pdfdataset import DATADIR, find_pdf_files

with open('/Users/christianwengert/src/llama-server/training/crypto.stackexchange.json') as f:
    dataset = json.load(f)


MODEL = 'wizardlm-30b.ggmlv3.q4_0'

model_path = f'{MODEL_PATH}{MODEL}.bin'

model = InterruptableLlamaCpp(model_path=model_path,
                              temperature=0.8,
                              n_threads=8,
                              n_ctx=2048,
                              n_batch=512,
                              max_tokens=1024,
                              n_gpu_layers=1
                              )

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# db = FAISS.from_documents(texts, embeddings)
docs = Docs(llm=model,
            embeddings=embeddings,
            max_concurrent=2)

do_iacr = False
if do_iacr:
    files = list(find_pdf_files(DATADIR))
    for d in tqdm.tqdm(files):
        docs.add(d)
else:
    for i, d in tqdm.tqdm(enumerate(dataset['train'])):
        question_string = f'Question: {d["question"]}'
        answers_string =  [f"Answer: {a}" for a in d['answers']]
        document_string = question_string + '\n' + '\n'.join(answers_string)
        with open('chunk', 'w') as f:
            f.write(document_string)
        docs.add('chunk', citation=f'Question {i}', key=str(i))

with open("my_docs.pkl", "wb") as f:
    pickle.dump(docs, f)

questions = [
    'What if LWE is not as secure as we think?',
    'How to determine cryptographic properties of AES S-Box?',
    'Is a naive 27bit FPE algorithm using AES-CTR insecure?',
    'How to find second subgroup for ECC Pairing?',
    'How much would removing enigmas biggest flaw improve it?',
    'Why does "hex encoding of the plaintext before encryption", "harm security"?'
]

answer = docs.query("What manufacturing challenges are unique to bispecific antibodies?")
print(answer.formatted_answer)

# from paperqa.qaprompts import qa_prompt
from langchain.prompts import PromptTemplate

my_qaprompt = PromptTemplate(
    input_variables=["context", "question"],
    template="Answer the question '{question}' "
    "Use the context below if helpful. "
    "You can cite the context using the key "
    "like (Example2012). "
    "If there is insufficient context, say you can't answer that question.\n\n"
    "Context: {context}\n\n")

prompts = Promp(qa=my_qaprompt)
# docs = Docs(prompts=prompts)