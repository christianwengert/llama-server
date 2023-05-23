import os
from langchain import SQLDatabase, LlamaCpp, SQLDatabaseChain
from sqlalchemy.exc import OperationalError

from models import MODEL_PATH, MODELS

# MODEL = 'Wizard-Vicuna-13B-Uncensored.ggml.q5_0'
MODEL = 'VicUnlocked-30B-LoRA.ggml.q5_0'


def qa_on_sql(connect_string: str, model: str):

    prompt, stop, n_ctx = MODELS[model]

    db = SQLDatabase.from_uri(connect_string,
                              engine_args=dict(connect_args={"check_same_thread": False}, echo=True),
                              include_tables=['employees']
                              )

    llm = LlamaCpp(model_path=os.path.join(MODEL_PATH, f'{model}.bin'),
                   temperature=0.0,
                   n_threads=8,
                   n_ctx=n_ctx,
                   n_batch=512,
                   max_tokens=512,
                   )

    db_chain = SQLDatabaseChain.from_llm(llm, db,
                                         verbose=True,
                                         # use_query_checker=True,
                                         )

    questions = [
        "How many employees are there?",
        # "How many albums by Aerosmith?",
        "What is the average salary?",
        "What countries are the employees from?",
        "who is the general manager?",
        "how many people work in IT?",
        "how many people work in Sales?",
        "who is the youngest employee?",
        # "which band has the most albums?",
    ]
    answers = []
    for question in questions:
        print(question)
        # noinspection PyBroadException
        try:
            answer = db_chain.run(question)
        except ValueError as _e:
            raise _e
        except OperationalError as _e:
            # noinspection PyUnresolvedReferences
            answer = f"Could not answer this question with this query {print(_e.intermediate_steps[-2])}"
        except Exception as _e:
            print(_e)
            answer = "GARGL"

        answers.append(answer)

    for answer, question in zip(answers, questions):
        print('---------------')
        print(question)
        print(answer)
        print('===============')


if __name__ == '__main__':
    qa_on_sql("sqlite:////Users/christianwengert/src/llama-server/chinook.db", MODEL)
