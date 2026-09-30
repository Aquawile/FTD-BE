"""Vectorize incoming raw data from raw-data-strg into embeddings, write to ftd-vectorized-data.

Cloud Function 2nd gen triggered by Cloud Storage OBJECT_FINALIZE events on raw-data-strg.
Uses sentence-transformers/all-MiniLM-L6-v2 for embeddings (384 dimensions).
"""
import json
import os
from google.cloud import storage

print("Starting vectorize-raw-data function module (Cloud Storage trigger)", flush=True)

_OUTPUT_BUCKET = os.environ.get("GCS_OUTPUT_BUCKET", "ftd-vectorized-data")
_EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "100000"))
_CHUNK_SIZE = 2000

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        print("Loading sentence-transformers model...", flush=True)
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(_EMBEDDING_MODEL)
        print("Model loaded successfully", flush=True)
    return _MODEL


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE):
    text = text[:_MAX_TEXT_LENGTH]
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    pos = 0
    while pos < len(text):
        end = pos + chunk_size
        if end < len(text):
            boundary = text.rfind(". ", pos, end)
            if boundary == -1:
                boundary = text.rfind("\n", pos, end)
            if boundary == -1:
                boundary = end
            else:
                boundary += 2 if text[boundary:boundary+2] == ". " else 1
        else:
            boundary = len(text)
        chunks.append(text[pos:boundary])
        pos = boundary
    return [c for c in chunks if c.strip()]


def _map_output_path(source_object: str) -> str:
    parts = source_object.split("/")
    if parts[0] == "SEC":
        if len(parts) > 1 and parts[1] == "10-K":
            prefix = "sec-10k"
        elif parts[1] == "8-K":
            prefix = "sec-8k"
        else:
            prefix = "sec"
        remainder = "/".join(parts[2:])
        output = f"{prefix}/{remainder}"
    elif parts[0] == "gnews":
        output = "/".join(parts)
    elif parts[0] == "prices":
        output = "/".join(parts)
    elif parts[0] == "reddit":
        output = "/".join(parts)
    else:
        output = source_object

    if output.endswith(".htm") or output.endswith(".html"):
        output = output.rsplit(".", 1)[0] + ".json"
    elif output.endswith(".jsonl"):
        output = output.rsplit(".", 1)[0] + ".json"
    elif not output.endswith(".json"):
        output += ".json"

    return output


def _extract_text_from_html(html_content: bytes) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "lxml")
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text(separator=" ", strip=True)


def _extract_json_text(json_obj) -> str:
    if isinstance(json_obj, dict):
        texts = []
        for v in json_obj.values():
            if isinstance(v, str):
                texts.append(v)
            elif isinstance(v, (dict, list)):
                texts.append(_extract_json_text(v))
        return " ".join(texts)
    elif isinstance(json_obj, list):
        return " ".join(_extract_json_text(item) for item in json_obj)
    elif isinstance(json_obj, str):
        return json_obj
    return ""


def process_object(source_bucket: str, source_object: str) -> dict:
    """Process a single GCS object and vectorize it."""
    print(f"Processing: {source_bucket}/{source_object}", flush=True)

    client = storage.Client()
    bucket = client.bucket(source_bucket)
    blob = bucket.blob(source_object)

    content_bytes = blob.download_as_bytes()

    if source_object.endswith((".htm", ".html")):
        text = _extract_text_from_html(content_bytes)
    elif source_object.endswith(".json"):
        data = json.loads(content_bytes.decode("utf-8"))
        text = _extract_json_text(data)
    elif source_object.endswith(".jsonl"):
        lines = content_bytes.decode("utf-8").strip().splitlines()
        parsed = [json.loads(line) for line in lines if line.strip()]
        text = _extract_json_text(parsed)
    else:
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            print(f"Skipping binary file: {source_object}", flush=True)
            return {"status": "skipped", "reason": "binary file"}

    if not text.strip():
        print(f"No text content in: {source_object}", flush=True)
        return {"status": "skipped", "reason": "no text"}

    print(f"Extracted {len(text)} chars from {source_object}", flush=True)

    model = _get_model()
    chunks = _chunk_text(text)
    vectors = model.encode(chunks)

    print(f"Generated {len(chunks)} vectors of dim {len(vectors[0])}", flush=True)

    result = {
        "source_bucket": source_bucket,
        "source_object": source_object,
        "vectorized_at": "2026-09-30T00:00:00Z",
        "model": _EMBEDDING_MODEL,
        "dimension": len(vectors[0]),
        "chunks": [
            {
                "chunk_index": i,
                "text_preview": chunks[i][:200],
                "vector": vectors[i].tolist()
            }
            for i in range(len(chunks))
        ]
    }

    output_path = _map_output_path(source_object)
    bucket_out = client.bucket(_OUTPUT_BUCKET)
    blob_out = bucket_out.blob(output_path)
    blob_out.upload_from_string(json.dumps(result, indent=2), content_type="application/json")
    print(f"Wrote vectorized output to gs://{_OUTPUT_BUCKET}/{output_path}", flush=True)

    return {
        "status": "complete",
        "source_bucket": source_bucket,
        "source_object": source_object,
        "output_path": output_path,
        "num_chunks": len(chunks),
        "dimension": len(vectors[0])
    }


import functions_framework


@functions_framework.cloud_event
def process_gcs_file(cloud_event):
    """Cloud Storage trigger entry point. Processes OBJECT_FINALIZE events."""
    data = cloud_event.data
    bucket = data.get("bucket", "")
    name = data.get("name", "")

    if not bucket or not name:
        print(f"Invalid CloudEvent data: bucket={bucket}, name={name}", flush=True)
        return

    # Skip metadata and config files (per layer-four.md security considerations)
    if name.endswith("metadata.txt"):
        print(f"Skipping metadata file: {name}", flush=True)
        return

    if name.startswith("SEC/config/"):
        print(f"Skipping config file: {name}", flush=True)
        return

    result = process_object(bucket, name)
    print(f"Completed: {name} -> {result.get('output_path', 'N/A')}", flush=True)
