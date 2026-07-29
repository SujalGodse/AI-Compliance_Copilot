# ============================================================
# eval/qa_testset.py
# Hand-curated 15 Q&A pairs for RAGAS evaluation.
# Covers the 8 compliance domains + mix of SEBI/RBI topics
# that actually exist in your ingested circulars and policies.
# ============================================================

QA_TESTSET = [
    {
        "question": "What is the base price and price band methodology for ETFs during the pre-open call auction session?",
        "ground_truth": "SEBI's circular on ETFs sets out norms for determining the base price and applicable price bands during the call auction in the pre-open session, and specifies the close-out procedure for exchange traded funds."
    },
    {
        "question": "What regulatory reporting obligations do Alternative Investment Funds (AIFs) have to SEBI?",
        "ground_truth": "SEBI's circular on regulatory reporting by AIFs specifies the format, frequency, and content requirements for periodic reporting by Alternative Investment Funds to the regulator."
    },
    {
        "question": "How are mutual fund schemes categorized and rationalized under SEBI's framework?",
        "ground_truth": "SEBI's circular on categorization and rationalization of mutual fund schemes defines standard scheme categories (equity, debt, hybrid, solution-oriented, etc.) to ensure uniformity and comparability across mutual fund houses."
    },
    {
        "question": "What changes were introduced by the addendum to SEBI's circular on borrowing by mutual funds?",
        "ground_truth": "The addendum modifies or clarifies specific provisions of the original circular governing the conditions and limits under which mutual funds may borrow."
    },
    {
        "question": "What is the special window for transfer and dematerialisation of physical securities under SEBI's ease of doing investment initiative?",
        "ground_truth": "SEBI introduced a special window allowing investors to transfer and dematerialise physical securities more easily, as part of its ease of doing investment and ease of doing business initiatives."
    },
    {
        "question": "What are the simplified requirements for an investor to obtain accreditation under SEBI's framework?",
        "ground_truth": "SEBI's circular simplifies the process and documentation requirements for investors seeking accredited investor status, reducing compliance burden for eligibility verification."
    },
    {
        "question": "What compliance reporting formats apply to Specialized Investment Funds (SIFs)?",
        "ground_truth": "SEBI specifies standardized reporting formats that Specialized Investment Funds must use to disclose their compliance status to the regulator."
    },
    {
        "question": "What is our bank's Know Your Customer (KYC) and Customer Acceptance Policy?",
        "ground_truth": "The bank's Customer Acceptance Policy sets out due diligence procedures for onboarding customers, including identity verification, risk categorization, and beneficial ownership checks, in line with KYC/AML norms."
    },
    {
        "question": "What is the bank's policy on customer grievance redressal?",
        "ground_truth": "The Grievance Redressal Policy establishes the process, timelines, and escalation matrix for customers to raise and resolve complaints, including recourse to the banking ombudsman."
    },
    {
        "question": "What does the bank's Fair Practices Code require in lending?",
        "ground_truth": "The Fair Practices Code sets standards for transparency, fair treatment, and responsible conduct in the bank's lending and recovery practices."
    },
    {
        "question": "What are the key terms of the bank's Deposit Policy?",
        "ground_truth": "The Deposit Policy outlines the types of deposit accounts offered, interest rate determination, premature withdrawal terms, and depositor protection measures."
    },
    {
        "question": "How does the bank's Customer Protection Policy address unauthorized transactions?",
        "ground_truth": "The Customer Protection Policy defines the bank's liability framework and reporting timelines for customers to report unauthorized electronic transactions and get reimbursed."
    },
    {
        "question": "What incentive structure exists for distributors onboarding new investors from B-30 cities and women investors?",
        "ground_truth": "SEBI extended the timeline for implementation of additional incentives for distributors who onboard new individual investors from beyond the top 30 (B-30) cities and women investors, to encourage mutual fund penetration."
    },
    {
        "question": "What changes were made regarding the letter of confirmation (LOC) requirement for demat account credits?",
        "ground_truth": "SEBI's circular does away with the requirement of issuing a letter of confirmation and instead allows direct credit of securities into the demat account, simplifying the investment process."
    },
    {
        "question": "What are the consequential requirements following amendments to SEBI's Merchant Bankers Regulations, 1992?",
        "ground_truth": "SEBI specifies the consequential compliance requirements that merchant bankers must follow as a result of amendments made to the SEBI (Merchant Bankers) Regulations, 1992."
    },
]

if __name__ == "__main__":
    print(f"Loaded {len(QA_TESTSET)} hand-curated Q&A pairs.")
    for i, qa in enumerate(QA_TESTSET, 1):
        print(f"{i}. {qa['question']}")