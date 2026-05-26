from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from plagiarism_service import (get_results, check_plagiarism_with_progress, check_semantic_with_progress)
from database import get_all_documents
import json
from fastapi.responses import StreamingResponse

from fastapi import UploadFile, File, Form
import os
from PyPDF2 import PdfReader
from docx import Document
from odf.opendocument import load
from odf.text import P

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

def extract_text_from_file(file: UploadFile):
    filename = file.filename.lower()
    temp_path = f"temp_{file.filename}"

    with open(temp_path, "wb") as buffer:
        buffer.write(file.file.read())

    text = ""

    try:
        if filename.endswith(".pdf"):
            reader = PdfReader(temp_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        elif filename.endswith(".docx"):
            doc = Document(temp_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

        elif filename.endswith(".odt"):
            doc = load(temp_path)
            paragraphs = doc.getElementsByType(P)
            text = "\n".join([
                "".join(node.data for node in paragraph.childNodes if hasattr(node, "data"))
                for paragraph in paragraphs
            ])

        else:
            raise ValueError("Непідтримуваний формат файлу")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return text.strip()

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

@app.post("/check-file-progress")
def check_file_progress(
    file: UploadFile = File(...),
    ngram_n: int = Form(2),
    mode: str = Form("plagiarism")
):
    input_text = extract_text_from_file(file)

    if not input_text:
        def empty_generate():
            yield json.dumps({
                "type": "error",
                "message": "Не вдалося витягнути текст з файлу"
            }, ensure_ascii=False) + "\n"

        return StreamingResponse(empty_generate(), media_type="application/x-ndjson")

    database_texts, filenames = get_all_documents()

    def generate():
        if mode == "plagiarism":
            generator = check_plagiarism_with_progress(
                database_texts,
                filenames,
                input_text,
                ngram_n
            )

        elif mode == "semantic":
            generator = check_semantic_with_progress(
                database_texts,
                filenames,
                input_text
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