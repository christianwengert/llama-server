import secrets
from flask import Flask, render_template, request, session, abort
# from flask_session import Session
from langchain import LlamaCpp, ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate


app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
# app.config["SESSION_PERMANENT"] = True
# app.config["SESSION_COOKIE_SECURE"] = True
# app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 30  # 30'
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)

ais = {}


def create_conversation() -> ConversationChain:
    llm = LlamaCpp(model_path="/Users/christianwengert/src/llama/alpaca.cpp-webui/bin/vicuna.ggml.bin",
                   temperature=0.8, n_threads=4,
                   n_ctx=2048,
                   n_batch=512,
                   max_tokens=256,
                   )
    # llm_chain = LLMChain(prompt=prompt, llm=llm)
    # todo
    template = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions."
    system_message_prompt = SystemMessagePromptTemplate.from_template(template)
    human_template = "{text}"
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    return ConversationChain(
        llm=llm,
        # prompt=chat_prompt,
        verbose=True,
        memory=ConversationBufferMemory()
    )


@app.route("/")
def hello_world():
    token = session.get('llm', None)
    if token is None:
        token = secrets.token_hex(32)
        session['llm'] = token
        ais[token] = create_conversation()

    return render_template('index.html')


@app.route('/', methods=["POST"])
def get_input():
    token = session.get('llm', None)
    conversation = ais.get(token, None)
    if not conversation:
        abort(400)
    binary = request.data
    text = binary.decode('utf8')
    answer = conversation.predict(input=text)
    return answer.encode()


if __name__ == '__main__':
    app.run()
