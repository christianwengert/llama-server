# Installation

- Checkout or download zip.
- `python3 -m venv env`
- `. env/bin/activate`
- `pip install -r requirements.txt`
- on the special system, langchain does not build correctly-> Download the wheel from the release page on https://github.com/hwchase17/langchain/releases
  - `pip install langchain-xxx.whl`
- idem for llama-cpp-python at https://github.com/abetlen/llama-cpp-python
  - ~~`pip install llama-cpp-python-xxx.whl`~~
  - `python setup develop`
- `pip install -r requirements.txt`
- `export MODEL_PATH=<path>`
- in the directory: 
  - `PYTHONPATH=<path>/server python3 server/app.py` 

## Build Javascript from typescript
```
npm install
npm run build
npm run build_mini
```





CMAKE_ARGS="-DLLAMA_METAL=on -DBUILD_SHARED_LIBS=on" FORCE_CMAKE=1 python setup.py develop

transformers:  pip install -e .
