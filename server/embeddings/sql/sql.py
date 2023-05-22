import os
from langchain import SQLDatabase, LlamaCpp, SQLDatabaseChain
from models import MODEL_PATH, MODELS

MODEL = 'Wizard-Vicuna-7B-Uncensored.ggmlv3.q5_0'


def qa_on_sql(connect_string: str, model: str):

    prompt, stop, n_ctx = MODELS[model]

    db = SQLDatabase.from_uri(connect_string,
                              engine_args=dict(connect_args={"check_same_thread": False}, echo=True),
                              include_tables=['employees', 'albums']
                              )

    llm = LlamaCpp(model_path=os.path.join(MODEL_PATH, f'{model}.bin'),
                   temperature=0.0,
                   n_threads=8,
                   n_ctx=n_ctx,
                   n_batch=512,
                   max_tokens=256,
                   )

    db_chain = SQLDatabaseChain.from_llm(llm, db,
                                         verbose=True,
                                         use_query_checker=True,
                                         )

    answer = db_chain.run("How many employees are there?")
    print(answer)

    answer = db_chain.run("How many albums by Aerosmith?")
    print(answer)

    answer = db_chain.run("What is the average salary?")
    print(answer)



if __name__ == '__main__':
    qa_on_sql("sqlite:////Users/christianwengert/src/llama-server/chinook.db", MODEL)