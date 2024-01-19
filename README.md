# Installation

- Checkout or download zip.
- `python3 -m venv env`
- `. env/bin/activate`
- `pip install -r requirements.txt`
- in the directory: 
  - `PYTHONPATH=<path>/server python3 server/app.py`
- Independently start the llama.cpp server

## Build Javascript from typescript
```
npm install
npm run build
npm run build_mini
```



# 
# This is how to get rid off langchain
# from sentence_transformers import SentenceTransformer
# EMBEDDINGS = SentenceTransformer('BAAI/bge-large-en-v1.5')
#
# #Our sentences we like to encode
# sentences = ['This framework generates embeddings for each input sentence',
#     'Sentences are passed as a list of string.',
#     'The quick brown fox jumps over the lazy dog.']
#
# #Sentences are encoded by calling model.encode()
# embeddings = model.encode(sentences, normalize_embeddings=True)
# EMBEDDINGS.embed_documents(sentences)
#
# #Print the embeddings
# for sentence, embedding in zip(sentences, embeddings):
#     print("Sentence:", sentence)
#     print("Embedding:", embedding)
#     print("")


CMAKE_ARGS="-DLLAMA_METAL=on -DBUILD_SHARED_LIBS=on" FORCE_CMAKE=1 python setup.py develop

transformers:  pip install -e .
