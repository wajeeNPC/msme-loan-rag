import os
from dotenv import load_dotenv
from datetime import date
import gradio as gr
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_chroma import Chroma
from langchain_core.documents import Document


from rag.config import DB_NAME, RETRIEVAL_K, ANSWER_MODEL, get_embeddings

MODEL = ANSWER_MODEL
RETRIVEL_K = RETRIEVAL_K

embeddings = get_embeddings()


SYSTEM_PROMPT = """
Today's date is {today}.
Your a AI assistant for Sri lankan MSME (medium small medium enterprice )
Your task is to only answer using the provided document text and if the documents dont cover the question , say i dont know , please check with the bank and never guess (never state a specific banks interest rate)
Always provide a disclaimer : not a financial  advice 
Every factual claim you take must include a citation to the source document and page number , e.g (treasury_msme_faq.pdf, page 3)
The context below is labeled with its source document and page number - use those exact labels when citing.
If a scheme has an end date or deadline, compare it with today's date. If it has already
passed, say the scheme appears to have ended on that date, and tell the user to confirm with
the Department of Development Finance or their bank. Never say an expired scheme is open.

{context}
"""

load_dotenv(override=True)
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
if openrouter_api_key:
    print(f"OpenAI API Key exists and begins {openrouter_api_key[:8]}")
else:
    print("OpenRouter API key not set")

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()
llm = ChatOpenAI(temperature=0, model_name=MODEL , base_url="https://openrouter.ai/api/v1", api_key=openrouter_api_key)

def fetch_context(question : str) -> list[Document]:
    "Retrive relevent context documents for a question"
    return retriever.invoke( question , k=RETRIVEL_K)

def build_context(docs):
    context=""
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")
        if page is not None:
            page += 1
            context += f"[Source: {source}, Page: {page}]\n"
        else:
            context += f"[Source: {source}]\n"
        context += f"{doc.page_content}\n\n"
    return context

def convert_history(history):
    converted = []
    for turn in history:
        if turn["role"] == "user":
            converted.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            converted.append(AIMessage(content=turn["content"]))
    return converted

def answer_question(question: str, history):
    docs = fetch_context(question)
    context = build_context(docs)
    today = date.today().strftime("%d %B %Y")
    system_prompt = SYSTEM_PROMPT.format(context=context , today=today)
    messages = [SystemMessage(content=system_prompt)] + convert_history(history) + [HumanMessage(content=question)]
    response = llm.invoke(messages)
    return response.content , docs

def chat(question : str , history):
    answer , _docs = answer_question(question , history)
    return answer 


if __name__ == "__main__":
    gr.ChatInterface(chat).launch()
