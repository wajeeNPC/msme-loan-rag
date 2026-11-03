import json
from pathlib import Path
from pydantic import BaseModel ,Field

TEST_FILE = str(Path(__file__).parent / "tests.jsonl")

class Source(BaseModel):
    file : str = Field(description="file name that belongs to")
    page : int = Field(description="page number of the file it belongs to")

class TestQuestion(BaseModel):
    """A text question with expected keywords , citations and reference answer"""
    id: str = Field(description="The question number")
    question: str = Field(description="The question to ask RAG system")
    reference_answer : str = Field(description="The reference answer for this question")
    category : str = Field(description="Question category (e.g., loan_limits , eligibilty )")
    keywords : list[str] = Field(description="")
    expected_sources : list[Source] = Field(description="Which file this source should belong to")
    type : str = Field(description="wether the rag can answer the question")

def load_tests() -> list[TestQuestion]:
    tests = []
    with open (TEST_FILE , "r" , encoding="utf-8") as f : 
        for line in f :
            data = json.loads(line.strip())
            tests.append(TestQuestion(**data))
    return tests
