import json
import os.path
import tqdm
from langchain import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import PyMuPDFLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from models import MODEL_PATH, MODELS
from models.interruptable_llama import InterruptableLlamaCpp
from training.pdfdataset import find_pdf_files


def embed_docs():
    # model = "wizardlm-30b.ggmlv3.q4_0"
    model = "guanaco-65B.ggmlv3.q4_0"

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=256,  # int(n_ctx / 4),  # todo this is related to the k top hits from vector store
        chunk_overlap=32,
    )

    prompt, stop, n_ctx, _ = MODELS[model]

    model_path = os.path.join(MODEL_PATH, f'{model}.bin')

    texts = []

    if False:
        with open('/Users/christianwengert/src/llama-server/training/crypto.stackexchange.json') as f:
            dataset = json.load(f)

        for i, d in tqdm.tqdm(enumerate(dataset['train'])):
            question_string = f'Question: {d["question"]}'
            answers_string = [f"Answer: {a}" for a in d['answers']]
            document_string = question_string + '\n' + '\n'.join(answers_string)

            texts.extend(text_splitter.split_text(document_string))
    else:
        files = list(find_pdf_files('/Users/christianwengert/Downloads/iacr'))
        for i, f in tqdm.tqdm(enumerate(files)):
            try:
                loader = PyMuPDFLoader(f)
                pages = loader.load()
                texts.extend(text_splitter.split_documents(pages))
            except Exception as _e:
                print(f'Cannot load {f}')



        # for file in glob.glob(directory + "/" + "**/*.pdf"):
        #     yield file

    print(f"Number of texts: {len(texts)}")

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    # noinspection PyBroadException
    try:
        db = FAISS.load_local('.', embeddings, 'stack-chunksize256')
    except Exception as _e:
        db = FAISS.from_texts(texts, embeddings)
        db.save_local('.', 'stack-chunksize256')
    print('index loaded')

    retriever = db.as_retriever()

    retriever.search_kwargs['k'] = 6
    # retriever.search_kwargs['reduce_k_below_max_tokens'] = True
    # retriever.search_kwargs['max_tokens_limit'] = 1024 + 512

    llm = InterruptableLlamaCpp(model_path=model_path,
                                temperature=0.1,
                                n_threads=8,
                                n_ctx=n_ctx,
                                n_batch=512,
                                max_tokens=512,
                                verbose=True,
                                n_gpu_layers=1
                                )

    chain_type = "stuff"
    return_source_documents = chain_type != 'stuff'
    qa = ConversationalRetrievalChain.from_llm(llm,
                                               retriever=retriever,
                                               chain_type=chain_type,
                                               return_source_documents=return_source_documents,
                                               max_tokens_limit=1024 + 512
                                               )

    questions = [
        'What if LWE is not as secure as we think?',
        'How to determine cryptographic properties of AES S-Box?',
        'Is a naive 27bit FPE algorithm using AES-CTR insecure?',
        'How to find second subgroup for ECC Pairing?',
        'How much would removing enigmas biggest flaw improve it?',
        'Why does "hex encoding of the plaintext before encryption", "harm security"?',
        'what happens if I compress after encryption?',
        'Which is stronger: Threefish 1024-bit, SHACAL-2 512-bit, or AES-256?'
    ]
    chat_history = list()

    for question in questions:
        print(f"-> **Question**: {question} \n")
        result = qa({"question": question, "chat_history": chat_history})
        print(f"**Answer**: {result['answer']} \n")


if __name__ == '__main__':

    embed_docs()
