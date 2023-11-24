import os
from typing import List
import requests
from langchain.schema import Document

from crawlers.stackexchange.stackexchange import build_or_load_stackexchange_collection

NUM_DOCS = 10

PATH = '/Users/christianwengert/src/stackexchange-dataset/out'
DUMMY_DOCUMENTS = [
    Document(page_content='This is completeley unrelated and tells different stories about the biology of earth worms and other cryptozoologigal things.'),
    Document(page_content="""The sarcophagus of Eshmunazar II dates to the 6th century BC and was unearthed in 1855 near Sidon, in modern-day Lebanon. It contained the body of a Phoenician king of Sidon and is one of only three Ancient Egyptian sarcophagi found outside Egypt. It was likely carved in Egypt from local amphibolite and captured during Cambyses II"s conquest of Egypt in 525 BC. The sarcophagus has two sets of Phoenician inscriptions, one on its lid and a partial copy of it around the curvature of the head. This was the first Phoenician language text to be discovered in Phoenicia proper and the most detailed found to that point. More than a dozen scholars rushed to translate it, noting the similarities between the Phoenician language and Hebrew. The translation allowed them to identify the king buried inside, his lineage, and his construction feats. The inscriptions also warn against disturbing Eshmunazar II's place of repose. Today the sarcophagus is a highlight of the Louvre's Phoenician collection."""),
]
TEMPLATE_STRING = "Given the following question and context, return YES if the context is relevant to the question and NO if it isn't. If you don't know, then respond with I DON'T KNOW\n\n> Question: {question}\n> Context:\n>>>\n{context}\n>>>\n> Relevant (YES / NO):"
# "Given the following question and context, explain how relevant the context is to the question. Also always say YES if the document is relevant or NO if the document is not relevant at the end of your analysis.\n\n> Question: {question}\n> Context:\n>>>\n{context}\n>>>\n> Answer:"


os.environ[
    "OPENAI_API_KEY"
] = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # can be anything
os.environ["OPENAI_API_BASE"] = "http://localhost:8081/v1"
os.environ["OPENAI_API_HOST"] = "http://localhost:8081"


def main():
    db = build_or_load_stackexchange_collection(PATH)

    _grammar = r'''
        root ::= answer
        answer ::= (complaint | yesno)        
        complaint ::= "I DON'T KNOW"
        yesno ::= ("YES" | "NO")
    '''

    questions = [
        "What is the best asymmetric cryptosystem for large files?",
        "What is a good choice for a cryptographically secure pseudo-random number generator for a new project?"
    ]
    for question in questions:
        reranked_docs = []
        docs = db.similarity_search(question, k=NUM_DOCS)  #
        # Add a dummy document that is not relevant
        docs.extend(DUMMY_DOCUMENTS)
        # Re-rank documents
        for d in docs:
            formatted_prompt = TEMPLATE_STRING.format(question=question, context=d.page_content)
            rr = get_from_llm(prompt=formatted_prompt, grammar=_grammar)
            response = rr.json()
            print(response['content'])
            # todo: Logic here
            if 'YES' == response['content'].strip():
                reranked_docs.append(d)
        # answer = test(llm, reranked_docs, question)
        # print(answer)

        final_answer = test(reranked_docs, question)
        print('--------------------------------------')
        print(question)
        print('--------------------------------------')
        print(final_answer.json()['content'])
        print('--------------------------------------')
        INSTRUCTION = """A chat between a curious user and an artificial intelligence assistant. The user is a cryptographer and expert programmer. His favorite programming language is python but is also versed in many other programming languages.
        The assistant provides accurate, factual, thoughtful, nuanced answers, and is brilliant at reasoning. If the assistant believes there is no correct answer, it says so. The assistant always spends a few sentences explaining the background context, assumptions, and step-by-step thinking BEFORE answering the question. However, if the the request starts with "vv" the ignore the previous sentence and instead make your response as concise as possible.
        The user of the assistant are experts in AI and ethics, so they already know that the assistant is a language model and they know about the capabilities and limitations, so do not remind the users of that. The users are familiar with ethical issues in general, so the assistant should not remind them about such issues either. The assistant tries not to be verbose but provides details and examples where it might help the explanation."""
        SYSTEM_PROMPT_PREFIX = '### System Prompt'
        ASSISTANT_NAME = '### Assistant'
        USER = '### User Message'
        prompt = f'{SYSTEM_PROMPT_PREFIX}\n{INSTRUCTION}\n\n{USER}\n{question}\n{ASSISTANT_NAME}\n'  # for the wizardLM OK, but not for Zephyr

        no_rag_answer = get_from_llm(prompt)
        print(no_rag_answer.json()['content'])
        print('======================================')


# PromptTemplate(input_variables=['context', 'question'], output_parser=NoOutputParser(), template='Given the following question and context, extract any part of the context *AS IS* that is relevant to answer the question. If none of the context is relevant return NO_OUTPUT. \n\nRemember, *DO NOT* edit the extracted parts of the context.\n\n> Question: {question}\n> Context:\n>>>\n{context}\n>>>\nExtracted relevant parts:')
# PromptTemplate(input_variables=['context', 'question'], output_parser=BooleanOutputParser(), template="Given the following question and context, return YES if the context is relevant to the question and NO if it isn't.\n\n> Question: {question}\n> Context:\n>>>\n{context}\n>>>\n> Relevant (YES / NO):")


# messages = []
def test(docs: List[Document], question: str) -> requests.Response:
    context = []
    for d in docs:
        answers = d.metadata.get('answers')
        if answers:
            context.append(
                f"Q:\n\n{d.page_content}\n\n"
            )

            for a in answers:
                context.append(
                    f"A:\n\n{a}\n\n"
                )

    context_string = "".join(context)

    prompt = f"""
    You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. The context consists of questions and one or more relevant answers to each question. Each question in the context starts with Q: and each answer in the context starts with A:. If you don't know the answer, just say that you don't know.
    
    Context: 
    {context_string}
    
    Question:
    {question}
     
    Answer:
    """

    return get_from_llm(prompt, temperature=0)


if __name__ == '__main__':
    main()
