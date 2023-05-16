from langchain import SQLDatabase, LlamaCpp, SQLDatabaseChain
from langchain.agents.agent_toolkits import SQLDatabaseToolkit

model = "wizard-vicuna-13B.ggml.q5_0.bin"
MODEL_PATH = f"/Users/christianwengert/Downloads/{model}"


db = SQLDatabase.from_uri("sqlite:////Users/christianwengert/src/llama-server/chinook.db", engine_args=dict(connect_args={"check_same_thread": False}, echo=True))
# toolkit = SQLDatabaseToolkit(db=db)


# db._engine.connect()
llm = LlamaCpp(model_path=MODEL_PATH,
               temperature=0.8,
               n_threads=8,
               n_ctx=2048,
               n_batch=512,
               max_tokens=256,
               )

db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

answer = db_chain.run("How many employees are there?")

print(answer)
