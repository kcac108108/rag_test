from typing import List
from app.rag.vectorstore import get_vectorstore
from app.schemas.common import SourceChunk

def retrieve(query: str, top_k: int = 5, namespace: str | None = None) -> List[SourceChunk]:
    vs = get_vectorstore()
    search_kwargs = {"k": top_k}
    if namespace:
        search_kwargs["filter"] = {"namespace": namespace}

    docs_and_scores = vs.similarity_search_with_score(query, **search_kwargs)
    out: List[SourceChunk] = []
    for i, (doc, score) in enumerate(docs_and_scores):
        out.append(SourceChunk(
            id=str(doc.metadata.get("id", f"{namespace or 'chunk'}_{i}")),
            text=doc.page_content,
            metadata=dict(doc.metadata),
            score=float(score) if score is not None else None
        ))
    return out
