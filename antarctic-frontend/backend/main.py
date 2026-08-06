import os
import time
import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_ID = os.environ.get("ANTHROPIC_MODEL", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-west-2")

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

LEGISLATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "scripts",
    "Australian-Federal-Police-Act-Australia-1979.pdf",
)


def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def get_legislation_text() -> str:
    path = os.path.normpath(LEGISLATION_PATH)
    if not os.path.exists(path):
        raise HTTPException(500, f"Legislation PDF not found at {path}")
    with open(path, "rb") as f:
        return extract_pdf_text(f.read())


def call_bedrock(prompt: str, max_tokens: int = 4096) -> dict:
    response = bedrock.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.7},
    )
    output_msg = response.get("output", {}).get("message", {})
    text_parts = [
        block["text"]
        for block in output_msg.get("content", [])
        if "text" in block
    ]
    usage = response.get("usage", {})
    return {
        "text": "\n".join(text_parts),
        "model": MODEL_ID,
        "input_tokens": usage.get("inputTokens", 0),
        "output_tokens": usage.get("outputTokens", 0),
    }


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")

    file_bytes = await file.read()
    movie_text = extract_pdf_text(file_bytes)

    if not movie_text.strip():
        raise HTTPException(400, "Could not extract text from the PDF.")

    legislation_text = get_legislation_text()

    prompt = f"""I will provide 2 pieces of text - the legislation for the AFP and the script of a movie.
----------
Legislation:
{legislation_text}
----------
Movie script:
{movie_text}
----------
First, provide a TLDR section (2-3 sentences) summarising the main compliance issues found in the movie script.

Then provide the full analysis:
- Suggestions for how the characters could have acted differently to align better with the AFP legislation
- Specific examples from the movie script and the legislation
- Give each character a score out of 10 as to how well they complied with the AFP legislation
"""

    try:
        start = time.time()
        print(f"[ANALYZE] Request received — calling Bedrock at {time.strftime('%H:%M:%S')}")
        result = call_bedrock(prompt)
        elapsed = time.time() - start
        print(f"[ANALYZE] Bedrock responded in {elapsed:.1f}s")
    except Exception as exc:
        elapsed = time.time() - start
        print(f"[ANALYZE] Bedrock FAILED after {elapsed:.1f}s — {exc}")
        raise HTTPException(502, f"LLM call failed: {exc}")

    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "region": REGION}
