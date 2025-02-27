# Another local GPT UI

This is a user interface for your browser written in Python with the idea to provide a minimal 
UI for chat with local LLMs using llama.cpp featuring Retrieval Augmented Generation (RAG) and audio input using
whisper.cpp.

The UI offers simple user identification without password authentication. This mainly serves to have
a history with each user.


# Installation

Use Python3.9 for compatibility for PDF extraction

- Checkout or download zip.
- `python3 -m venv env`
- `. env/bin/activate`
- `pip install -r requirements.txt`
- in the directory: 
  - `PYTHONPATH=<path>/server python3 server/app.py`
- Independently start the llama.cpp server
  - `./server -m ~/Downloads/models/dolphin-2.6-mixtral-8x7b.Q6_K.gguf  --threads 8 -ngl 100 -c 32768 --cont-batching --parallel 1 -b 128`
- Independently start the GROBID docker image and expose it
  - `docker run --rm --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.0`

## Build Javascript from typescript
```
npm install
npm run build
npm run build_mini
```

# Todos
- Get rid of langchain
- 


[//]: # (# )

[//]: # (# This is how to get rid off langchain)

[//]: # (# from sentence_transformers import SentenceTransformer)

[//]: # (# EMBEDDINGS = SentenceTransformer&#40;'BAAI/bge-large-en-v1.5'&#41;)

[//]: # (#)

[//]: # (# #Our sentences we like to encode)

[//]: # (# sentences = ['This framework generates embeddings for each input sentence',)

[//]: # (#     'Sentences are passed as a list of string.',)

[//]: # (#     'The quick brown fox jumps over the lazy dog.'])

[//]: # (#)

[//]: # (# #Sentences are encoded by calling model.encode&#40;&#41;)

[//]: # (# embeddings = model.encode&#40;sentences, normalize_embeddings=True&#41;)

[//]: # (# EMBEDDINGS.embed_documents&#40;sentences&#41;)

[//]: # (#)

[//]: # (# #Print the embeddings)

[//]: # (# for sentence, embedding in zip&#40;sentences, embeddings&#41;:)

[//]: # (#     print&#40;"Sentence:", sentence&#41;)

[//]: # (#     print&#40;"Embedding:", embedding&#41;)

[//]: # (#     print&#40;""&#41;)


[//]: # (CMAKE_ARGS="-DLLAMA_METAL=on -DBUILD_SHARED_LIBS=on" FORCE_CMAKE=1 python setup.py develop)

[//]: # (transformers:  pip install -e .)
