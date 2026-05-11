from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from plagiarism_service import (get_results, check_plagiarism_with_progress, check_semantic_with_progress)
from database import get_all_documents
import json
from fastapi.responses import StreamingResponse

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
    ngram_n: int = 2
    mode: str = "plagiarism"

@app.post("/check")
def check_text(request: CheckRequest):
    database_texts, filenames = get_all_documents()

    result = get_results(
        database_texts,
        filenames,
        request.text,
        request.ngram_n
    )

    return result

@app.post("/check-progress")
def check_text_progress(request: CheckRequest):
    database_texts, filenames = get_all_documents()

    def generate():
        if request.mode == "plagiarism":
            generator = check_plagiarism_with_progress(
                database_texts,
                filenames,
                request.text,
                request.ngram_n
            )

        elif request.mode == "semantic":
            generator = check_semantic_with_progress(
                database_texts,
                filenames,
                request.text
            )

        else:
            generator = iter([
                {
                    "type": "error",
                    "message": "Невідомий режим перевірки"
                }
            ])

        for item in generator:
            yield json.dumps(item, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")