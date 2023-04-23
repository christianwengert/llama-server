import re
import secrets
from flask import Flask, render_template, request, session, abort
from langchain import LlamaCpp, ConversationChain, BasePromptTemplate, PromptTemplate
from langchain.memory import ConversationBufferMemory


app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
)


MODEL_PATH = "/Users/christianwengert/src/llama/alpaca.cpp-webui/bin/vicuna.ggml.bin"
CONVERSATIONS = {}

# _DEFAULT_TEMPLATE = """The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.
VICUNA_TEMPLATE = """A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.

Current conversation:
{history}
Human: {input}
AI:"""
PROMPT = PromptTemplate(
    input_variables=["history", "input"], template=VICUNA_TEMPLATE
)


class MyConversationChain(ConversationChain):
    prompt: BasePromptTemplate = PROMPT


def create_conversation() -> ConversationChain:
    llm = LlamaCpp(model_path=MODEL_PATH,
                   temperature=0.8,
                   n_threads=8,
                   n_ctx=2048,
                   n_batch=512,
                   max_tokens=256,
                   )
    # template = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions."
    # system_message_prompt = SystemMessagePromptTemplate.from_template(template)
    # human_template = "{text}"
    # human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    # chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    conversation_chain = MyConversationChain(
        llm=llm,
        # prompt=chat_prompt,
        verbose=True,
        memory=ConversationBufferMemory()
    )
    # conversation_chain.prompt = chat_prompt
    return conversation_chain


@app.route("/")
def hello_world():
    token = session.get('llm', None)
    if token is None:
        token = secrets.token_hex(32)
        session['llm'] = token
        CONVERSATIONS[token] = create_conversation()

    return render_template('index.html')


@app.route('/', methods=["POST"])
def get_input():
    token = session.get('llm', None)
    conversation = CONVERSATIONS.get(token, None)
    if not conversation:
        abort(400)
    binary = request.data
    text = binary.decode('utf8')
    answer = conversation.predict(input=text)
    # replace markdown code with html
    html_code_template = r"""
    <div class="code-header">
        <div class="language">\1</div>
        <div class="copy">Copy</div>
    </div>
    <pre><code class="language-\1">\2</code></pre>
    """
    markdown_code_pattern = r'```([a-z]+)?([a-z]*\n[\s\S]*?\n)```'
    answer = re.sub(markdown_code_pattern, html_code_template, answer)

    return answer.encode()


if __name__ == '__main__':
    app.run()
