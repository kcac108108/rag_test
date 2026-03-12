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
        docs.append(Document(
            page_content=content,
            metadata={
                "namespace": namespace,
                "id": doc_id,
                "source": str(p),
            }
        ))
        ids.append(doc_id)
    else:
        for name, content in _load_text_files(folder):
            doc_id = f"{namespace}:{name}"
            docs.append(Document(
                page_content=content,
                metadata={
                    "namespace": namespace,
                    "id": doc_id,
                    "source": str(folder / name),
                }
            ))
            ids.append(doc_id)

    if not docs:
        return 0, []

    try:
        vs._collection.delete(ids=ids)  # type: ignore[attr-defined]
    except Exception:
        pass

    vs.add_documents(docs, ids=ids)
    return len(ids), ids


# ===============================
# 표준품명 전용 인덱싱 (정확도 강화 버전)
# ===============================

from sqlalchemy import text
from app.db.connectors.oracle import get_engine


def ingest_std():
    """
    정확도 극대화를 위한 표준품명/동의어 인덱싱.

    개선사항:
    - std_master에 HS_CODE 포함
    - std_master / std_synonym 모두 설명 포함
    - 구조화된 태그 사용
    - metadata에 hs_code/std_desc 저장
    """

    vs = get_vectorstore()
    eng = get_engine()

    with eng.connect() as conn:

        # -----------------------------
        # 1. STD_MASTER
        # -----------------------------
        rows = conn.execute(text("""
            SELECT
                M.STD_ID,
                M.STD_NM,
                M.STD_DESC,
                M.HS_CODE
            FROM TE_STD001M M
            WHERE M.IS_ACTIVE = 'Y'
        """)).fetchall()

        docs = []
        ids = []

        for r in rows:
            std_id, name, desc, hs_code = r

            content = (
                f"[TYPE] STD_MASTER\n"
                f"[STD_ID] {std_id}\n"
                f"[STD_NAME] {name}\n"
                f"[DESCRIPTION] {desc or ''}\n"
                f"[HS_CODE] {hs_code or ''}\n"
            )

            doc_id = f"std_master:{std_id}"

            docs.append(Document(
                page_content=content,
                metadata={
                    "namespace": "std_master",
                    "id": doc_id,
                    "std_id": std_id,
                    "std_name": name,
                    "std_desc": desc,
                    "hs_code": hs_code,
                }
            ))
            ids.append(doc_id)

        if docs:
            try:
                vs._collection.delete(ids=ids)
            except Exception:
                pass
            vs.add_documents(docs, ids=ids)

        # -----------------------------
        # 2. STD_SYNONYM
        # -----------------------------
        rows = conn.execute(text("""
            SELECT
                L.SYN_ID,
                L.SYN_NM,
                M.STD_ID,
                M.STD_NM,
                M.STD_DESC,
                M.HS_CODE
            FROM TE_STD002L L
            JOIN TE_STD001M M ON L.STD_ID = M.STD_ID
            WHERE L.IS_ACTIVE = 'Y'
        """)).fetchall()

        docs = []
        ids = []

        for r in rows:
            syn_id, syn_nm, std_id, std_name, std_desc, hs_code = r

            content = (
                f"[TYPE] STD_SYNONYM\n"
                f"[SYNONYM] {syn_nm}\n"
                f"[STD_NAME] {std_name}\n"
                f"[DESCRIPTION] {std_desc or ''}\n"
                f"[HS_CODE] {hs_code or ''}\n"
            )

            doc_id = f"std_synonym:{syn_id}"

            docs.append(Document(
                page_content=content,
                metadata={
                    "namespace": "std_synonym",
                    "id": doc_id,
                    "std_id": std_id,
                    "std_name": std_name,
                    "std_desc": std_desc,
                    "hs_code": hs_code,
                }
            ))
            ids.append(doc_id)

        if docs:
            try:
                vs._collection.delete(ids=ids)
            except Exception:
                pass
            vs.add_documents(docs, ids=ids)