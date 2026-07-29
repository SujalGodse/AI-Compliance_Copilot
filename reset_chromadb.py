import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from embeddings import get_milvus_client, COL_CIRCULARS, COL_POLICIES
from pymilvus import utility

get_milvus_client()

for name in [COL_CIRCULARS, COL_POLICIES]:
    try:
        if utility.has_collection(name):
            utility.drop_collection(name)
            print(f"Dropped Milvus collection: {name}")
        else:
            print(f"Collection '{name}' does not exist — skipping")
    except Exception as e:
        print(f"Could not drop '{name}': {e}")

print("Milvus reset complete.")