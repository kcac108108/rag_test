from app.core.config import settings
from app.rag.embeddings import get_embeddings

def get_vectorstore():
    from langchain_chroma import Chroma
    embeddings = get_embeddings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings,
        persist_directory=settings.chroma_dir,
    )
