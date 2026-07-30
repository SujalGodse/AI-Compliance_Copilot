import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

import { API_BASE } from '../config'

function Policies() {
  const [policies, setPolicies] = useState(null)
  const [error, setError] = useState(null)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)

  const loadPolicies = () => {
    axios.get(`${API_BASE}/policies`)
      .then(res => setPolicies(res.data.policies))
      .catch(err => setError(err.message))
  }

  useEffect(() => {
    loadPolicies()
    const interval = setInterval(loadPolicies, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setUploadResult(null)
    setUploadError(null)
  }

  const fileInputRef = useState(null)

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setUploadResult(null)
    setUploadError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post(`${API_BASE}/policies/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000
      })
      setUploadResult(res.data)
      setFile(null)
      const inputEl = document.getElementById('policy-file-input')
      if (inputEl) inputEl.value = ''
      loadPolicies()
    } catch (err) {
      setUploadError(err.response?.data?.detail || err.message)
    } finally {
      setUploading(false)
    }
  }

  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>
  if (!policies) return <p>Loading policies...</p>

  return (
    <div>
      <h2 className="page-title">Bank Policies ({policies.length})</h2>
      <p className="page-sub">Internal Bank Policies indexed in Milvus & AWS RDS PostgreSQL for RAG Drift Analysis</p>

      {/* Upload Policy Card */}
      <div className="card mb-16" style={{ border: '2px dashed #0369a1', background: '#f8fafc', textAlign: 'center' }}>
        <div className="section-title">Upload New / Updated Policy PDF</div>
        <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px' }}>
          Uploading a PDF will automatically extract text, create parent-child chunks, update AWS RDS PostgreSQL, and generate 1024-dim Milvus vector embeddings.
        </p>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            id="policy-file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            style={{ fontSize: '13px', padding: '6px' }}
          />
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            style={{
              padding: '8px 20px',
              borderRadius: '6px',
              border: 'none',
              background: (!file || uploading) ? '#94a3b8' : '#0369a1',
              color: '#fff',
              fontWeight: 600,
              cursor: (!file || uploading) ? 'not-allowed' : 'pointer'
            }}
          >
            {uploading ? 'Processing & Re-Embedding...' : 'Upload & Index Policy'}
          </button>
        </div>

        {uploadResult && (
          <div style={{ marginTop: '14px', fontSize: '13px', color: '#2e7d32', fontWeight: 600 }}>
            ✅ {uploadResult.message || 'Policy uploaded and embedded successfully!'}
          </div>
        )}
        {uploadError && (
          <div style={{ marginTop: '14px', fontSize: '13px', color: '#c62828', fontWeight: 600 }}>
            ❌ Error: {uploadError}
          </div>
        )}
      </div>

      {/* Policy List Table */}
      <div className="card">
        <div className="section-title">Indexed Policy Documents</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Total Chunks</th>
              <th>Last Updated</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {policies.map(p => (
              <tr key={p.filename}>
                <td><strong>{p.filename}</strong></td>
                <td><span className="badge badge-blue">{p.chunks} Chunks</span></td>
                <td style={{ color: '#64748b' }}>{new Date(p.last_updated).toLocaleString()}</td>
                <td>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <a
                      href={p.s3_url || `${API_BASE}/policies/${p.filename}/file`}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: '4px 10px',
                        borderRadius: '4px',
                        border: '1px solid #2e7d32',
                        color: '#2e7d32',
                        textDecoration: 'none',
                        fontSize: '12px',
                        fontWeight: 600
                      }}
                    >
                      📄 View PDF
                    </a>
                    <Link
                      to={`/policies/${p.filename}`}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '4px',
                        border: '1px solid #0369a1',
                        color: '#0369a1',
                        textDecoration: 'none',
                        fontSize: '12px',
                        fontWeight: 600
                      }}
                    >
                      View Chunks
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Policies
