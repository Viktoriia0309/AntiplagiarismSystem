from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from plagiarism_service import read_texts_from_folder, get_results

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CheckRequest(BaseModel):
    text: str
    ngram_n: int


@app.post("/check")
def check_text(request: CheckRequest):
    database_texts, filenames = read_texts_from_folder("texts")

    result = get_results(
        database_texts,
        filenames,
        request.text,
        request.ngram_n
    )

    return result