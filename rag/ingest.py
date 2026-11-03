import os
import re
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import DB_NAME, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, get_embeddings

db_name = DB_NAME

pdf_filenames = ["treasury_msme_faq.pdf" , "re_msme_operating_guideline.pdf"]

# The summary PDF's table extracts scrambled, so we index a hand-cleaned markdown copy instead.
# Its chunks are labelled as the original PDF (0-indexed page, like PyPDFLoader) so citations
# and eval matching point at the real document. Table rows 1-7 are on PDF page 1, rows 8-12 on page 2.
SUMMARY_MD = "data/processed/loan_schemes_summary.md"
SUMMARY_PDF = "data/raw/treasury_msme_loan_schemes_summary.pdf"
FIRST_ROW_ON_PAGE_2 = 8


def load_summary_by_page() -> list[Document]:
    with open(SUMMARY_MD, encoding="utf-8") as f:
        lines = f.read().splitlines()

    table_start = next(i for i, line in enumerate(lines) if line.startswith("| # |"))
    intro = [line for line in lines[:table_start] if line.strip()]
    table_header = lines[table_start:table_start + 2]   # header row + |---| separator

    pages = {0: [], 1: []}
    for line in lines[table_start + 2:]:
        match = re.match(r"^\| (\d+) \|", line)
        if match:
            page = 0 if int(match.group(1)) < FIRST_ROW_ON_PAGE_2 else 1
            pages[page].append(line)

    return [
        Document(
            page_content="\n".join(intro + table_header + rows),
            metadata={"source": SUMMARY_PDF, "page": page, "parsed_from": SUMMARY_MD},
        )
        for page, rows in pages.items()
    ]

pdf_docs = []

for filename in pdf_filenames:
    loader  = PyPDFLoader(f"data/raw/{filename}")
    pdf_docs += loader.load()

print(len(pdf_docs))

md_docs = load_summary_by_page()

print(len(md_docs))

text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE , chunk_overlap=CHUNK_OVERLAP)
pdf_chunks = text_splitter.split_documents(pdf_docs)


all_chunks = pdf_chunks + md_docs

print(f"Embedding with {EMBEDDING_MODEL} (chunks {CHUNK_SIZE}/{CHUNK_OVERLAP})")
embeddings = get_embeddings()

if os.path.exists(db_name):
    Chroma(persist_directory=db_name , embedding_function=embeddings).delete_collection()

vectorstore = Chroma.from_documents(documents=all_chunks , embedding=embeddings , persist_directory=db_name)
print(f"Vectorstore created with {vectorstore._collection.count()} documents")

