import os
from dotenv import load_dotenv
from pypdf import PdfReader
import gradio as gr
from openai import OpenAI

filenames = ["treasury_msme_faq.pdf" , "treasury_msme_loan_schemes_summary.pdf" , "re_msme_operating_guideline.pdf"]

load_dotenv(override=True)
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
if openrouter_api_key:
    print(f"OpenAI API Key exists and begins {openrouter_api_key[:8]}")
else:
    print("OpenRouter API key not set")

MODEL = "openai/gpt-4.1-nano"
openai = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=openrouter_api_key,
)

pages = []

for filename in filenames : 
    reader = PdfReader(f"data/raw/{filename}")

    for i , page in enumerate(reader.pages) :
        text = page.extract_text()
        pages.append({"source" : filename , "page" : i + 1 , "text" : text })


SYSTEM_PROMPT = """
Your a AI assistant for Sri lankan MSME (medium small medium enterprice )
Your task is to only answer using the provided document text and if the documents dont cover the question , say i dont know , please check with the bank and never guess (never state a specific banks interest rate)
Always provide a disclaimer : not a financial  advice 
Every factual claim you take must include a citation to the source document and page number , e.g (treasury_msme_faq.pdf, page 3)
The context below is labeled with its source document and page number - use those exact labels when citing.

{context}
"""

full_context = ""

for dict_page in pages : 
    full_context += f"[ Source :  {dict_page['source']} , Page : {dict_page['page']}]\n"
    full_context += f"{dict_page['text']}\n\n"

system_message = SYSTEM_PROMPT.format(context=full_context)

def answer_question(question: str, history) -> tuple[str, list]:
    """Same shape as rag.answer.answer_question so eval.py can score both.
    Returns an empty docs list: the baseline puts every page in the prompt and retrieves nothing."""
    messages = [{"role" : "system" , "content" : system_message}] + history + [{"role" : "user" , "content" : question}]
    response = openai.chat.completions.create(model=MODEL , messages = messages, temperature=0)
    return response.choices[0].message.content, []

def chat(message, history):
    answer, _docs = answer_question(message, history)
    return answer


if __name__ == "__main__":
    gr.ChatInterface(chat).launch()

