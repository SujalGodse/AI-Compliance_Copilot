# ============================================================
# eval/run_evaluation.py
# Runs the 15 hand-curated questions through the real pipeline,
# checkpoints the answers, then scores them with RAGAS.
# Answer generation and RAGAS scoring are now separate phases —
# if scoring fails, re-run without regenerating answers.
# ============================================================

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "src"))

from dotenv import load_dotenv
load_dotenv()

from groq import Groq
from qa_testset import QA_TESTSET

from datasets import Dataset
from ragas import evaluate, RunConfig
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_groq import ChatGroq
from langchain_ollama import OllamaEmbeddings

from embeddings import search_similar, COL_CIRCULARS, COL_POLICIES

CHECKPOINT_PATH = os.path.join(BASE_DIR, "eval", "qa_answers_checkpoint.json")
OUT_PATH        = os.path.join(BASE_DIR, "eval", "evaluation_results.csv")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise SystemExit("GROQ_API_KEY not set — check your .env file.")

client = Groq(api_key=GROQ_API_KEY)

# ─────────────────────────────────────────
# PHASE 1 — GET ANSWER + CONTEXT FOR ONE QUESTION
# ─────────────────────────────────────────

def get_answer_and_context(question):
    circular_chunks = search_similar(
        query_text=question, n_results=5, collection_name=COL_CIRCULARS
    )
    policy_chunks = search_similar(
        query_text=question, n_results=5, collection_name=COL_POLICIES
    )
    chunks = sorted(
        circular_chunks + policy_chunks,
        key=lambda c: c["similarity"],
        reverse=True
    )[:3]

    contexts = [c["text"] for c in chunks]
    context_block = "\n\n".join(contexts)

    prompt = f"""You are a compliance assistant for an Indian bank.
Answer the question using only the context provided below.
If the answer is not in the context, say "I don't have that information."

Context:
{context_block}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=512,
    )
    answer = response.choices[0].message.content.strip()
    return answer, contexts


def run_phase1():
    """Generate answers, or load them from checkpoint if already done."""
    if os.path.exists(CHECKPOINT_PATH):
        print(f"Found checkpoint at {CHECKPOINT_PATH} — loading cached answers.")
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"No checkpoint found. Running {len(QA_TESTSET)} questions through the pipeline...")
    records = []
    for i, qa in enumerate(QA_TESTSET, 1):
        print(f"[{i}/{len(QA_TESTSET)}] {qa['question'][:60]}...")
        answer, contexts = get_answer_and_context(qa["question"])
        records.append({
            "question": qa["question"],
            "answer": answer,
            "contexts": contexts,
            "ground_truth": qa["ground_truth"],
        })

    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Checkpoint saved to {CHECKPOINT_PATH}")
    return records

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    records = run_phase1()

    eval_dataset = Dataset.from_dict({
        "question": [r["question"] for r in records],
        "answer": [r["answer"] for r in records],
        "contexts": [r["contexts"] for r in records],
        "ground_truth": [r["ground_truth"] for r in records],
    })

    print("Setting up judge LLM (Groq 70B) and embeddings (Ollama)...")
    judge_llm = LangchainLLMWrapper(
        ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0)
    )
    judge_embeddings = LangchainEmbeddingsWrapper(
        OllamaEmbeddings(model="bge-m3:latest")
    )

    # strictness=1 -> avoids Groq's "n must be at most 1" 400 error
    # (default strictness=3 asks for 3 completions per call)
    metrics = [
        Faithfulness(),
        AnswerRelevancy(strictness=1),
        ContextPrecision(),
        ContextRecall(),
    ]

    # sequential-ish execution avoids stacking retries into 429 pile-ups;
    # slower wall-clock time but should actually complete without timeouts
    run_config = RunConfig(max_workers=1, timeout=300, max_retries=15, max_wait=90)

    print("Running RAGAS evaluation (this may take several minutes)...")
    result = evaluate(
        eval_dataset,
        metrics=metrics,
        llm=judge_llm,
        embeddings=judge_embeddings,
        run_config=run_config,
    )

    df = result.to_pandas()
    df.to_csv(OUT_PATH, index=False)

    print(f"\nDone. Saved results to {OUT_PATH}")
    print("\nOverall scores:")
    print(df[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]].mean())

if __name__ == "__main__":
    main()