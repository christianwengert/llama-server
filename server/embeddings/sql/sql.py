import os
from langchain import SQLDatabase, LlamaCpp, SQLDatabaseChain
from models import MODEL_PATH, MODELS

MODEL = 'stable-vicuna-13B.ggml.q5_0'


def qa_on_sql(connect_string: str, model: str):

    prompt, stop, n_ctx = MODELS[model]

    db = SQLDatabase.from_uri(connect_string,
                              engine_args=dict(connect_args={"check_same_thread": False}, echo=True),
                              # include_tables=['employees']
                              )

    llm = LlamaCpp(model_path=os.path.join(MODEL_PATH, MODEL),
                   temperature=0.8,
                   n_threads=8,
                   n_ctx=n_ctx,
                   n_batch=512,
                   max_tokens=256,
                   )

    db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

    answer = db_chain.run("How many employees are there?")

    print(answer)


if __name__ == '__main__':
    qa_on_sql("sqlite:////Users/christianwengert/src/llama-server/chinook.db", MODEL)