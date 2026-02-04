import argparse
from app.services.ingest_service import ingest_namespace

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", choices=["schema", "examples"], default="schema")
    parser.add_argument("--file_path", default=None)
    args = parser.parse_args()
    added, ids = ingest_namespace(args.namespace, file_path=args.file_path)
    print(f"Added {added} docs to namespace={args.namespace}")
    for _id in ids:
        print(" -", _id)

if __name__ == "__main__":
    main()
