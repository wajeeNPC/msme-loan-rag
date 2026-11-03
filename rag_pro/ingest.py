import os
import difflib
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
import re
from pydantic import BaseModel , Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion
from tenacity import retry, wait_exponential , stop_after_attempt
from concurrent.futures import ThreadPoolExecutor

from rag_pro.config import DB_NAME, COLLECTION_NAME, CHUNK_MODEL, AVERAGE_CHUNK_SIZE, EMBEDDING_MODEL

load_dotenv(override=True)
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
if openrouter_api_key:
    print(f"OpenRouter API Key exists and begins {openrouter_api_key[:8]}")
else:
    print("OpenRouter API key not set")

PDF_FILENAMES = ["treasury_msme_faq.pdf"  , "re_msme_operating_guideline.pdf"]
SUMMARY_MD = "data/processed/loan_schemes_summary.md"
SUMMARY_PDF = "treasury_msme_loan_schemes_summary.pdf"

wait =wait_exponential(multiplier=1, min=10 , max=240)
WORKERS = 3

openrouter = OpenAI(base_url="https://openrouter.ai/api/v1" , api_key=openrouter_api_key)

FIRST_ROW_ON_PAGE_2 = 8

class Result(BaseModel):
    page_content: str
    metadata: dict


class Chunk(BaseModel):
    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query",
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document):
        metadata = {"source": document["source"], "page" : document["page"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )


class Chunks(BaseModel):
    chunks: list[Chunk]

# The FAQ PDF is a printed web page, so its pages carry the site's menu, footer and the
# browser's print header. The guideline PDF has a "N | P a g e" header on every page.
JUNK_PATTERNS = [
    r"^Home Help Frequently Asked Questions\n",                               # breadcrumb
    r"Ministry of Finance, Planning and Economic\s+Development.*?Public Debt\s+MSME\s+Loan\s+Scheme",  # nav menu
    r"ABOUT US\s+Ministry of Finance.*?Last updated:[^\n]*",                  # site footer (last page)
    r"\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2} [AP]M Ministry of Finance - Sri lanka\s*https://www\.treasury\.gov\.lk/.*?\d+/\d+",  # print header
    r"^\s*\d+ \| P a g e\s*$",                                                # guideline page number
]

def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    for pattern in JUNK_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.MULTILINE)
    text = re.sub(r"_{4,}", "___", text)          # form blanks in the application annexes
    text = re.sub(r"[ \t]+\n", "\n", text)        # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)        # runs of empty lines
    return text.strip()

def load_pdf() -> list[dict]:
    pdf_docs = []

    for filename in PDF_FILENAMES :
        reader = PdfReader(f"data/raw/{filename}")

        for i , page in enumerate(reader.pages):
            text = clean_text(page.extract_text())
            pdf_docs.append({"source" : filename , "page" : i  , "text" : text})
    return pdf_docs

def load_summary_by_page() -> list[dict]:
    with open(SUMMARY_MD, encoding="utf-8") as f:
        lines = f.read().splitlines()

    table_start = next(i for i, line in enumerate(lines) if line.startswith("| # |"))
    intro = [line for line in lines[:table_start] if line.strip()]
    table_header = lines[table_start:table_start + 2]   # header row + |---| separator

    rows_by_page = {0: [], 1: []}
    for line in lines[table_start + 2:]:
        match = re.match(r"^\| (\d+) \|", line)
        if match:
            page = 0 if int(match.group(1)) < FIRST_ROW_ON_PAGE_2 else 1
            rows_by_page[page].append(line)

    return [
        {"source": SUMMARY_PDF, "page": page, "text": "\n".join(intro + table_header + rows)}
        for page, rows in rows_by_page.items()
    ]


def make_prompt(page: dict) -> str:
    how_many = (len(page["text"]) // AVERAGE_CHUNK_SIZE) + 1
    return f"""
You split one page of a document into overlapping chunks for a knowledge base.

The documents are official Sri Lankan government and bank publications about loan schemes for
micro, small and medium enterprises (MSMEs). A chatbot will use these chunks to answer business
owners' questions about eligibility, loan amounts, interest rates, repayment and how to apply.

This is page {page["page"] + 1} of {page["source"]}.

Divide the page as you see fit, making sure the entire page is covered across the chunks - don't leave anything out.
This page should probably be split into about {how_many} chunks, but use more or fewer as appropriate,
so that each specific question can be answered from a single chunk.
Use some overlap between neighbouring chunks (about 25%, or about 50 words) so text near a boundary appears in both.

If the page contains a table, keep every table row whole - never cut a row in half - and keep the
column headers with the rows they describe.

For each chunk, provide:
- headline: a few words a user's question would likely match
- summary: a few sentences summarizing what the chunk says
- original_text: the exact text from the page, copied character for character. Do not fix typos,
  reword, reformat or add anything.

Here is the page:

{page["text"]}

Respond with the chunks.
"""
def make_messages(page):
    return [
        {"role": "user", "content": make_prompt(page)},
    ]

def normalize(s: str) -> str:
    return " ".join(s.split())

NUMBER = r"\d+(?:[.,]\d+)*%?"     # 8%, 1,000, 1.0, 6.5.2
MIN_TEXT_FROM_PAGE = 0.95

def check_chunk(chunk_text: str, page_text: str) -> str | None:
    """Why original_text can't be trusted, or None if it's fine.
    Small edits (fixed PDF typos, skipped table rows) are allowed; changed numbers are not."""
    new_numbers = set(re.findall(NUMBER, chunk_text)) - set(re.findall(NUMBER, page_text))
    if new_numbers:
        return f"numbers not on page: {sorted(new_numbers)}"
    matcher = difflib.SequenceMatcher(None, chunk_text, page_text, autojunk=False)
    from_page = sum(block.size for block in matcher.get_matching_blocks()) / max(len(chunk_text), 1)
    if from_page < MIN_TEXT_FROM_PAGE:
        return f"only {from_page:.0%} of text from page"
    return None

@retry(wait=wait, stop=stop_after_attempt(5), reraise=True)
def process_page(page):
    messages = make_messages(page)
    response = completion(model=CHUNK_MODEL, messages=messages, response_format=Chunks)
    reply = response.choices[0].message.content
    page_as_chunks = Chunks.model_validate_json(reply).chunks

    # original_text should come from the page; report chunks where the LLM changed it
    page_text = normalize(page["text"])
    for c in page_as_chunks:
        problem = check_chunk(normalize(c.original_text), page_text)
        if problem:
            print(f"{page['source']} p{page['page'] + 1}: '{c.headline}' - {problem}")

    return [chunk.as_result(page) for chunk in page_as_chunks]

def create_chunks(pages):
    """ Create chunks using a number of workers in parallel. """
    chunks = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for result in tqdm(pool.map(process_page, pages), total=len(pages)):
            chunks.extend(result)
    return chunks

def create_embeddings(chunks):
    chroma = PersistentClient(path=DB_NAME)
    if COLLECTION_NAME in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(COLLECTION_NAME)

    texts = [chunk.page_content for chunk in chunks]
    emb = openrouter.embeddings.create(model=EMBEDDING_MODEL, input=texts).data
    vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(COLLECTION_NAME)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore created with {collection.count()} chunks")


if __name__ == "__main__":
    pages = load_pdf() + load_summary_by_page()
    chunks = create_chunks(pages)
    create_embeddings(chunks)
    print("Ingestion complete")

