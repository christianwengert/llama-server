import os
from langchain import SQLDatabase, SQLDatabaseChain
from sqlalchemy.exc import OperationalError

from models import MODEL_PATH, MODELS, SELECTED_MODEL
from models.interruptable_llama import InterruptableLlamaCpp


def embed_sql(dbname: str, file_path: str, model: str, run_test: bool = False) -> SQLDatabaseChain:

    prompt, stop, n_ctx = MODELS[model]

    connect_string = f"sqlite:///{file_path}"

    db = SQLDatabase.from_uri(connect_string,
                              engine_args=dict(connect_args={"check_same_thread": False}, echo=True),
                              include_tables=['employees']
                              )

    llm = InterruptableLlamaCpp(model_path=os.path.join(MODEL_PATH, f'{model}.bin'),
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

    class MyChain:
        def __call__(self, question, callbacks):
            try:
                answer = db_chain.run(question, callbacks=callbacks)
            except ValueError as _e:
                raise _e
            except OperationalError as _e:
                # noinspection PyUnresolvedReferences
                answer = f"Could not answer this question with this query {_e.intermediate_steps[-2]}"
            except Exception as _e:
                print(_e)
                answer = f"Something went wrong: {str(_e)}"
            return answer

    mychain = MyChain()

    if run_test:
        questions = [
            "How many employees are there?",
            # "How many albums by Aerosmith?",
            "What is the average salary?",
            "What countries are the employees from?",
            "who is the general manager?",
            "how many people work in IT?",
            "how many people work in Sales?",
            "who is the youngest employee?",
            "what is the average age of all employees?",
            "how many people report to michael?",
            "who does michael report to?",
            "who does Margaret report to?",
            "when has steve been hired?",

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
                answer = f"Could not answer this question with this query {_e.intermediate_steps[-2]}"
            except Exception as _e:
                print(_e)
                answer = f"Something went wrong: {str(_e)}"

            answers.append(answer)

        for answer, question in zip(answers, questions):
            print('---------------')
            print(question)
            print(answer)
            print('===============')
    return mychain


if __name__ == '__main__':
    embed_sql("", "sqlite:////Users/christianwengert/src/llama-server/chinook.db", SELECTED_MODEL, run_test=True)
