import glob
import re
import tqdm
import json
from langchain.document_loaders import PyPDFLoader, PyMuPDFLoader
from langchain.text_splitter import NLTKTextSplitter

DATADIR = '/Users/christianwengert/Downloads/iacr/'


dataset = []


# loader = PyPDFDirectoryLoader(DATADIR)
def find_pdf_files(directory):
    for file in glob.glob(directory + "/" + "**/*.pdf"):
        yield file

def main():
    # Rather use a NLTK Splitter, this seems to produce much better chunks
    text_splitter = NLTKTextSplitter(chunk_size=512)


    files = list(find_pdf_files(DATADIR))

    docs = []
    for file in tqdm.tqdm(files):
        try:
            pages = PyMuPDFLoader(file).load()
        except Exception as _e:
            continue
        docs.extend(pages)


    texts = []
    for doc in tqdm.tqdm(docs):
        # CLEANUP

        # this removes \n in the middle of a sentence
        temp1 = re.sub(r'([a-zA-Z,)])\n([a-zA-Z(])', r'\g<1> \g<2>', doc.page_content)
        # this removes hyphens followed by a \n
        temp2 = re.sub(r'([-)])\n([a-zA-Z(])', r'\g<2>', temp1)

        t = text_splitter.split_text(temp2)

        for _ in t:
            if len(_) < 1024 + 512:  # otherwise just skip?
                texts.append(_)
            else:
                print('Could no load too big')


    dataset = []
    for text in texts:
        dataset.append({"text": text})


    with open('iacr.jsonl', 'w') as f:
        json.dump(dataset, f)

if __name__ == '__main__':
    main()
