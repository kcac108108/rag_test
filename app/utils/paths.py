from pathlib import Path

def project_root() -> Path:
    # paths.py 위치: rag_test/app/utils/paths.py
    # parents[0]=utils, [1]=app, [2]=rag_test(프로젝트 루트)
    return Path(__file__).resolve().parents[2]

def data_dir() -> Path:
    return project_root() / "data"

def schema_dir() -> Path:
    return data_dir() / "schema"

def examples_dir() -> Path:
    return data_dir() / "examples"
