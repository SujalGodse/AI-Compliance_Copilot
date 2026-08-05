import os
import fitz
import pytesseract
import json
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def chunk_fast(text, parent_words=800, child_words=150):
    words = text.split()
    parents = []
    for i in range(0, len(words), parent_words):
        p_words = words[i:i+parent_words]
        p_text = ' '.join(p_words)
        children = []
        for j in range(0, len(p_words), child_words):
            c_words = p_words[j:j+child_words]
            children.append(' '.join(c_words))
        parents.append({'parent_text': p_text, 'children': children})
    return parents

policies_dir = r'c:\Users\sujal\compliance_copilot\data\policies'
policy_files = [
    'customer_acceptance_policy.pdf',
    'customer_protection_policy.pdf',
    'deposit_policy.pdf',
    'fair_practices_code.pdf',
    'grievance_redressal_policy.pdf'
]

policy_data = {}

for f in policy_files:
    p = os.path.join(policies_dir, f)
    doc = fitz.open(p)
    full_text = ''
    for page in doc:
        t = page.get_text()
        if len(t.strip()) > 50:
            full_text += t + '\n'
        else:
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            full_text += pytesseract.image_to_string(img) + '\n'
    
    chunks = chunk_fast(full_text)
    policy_data[f] = chunks
    print(f'Prepared {f}: {len(chunks)} parent chunks')

with open('precalculated_policy_chunks.json', 'w', encoding='utf-8') as jf:
    json.dump(policy_data, jf, ensure_ascii=False)

print('Successfully created precalculated_policy_chunks.json!')
