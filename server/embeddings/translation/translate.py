import os

from langchain import LLMChain, PromptTemplate
from langchain.document_loaders import CSVLoader, UnstructuredExcelLoader, PyMuPDFLoader, UnstructuredHTMLLoader, \
    UnstructuredMarkdownLoader, UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from models import MODELS, MODEL_PATH
from models.interruptable_llama import InterruptableLlamaCpp
from streaming import StreamingLlamaHandler


def fun(token: str):
    print(token)


def abortfun():
    return False

def translate_file(file_or_path: str, model: str):

    prompt, stop, n_ctx, model_type = MODELS[model]
    llm = InterruptableLlamaCpp(model_path=os.path.join(MODEL_PATH, f'{model}.bin'),
                                temperature=0.0,
                                n_threads=8,
                                n_ctx=n_ctx,
                                n_batch=512,
                                max_tokens=512,
                                callbacks=[StreamingLlamaHandler(fun, abortfun)]
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
    prompt_template = "Translate the following text to english:\n {input}"
    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(prompt_template),
        verbose=True

    )

    answers = ""
    for text in texts:
        answer = llm_chain.predict(input=text.page_content)
        answers += prompt_template.format(input=text.page_content) + answer
    return answers



if __name__ == '__main__':
    translate_file('/Users/christianwengert/Downloads/chinese.txt', 'WizardLM-30B-Uncensored.ggmlv3.q5_0')  #