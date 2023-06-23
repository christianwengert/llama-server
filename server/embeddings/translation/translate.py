import os
from typing import Tuple, List

from langchain import LLMChain, PromptTemplate
from langchain.document_loaders import CSVLoader, UnstructuredExcelLoader, PyMuPDFLoader, UnstructuredHTMLLoader, \
    UnstructuredMarkdownLoader, UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from models import MODELS, MODEL_PATH
from models.interruptable_llama import InterruptableLlamaCpp
from streaming import StreamingLlamaHandler


def fun(token: str):
    print(token)


def abortfun():
    return False


def prepare_translation(file_or_path: str, model: str) -> Tuple[LLMChain, List[Document]]:

    prompt, stop, n_ctx, model_type = MODELS[model]

    extra_args = {}
    import platform
    if 'arm64' in platform.platform() and 'macOS' in platform.platform():
        extra_args['n_gpu_layers'] = 1
        print('Using METAL')

    llm = InterruptableLlamaCpp(model_path=os.path.join(MODEL_PATH, f'{model}.bin'),
                                temperature=0.1,
                                n_threads=8,
                                n_ctx=n_ctx,
                                n_batch=512,
                                max_tokens=2048,
                                callbacks=[StreamingLlamaHandler(fun, abortfun)],
                                **extra_args
                                )
    extension = os.path.splitext(file_or_path)[-1]

    if extension == '.pdf':
        loader_class = PyMuPDFLoader
    elif extension == '.xls' or extension == '.xlsx':
        loader_class = UnstructuredExcelLoader
    elif extension == '.csv':
        loader_class = CSVLoader
    elif extension == '.html' or extension == 'htm':
        loader_class = UnstructuredHTMLLoader
    elif extension == '.md':
        loader_class = UnstructuredMarkdownLoader
    else:  # all other formats
        loader_class = UnstructuredFileLoader
    loader = loader_class(file_or_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=0,
    )

    texts = text_splitter.split_documents(documents)

    prompt_template = """
### Instruction:
Translate the following text to english:
{input}
### Response:
"""


    # prompt_template = "Translate the following text to english:\n {input}"
    prompt = PromptTemplate.from_template(prompt_template)
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True

    )

    return llm_chain, texts


if __name__ == '__main__':
    llm_chain, texts = prepare_translation('/Users/christianwengert/Downloads/chinese.txt', 'wizardlm-30b.ggmlv3.q5_K_S')

    answers = ""
    for text in texts:
        answer = llm_chain.predict(input=text.page_content)
        answers += answer
    from pprint import pprint
    pprint(answers)

