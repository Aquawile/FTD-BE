"""count_vectorized_content() caches per-file chunk counts by (name, generation)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services import vectorized_gcs


class _FakeBlob:
    def __init__(self, name: str, generation: int, chunks: int, fail: bool = False) -> None:
        self.name = name
        self.generation = generation
        self.chunks = chunks
        self.fail = fail
        self.downloads = 0

    def download_as_bytes(self) -> bytes:
        self.downloads += 1
        if self.fail:
            raise RuntimeError("download failed")
        return json.dumps({"chunks": [{}] * self.chunks}).encode("utf-8")


@pytest.fixture
def bucket(monkeypatch):
    """Fake bucket whose listing is controlled by `bucket.blobs`."""
    vectorized_gcs._chunk_count_cache.clear()
    fake_bucket = MagicMock()
    fake_bucket.blobs = []
    fake_bucket.list_blobs.side_effect = lambda prefix: [
        b for b in fake_bucket.blobs if b.name.startswith(prefix)
    ]
    client = MagicMock()
    client.bucket.return_value = fake_bucket
    with patch.object(vectorized_gcs, "_get_client", return_value=client):
        yield fake_bucket
    vectorized_gcs._chunk_count_cache.clear()


@pytest.mark.unit
def test_counts_once_then_serves_from_cache(bucket) -> None:
    a = _FakeBlob("sec-8k/1/a/x.json", 1, 3)
    b = _FakeBlob("sec-10k/2/b/y.json", 1, 5)
    other = _FakeBlob("sec-10k/2/b/readme.txt", 1, 99)
    bucket.blobs = [a, b, other]

    assert vectorized_gcs.count_vectorized_content() == 8
    assert vectorized_gcs.count_vectorized_content() == 8
    assert (a.downloads, b.downloads, other.downloads) == (1, 1, 0)


@pytest.mark.unit
def test_new_rewritten_and_deleted_files_change_the_total(bucket) -> None:
    a = _FakeBlob("sec-8k/1/a/x.json", 1, 3)
    b = _FakeBlob("sec-10k/2/b/y.json", 1, 5)
    bucket.blobs = [a, b]
    assert vectorized_gcs.count_vectorized_content() == 8

    a_rewritten = _FakeBlob("sec-8k/1/a/x.json", 2, 4)
    c = _FakeBlob("sec-8k/3/c/z.json", 1, 10)
    bucket.blobs = [a_rewritten, c]  # b deleted
    assert vectorized_gcs.count_vectorized_content() == 14
    assert b.downloads == 1 and a_rewritten.downloads == 1 and c.downloads == 1
    assert set(vectorized_gcs._chunk_count_cache) == {
        ("sec-8k/1/a/x.json", 2),
        ("sec-8k/3/c/z.json", 1),
    }


@pytest.mark.unit
def test_failed_download_counts_zero_and_is_retried(bucket) -> None:
    a = _FakeBlob("sec-8k/1/a/x.json", 1, 3, fail=True)
    bucket.blobs = [a]
    assert vectorized_gcs.count_vectorized_content() == 0

    a.fail = False
    assert vectorized_gcs.count_vectorized_content() == 3
    assert a.downloads == 2
