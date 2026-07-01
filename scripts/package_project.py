from __future__ import annotations

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "数据结构RAG智能问答Agent.zip"

INCLUDE = [
    "app.py",
    "README.md",
    "requirements.txt",
    ".env.example",
    "说明文档.docx",
    "src",
    "materials",
    "vector_store",
    "scripts",
    "tests",
]

EXCLUDED_DIRS = {"__pycache__", "package_stage", "report_render"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name == ZIP_PATH.name:
        return False
    return True


def iter_files(path: Path):
    if path.is_file() and should_include(path):
        yield path
    elif path.is_dir():
        for child in path.rglob("*"):
            if child.is_file() and should_include(child.relative_to(ROOT)):
                yield child


def main() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE:
            path = ROOT / item
            if not path.exists():
                raise FileNotFoundError(path)
            for file_path in iter_files(path):
                zf.write(file_path, file_path.relative_to(ROOT).as_posix())
    print(ZIP_PATH)


if __name__ == "__main__":
    main()
