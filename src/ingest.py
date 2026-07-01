from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import pickle
import re
from typing import Iterable

import faiss
import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .config import MATERIALS_DIR, VECTOR_STORE_DIR, SUPPORTED_EXTENSIONS, AppConfig, ensure_project_dirs


INDEX_PATH = VECTOR_STORE_DIR / "index.faiss"
VECTORIZER_PATH = VECTOR_STORE_DIR / "vectorizer.pkl"
CHUNKS_PATH = VECTOR_STORE_DIR / "chunks.json"


@dataclass
class DocumentChunk:
    id: int
    source: str
    location: str
    text: str


def list_material_files(materials_dir: Path = MATERIALS_DIR) -> list[Path]:
    ensure_project_dirs()
    return sorted(
        path for path in materials_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and path.name.lower() != "readme.md"
    )


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def read_pdf(path: Path) -> list[tuple[str, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[str, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append((f"第 {index} 页", text))
    return pages


def clean_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    sections = split_markdown_sections(text)
    if len(sections) > 1:
        chunks: list[str] = []
        for section in sections:
            chunks.extend(split_text_by_window(section, chunk_size, overlap))
        return chunks
    return split_text_by_window(text, chunk_size, overlap)


def split_markdown_sections(text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{1,3}\s+", line) and current:
            section = "\n".join(current).strip()
            if section:
                sections.append(section)
            current = [line]
        else:
            current.append(line)
    if current:
        section = "\n".join(current).strip()
        if section:
            sections.append(section)
    return sections


def split_text_by_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def load_documents(config: AppConfig, materials_dir: Path = MATERIALS_DIR) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    next_id = 0
    for path in list_material_files(materials_dir):
        if path.suffix.lower() == ".pdf":
            page_items = read_pdf(path)
        else:
            page_items = [("全文", read_text_file(path))]

        for location, raw_text in page_items:
            for piece_index, piece in enumerate(split_text(raw_text, config.chunk_size, config.chunk_overlap), start=1):
                chunks.append(
                    DocumentChunk(
                        id=next_id,
                        source=str(path.relative_to(materials_dir)),
                        location=f"{location} / 片段 {piece_index}",
                        text=piece,
                    )
                )
                next_id += 1
    return chunks


def build_vector_store(config: AppConfig, materials_dir: Path = MATERIALS_DIR) -> tuple[int, str]:
    ensure_project_dirs()
    chunks = load_documents(config, materials_dir)
    if not chunks:
        empty_payload: list[dict[str, str | int]] = []
        CHUNKS_PATH.write_text(json.dumps(empty_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0, "未发现可导入资料。请将 .txt、.md、.pdf 文件放入 materials 目录，或在页面上传文件。"

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(1, 3),
        min_df=1,
        max_features=50000,
    )
    matrix = vectorizer.fit_transform([chunk.text for chunk in chunks])
    dense = normalize(matrix, norm="l2", axis=1).astype(np.float32).toarray()
    index = faiss.IndexFlatIP(dense.shape[1])
    index.add(dense)

    serialized_index = faiss.serialize_index(index)
    INDEX_PATH.write_bytes(serialized_index.tobytes())
    with VECTORIZER_PATH.open("wb") as f:
        pickle.dump(vectorizer, f)
    CHUNKS_PATH.write_text(
        json.dumps([asdict(chunk) for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(chunks), f"知识库构建完成，共生成 {len(chunks)} 个文本片段。"


def vector_store_exists() -> bool:
    return INDEX_PATH.exists() and VECTORIZER_PATH.exists() and CHUNKS_PATH.exists()


def load_vector_store() -> tuple[faiss.Index, TfidfVectorizer, list[DocumentChunk]]:
    if not vector_store_exists():
        raise FileNotFoundError("向量库不存在，请先构建知识库。")
    index_bytes = np.frombuffer(INDEX_PATH.read_bytes(), dtype=np.uint8)
    index = faiss.deserialize_index(index_bytes)
    with VECTORIZER_PATH.open("rb") as f:
        vectorizer = pickle.load(f)
    data = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    chunks = [DocumentChunk(**item) for item in data]
    return index, vectorizer, chunks


def save_uploaded_files(files: Iterable, materials_dir: Path = MATERIALS_DIR) -> list[Path]:
    ensure_project_dirs()
    saved: list[Path] = []
    for file in files:
        filename = Path(file.name).name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            continue
        target = materials_dir / filename
        target.write_bytes(file.getbuffer())
        saved.append(target)
    return saved
