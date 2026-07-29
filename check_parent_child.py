import sys
sys.path.append('src')
from embeddings import search_similar

results = search_similar('investment adviser certification NISM', n_results=3)
for r in results:
    print(f"similarity={r['similarity']}  full_text_len={len(r['text'])}  matched_child_len={len(r['matched_child_text'])}")