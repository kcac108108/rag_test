from pathlib import Path
from typing import List, Tuple
from langchain_core.documents import Document
from app.rag.vectorstore import get_vectorstore
from app.utils.paths import schema_dir, examples_dir

TEXT_EXTS = {".txt", ".md", ".sql", ".yaml", ".yml", ".json"}

def _load_text_files(folder: Path) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    if not folder.exists():
        return out
    for p in sorted(folder.glob("**/*")):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            out.append((p.name, p.read_text(encoding="utf-8", errors="ignore")))
    return out

def ingest_namespace(namespace: str, file_path: str | None = None) -> Tuple[int, List[str]]:
    vs = get_vectorstore()

    if namespace == "schema":
        folder = schema_dir()
    elif namespace == "examples":
        folder = examples_dir()
    else:
        folder = schema_dir().parent / namespace

    docs: List[Document] = []
    ids: List[str] = []

    if file_path:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"file_path not found: {file_path}")
        content = p.read_text(encoding="utf-8", errors="ignore")
        doc_id = f"{namespace}:{p.name}"
        docs.append(Document(page_content=content, metadata={"namespace": namespace, "id": doc_id, "source": str(p)}))
        ids.append(doc_id)
    else:
        for name, content in _load_text_files(folder):
            doc_id = f"{namespace}:{name}"
            docs.append(Document(page_content=content, metadata={"namespace": namespace, "id": doc_id, "source": str(folder / name)}))
            ids.append(doc_id)

    if not docs:
        return 0, []

    # best-effort delete existing ids then add (upsert-ish)
    try:
        vs._collection.delete(ids=ids)  # type: ignore[attr-defined]
    except Exception:
        pass

    vs.add_documents(docs, ids=ids)
    return len(ids), ids
