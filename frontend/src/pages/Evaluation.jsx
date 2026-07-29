import StatCard from '../components/StatCard';

const RAGAS_DATA = [
  { q: "ETF base price and price band methodology?", answer_relevancy:0.6884, context_recall:0.7735, context_precision:0.5000, faithfulness:0.2037 },
  { q: "AIF regulatory reporting obligations to SEBI?", answer_relevancy:0.7702, context_recall:0.7800, context_precision:0.5000, faithfulness:0.1655 },
  { q: "Mutual fund scheme categorization under SEBI?", answer_relevancy:0.7371, context_recall:0.7611, context_precision:1.0000, faithfulness:0.1217 },
  { q: "Addendum to SEBI circular on mutual fund borrowing?", answer_relevancy:0.7247, context_recall:0.6098, context_precision:1.0000, faithfulness:0.1639 },
  { q: "Special window for physical securities dematerialisation?", answer_relevancy:0.7961, context_recall:0.6746, context_precision:0.5000, faithfulness:0.1203 },
  { q: "Simplified investor accreditation requirements?", answer_relevancy:0.8082, context_recall:0.7258, context_precision:0.5000, faithfulness:0.1369 },
  { q: "SIF compliance reporting formats?", answer_relevancy:0.7716, context_recall:0.6937, context_precision:1.0000, faithfulness:0.1388 },
  { q: "Bank KYC and Customer Acceptance Policy?", answer_relevancy:0.7902, context_recall:0.7055, context_precision:0.5000, faithfulness:0.0665 },
  { q: "Bank customer grievance redressal policy?", answer_relevancy:0.7894, context_recall:0.7267, context_precision:0.5000, faithfulness:0.2119 },
  { q: "Fair Practices Code in lending?", answer_relevancy:0.7660, context_recall:0.7098, context_precision:1.0000, faithfulness:0.2212 },
  { q: "Bank Deposit Policy key terms?", answer_relevancy:0.7593, context_recall:0.7046, context_precision:0.5000, faithfulness:0.3162 },
  { q: "Unauthorized transactions in Customer Protection Policy?", answer_relevancy:0.7913, context_recall:0.6825, context_precision:0.0000, faithfulness:0.0709 },
  { q: "Distributor incentive for B-30 and women investors?", answer_relevancy:0.7057, context_recall:0.7902, context_precision:0.5000, faithfulness:0.1009 },
  { q: "LOC requirement changes for demat account credits?", answer_relevancy:0.6945, context_recall:0.6868, context_precision:0.5000, faithfulness:0.1644 },
  { q: "Consequential requirements after Merchant Bankers Regulations amendment?", answer_relevancy:0.7611, context_recall:0.7203, context_precision:1.0000, faithfulness:0.2509 },
];

const METRICS = [
  { key:'answer_relevancy',   label:'Answer Relevancy',   desc:'How relevant is the answer to the question?' },
  { key:'context_recall',     label:'Context Recall',     desc:'Were all needed facts retrieved?' },
  { key:'context_precision',  label:'Context Precision',  desc:'How many retrieved chunks were relevant?' },
  { key:'faithfulness',       label:'Faithfulness',       desc:'Does the answer stay within the context?' },
];

function badge(v) {
  if (v >= 0.75) return 'badge badge-green';
  if (v >= 0.50) return 'badge badge-yellow';
  return 'badge badge-red';
}

function Evaluation() {
  const averages = METRICS.reduce((acc, m) => {
    const sum = RAGAS_DATA.reduce((s, row) => s + row[m.key], 0);
    acc[m.key] = sum / RAGAS_DATA.length;
    return acc;
  }, {});

  return (
    <div>
      <h2 className="page-title">RAGAS Evaluation</h2>
      <p className="page-sub">RAG pipeline quality assessment across {RAGAS_DATA.length} test questions</p>

      <div className="grid-4 mb-16">
        {METRICS.map(m => (
          <StatCard key={m.key} label={m.label} value={`${(averages[m.key] * 100).toFixed(1)}%`} />
        ))}
      </div>

      <div className="grid-2 mb-16">
        <div className="card">
          <div className="section-title">Average Scores</div>
          {METRICS.map(m => (
            <div key={m.key} className="mb-16">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                <span>{m.label}</span>
                <span style={{ fontWeight: 600 }}>{(averages[m.key] * 100).toFixed(1)}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${averages[m.key] * 100}%` }}></div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="card">
          <div className="section-title">Score Legend</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-green" style={{ minWidth: '50px', textAlign: 'center' }}>≥75%</span>
              <span>Excellent</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-yellow" style={{ minWidth: '50px', textAlign: 'center' }}>50-74%</span>
              <span>Acceptable</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-red" style={{ minWidth: '50px', textAlign: 'center' }}>&lt;50%</span>
              <span>Needs Improvement</span>
            </div>
          </div>
          <div style={{ marginTop: '20px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Note: Faithfulness scores are generally lower in standard evaluations due to strict citation requirements.
          </div>
        </div>
      </div>

      <div className="card">
        <div className="section-title">Per-Question Breakdown</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Ans. Relevancy</th>
              <th>Context Recall</th>
              <th>Ctx. Precision</th>
              <th>Faithfulness</th>
            </tr>
          </thead>
          <tbody>
            {RAGAS_DATA.map((row, idx) => (
              <tr key={idx} className="clickable">
                <td style={{ maxWidth: '400px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{row.q}</td>
                <td><span className={badge(row.answer_relevancy)}>{(row.answer_relevancy * 100).toFixed(1)}%</span></td>
                <td><span className={badge(row.context_recall)}>{(row.context_recall * 100).toFixed(1)}%</span></td>
                <td><span className={badge(row.context_precision)}>{(row.context_precision * 100).toFixed(1)}%</span></td>
                <td><span className={badge(row.faithfulness)}>{(row.faithfulness * 100).toFixed(1)}%</span></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ fontWeight: 700, background: '#f8fafc' }}>
              <td>AVERAGE</td>
              <td>{(averages.answer_relevancy * 100).toFixed(1)}%</td>
              <td>{(averages.context_recall * 100).toFixed(1)}%</td>
              <td>{(averages.context_precision * 100).toFixed(1)}%</td>
              <td>{(averages.faithfulness * 100).toFixed(1)}%</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

export default Evaluation;
