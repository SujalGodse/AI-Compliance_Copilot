import fitz
import os

files = os.listdir("data/policies")
for f in files:
    if not f.endswith(".pdf"):
        continue
    path = f"data/policies/{f}"
    doc  = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    words = len(text.split())
    print(f"{f}: {words} words")