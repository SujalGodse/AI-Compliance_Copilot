# ============================================================
# eval/simple_ragas.py
# Lightweight RAGAS-style evaluator using only:
#   - Local Ollama bge-m3 embeddings (cosine similarity)
#   - Simple keyword overlap math
# No cloud LLM judge needed -- runs in ~1-3 minutes!
#
# Metrics implemented:
#   1. Answer Relevancy    -- cosine(question_vec, answer_vec)
#   2. Context Recall      -- cosine(ground_truth_vec, best_context_vec)
#   3. Context Precision   -- are top chunks more similar to ground_truth?
#   4. Faithfulness        -- keyword overlap: answer terms found in context?
# ============================================================

import os
import sys
import json
import re
import math
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "src"))
sys.path.append(EVAL_DIR)

from dotenv import load_dotenv
load_dotenv()

from groq import Groq
from embeddings import search_similar, get_embedding, COL_CIRCULARS, COL_POLICIES
from qa_testset import QA_TESTSET

CHECKPOINT_PATH = os.path.join(BASE_DIR, "eval", "qa_answers_checkpoint.json")
OUT_PATH        = os.path.join(BASE_DIR, "eval", "simple_ragas_results.csv")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# -------------------------------------------------
# MATH UTILITIES
# -------------------------------------------------

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot   = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def keyword_overlap(text_a: str, text_b: str) -> float:
    """Jaccard-style keyword overlap between two text strings."""
    def tokenize(t):
        tokens = re.findall(r'\b[a-z]{3,}\b', t.lower())
        stop = {'the', 'and', 'for', 'are', 'not', 'with', 'that', 'this',
                'from', 'has', 'have', 'its', 'will', 'may', 'can', 'been'}
        return set(tok for tok in tokens if tok not in stop)

    set_a = tokenize(text_a)
    set_b = tokenize(text_b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union        = set_a | set_b
    return len(intersection) / len(union)


# -------------------------------------------------
# PHASE 1 -- ANSWER GENERATION (with checkpoint)
# -------------------------------------------------

def get_answer_and_context(question: str):
    """Run one question through the live RAG pipeline."""
    circular_chunks = search_similar(query_text=question, n_results=3, collection_name=COL_CIRCULARS)
    policy_chunks   = search_similar(query_text=question, n_results=3, collection_name=COL_POLICIES)
    chunks = sorted(circular_chunks + policy_chunks, key=lambda c: c["similarity"], reverse=True)[:3]

    contexts      = [c["text"] for c in chunks]
    context_block = "\n\n".join(contexts)

    prompt = f"""You are a compliance assistant for an Indian bank.
Answer the question using only the context provided below.
If the answer is not in the context, say "I don't have that information."

Context:
{context_block}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model="qwen-2.5-coder-32b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300,
    )
    answer = response.choices[0].message.content.strip()
    return answer, contexts


def run_phase1():
    """Load checkpoint if exists, otherwise generate answers for all questions."""
    if os.path.exists(CHECKPOINT_PATH):
        print(f"[OK] Checkpoint found -- loading cached answers from {CHECKPOINT_PATH}")
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"No checkpoint found. Running {len(QA_TESTSET)} questions through the pipeline...")
    records = []
    for i, qa in enumerate(QA_TESTSET, 1):
        print(f"  [{i}/{len(QA_TESTSET)}] {qa['question'][:70]}...")
        answer, contexts = get_answer_and_context(qa["question"])
        records.append({
            "question":     qa["question"],
            "answer":       answer,
            "contexts":     contexts,
            "ground_truth": qa["ground_truth"],
        })

    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"[OK] Checkpoint saved to {CHECKPOINT_PATH}")
    return records


# -------------------------------------------------
# PHASE 2 -- LOCAL METRIC COMPUTATION
# -------------------------------------------------

def compute_answer_relevancy(question: str, answer: str) -> float:
    """
    How directly does the answer address the question?
    Method: cosine similarity between question embedding and answer embedding.
    Score range: 0.0 (unrelated) -> 1.0 (identical meaning)
    """
    q_vec = get_embedding(question)
    a_vec = get_embedding(answer)
    return round(cosine_similarity(q_vec, a_vec), 4)


def compute_context_recall(ground_truth: str, contexts: list) -> float:
    """
    Did the retriever find the information needed to answer correctly?
    Method: max cosine similarity between ground_truth and each retrieved context.
    Score range: 0.0 (context misses the answer) -> 1.0 (perfect match)
    """
    gt_vec = get_embedding(ground_truth)
    scores = [cosine_similarity(gt_vec, get_embedding(ctx)) for ctx in contexts]
    return round(max(scores) if scores else 0.0, 4)


def compute_context_precision(ground_truth: str, contexts: list) -> float:
    """
    Are the most relevant chunks ranked first?
    Method: check if chunk similarities to ground_truth are in descending order.
    Score: proportion of adjacent pairs where rank[i] >= rank[i+1]
    """
    if len(contexts) <= 1:
        return 1.0
    gt_vec  = get_embedding(ground_truth)
    scores  = [cosine_similarity(gt_vec, get_embedding(ctx)) for ctx in contexts]
    ordered = sum(1 for i in range(len(scores) - 1) if scores[i] >= scores[i + 1])
    return round(ordered / (len(scores) - 1), 4)


def compute_faithfulness(answer: str, contexts: list) -> float:
    """
    Is the answer grounded in the retrieved context (no hallucination)?
    Method: keyword overlap (Jaccard) between answer and combined context.
    Score range: 0.0 (answer has no grounding) -> 1.0 (fully grounded)
    """
    combined_context = " ".join(contexts)
    return round(keyword_overlap(answer, combined_context), 4)


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    print("\n" + "="*60)
    print("  Simple RAGAS Evaluation -- Local Math (No LLM Judge)")
    print("="*60 + "\n")

    # Phase 1: Get answers (from checkpoint or live pipeline)
    records = run_phase1()
    print(f"\n[OK] Loaded {len(records)} Q&A records.\n")

    # Phase 2: Evaluate each record using local math
    print("Computing metrics locally (no API calls needed)...")
    print("-" * 60)

    results = []
    totals  = {"answer_relevancy": 0, "context_recall": 0,
               "context_precision": 0, "faithfulness": 0}

    for i, r in enumerate(records, 1):
        q   = r["question"]
        a   = r["answer"]
        ctx = r["contexts"]
        gt  = r["ground_truth"]

        ar = compute_answer_relevancy(q, a)
        cr = compute_context_recall(gt, ctx)
        cp = compute_context_precision(gt, ctx)
        f  = compute_faithfulness(a, ctx)

        totals["answer_relevancy"]   += ar
        totals["context_recall"]     += cr
        totals["context_precision"]  += cp
        totals["faithfulness"]       += f

        print(f"[{i:02d}] {q[:55]}...")
        print(f"      AR={ar:.3f}  CR={cr:.3f}  CP={cp:.3f}  F={f:.3f}")

        results.append({
            "question":          q,
            "answer":            a,
            "ground_truth":      gt,
            "answer_relevancy":  ar,
            "context_recall":    cr,
            "context_precision": cp,
            "faithfulness":      f,
        })

    # Averages
    n = len(records)
    avg = {k: round(v / n, 4) for k, v in totals.items()}

    print("\n" + "="*60)
    print("  OVERALL AVERAGE SCORES")
    print("="*60)
    print(f"  Answer Relevancy  : {avg['answer_relevancy']:.4f}")
    print(f"  Context Recall    : {avg['context_recall']:.4f}")
    print(f"  Context Precision : {avg['context_precision']:.4f}")
    print(f"  Faithfulness      : {avg['faithfulness']:.4f}")
    print("="*60 + "\n")

    # Save to CSV
    fieldnames = ["question", "answer", "ground_truth",
                  "answer_relevancy", "context_recall", "context_precision", "faithfulness"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"[OK] Results saved to {OUT_PATH}")
    print(f"     Evaluated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    main()
