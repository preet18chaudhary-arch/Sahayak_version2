import { useRef } from 'react'
import { formatDateTime, formatDocumentType } from '../utils/formatters'

export function RequiredDocuments({
  ruleConfig,
  uploadedDocuments,
  onUploadSlot,
  uploading,
}) {
  const inputRefs = useRef({})

  if (!ruleConfig || !ruleConfig.required_documents) {
    return null
  }

  const requiredList = ruleConfig.required_documents

  const verifiedCount = requiredList.filter((docType) =>
    uploadedDocuments.some(
      (doc) =>
        (doc.verification_status === 'VERIFIED' || doc.classification_status === 'MATCH') &&
        (doc.expected_type === docType || doc.detected_type === docType)
    )
  ).length

  const handleSlotFileChange = (docType, e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (onUploadSlot) {
        onUploadSlot(docType, file)
      }
      e.target.value = ''
    }
  }

  const triggerSlotPicker = (docType) => {
    if (uploading) return
    const input = inputRefs.current[docType]
    if (input) {
      input.click()
    }
  }

  return (
    <section className="dashboard-card required-docs-card">
      <div className="section-card-header">
        <div>
          <h3>Required Documents Checklist</h3>
          <p className="section-card-subtitle">
            Mandatory documents required for {ruleConfig.name}
          </p>
        </div>
        <span className={`count-pill ${verifiedCount === requiredList.length ? 'tag-green' : 'tag-neutral'}`}>
          {verifiedCount} / {requiredList.length} Verified
        </span>
      </div>

      <div className="required-docs-grid">
        {requiredList.map((docType) => {
          // Check for verified document for this slot
          const verifiedDoc = uploadedDocuments.find(
            (doc) =>
              (doc.verification_status === 'VERIFIED' || doc.classification_status === 'MATCH') &&
              (doc.expected_type === docType || doc.detected_type === docType)
          )

          // Check for mismatched document uploaded for this slot
          const mismatchedDoc = !verifiedDoc && uploadedDocuments.find(
            (doc) =>
              (doc.verification_status === 'DOCUMENT_TYPE_MISMATCH' || doc.classification_status === 'MISMATCH') &&
              doc.expected_type === docType
          )

          // Check for unreadable or unknown document uploaded for this slot
          const problemDoc = !verifiedDoc && !mismatchedDoc && uploadedDocuments.find(
            (doc) =>
              (doc.verification_status === 'UNREADABLE' || doc.verification_status === 'UNKNOWN_DOCUMENT') &&
              doc.expected_type === docType
          )

          let statusClass = 'missing'
          let statusTagClass = 'tag-orange'
          let statusLabel = 'Missing'
          let statusIcon = '!'

          if (verifiedDoc) {
            statusClass = 'uploaded'
            statusTagClass = 'tag-green'
            statusLabel = 'Uploaded & Verified'
            statusIcon = '✓'
          } else if (mismatchedDoc) {
            statusClass = 'mismatched'
            statusTagClass = 'tag-red'
            statusLabel = 'Wrong Document Type'
            statusIcon = '⚠'
          } else if (problemDoc) {
            statusClass = 'problem'
            statusTagClass = 'tag-orange'
            statusLabel = problemDoc.verification_status === 'UNREADABLE' ? 'Unreadable File' : 'Unrecognized Type'
            statusIcon = '?'
          }

          return (
            <div
              key={docType}
              className={`doc-checklist-item ${statusClass}`}
            >
              <input
                ref={(el) => (inputRefs.current[docType] = el)}
                type="file"
                accept=".png,.jpg,.jpeg,.pdf,.webp"
                style={{ display: 'none' }}
                onChange={(e) => handleSlotFileChange(docType, e)}
                disabled={uploading}
              />

              <div className="doc-checklist-status-icon">
                {statusIcon}
              </div>

              <div className="doc-checklist-content">
                <div className="doc-checklist-title-row">
                  <strong>{formatDocumentType(docType)}</strong>
                  <span className={`status-tag ${statusTagClass}`}>
                    {statusLabel}
                  </span>
                </div>

                <div className="doc-checklist-meta">
                  <span className="meta-requirement">Mandatory Requirement</span>

                  {verifiedDoc && (
                    <span className="meta-filename">
                      File: <em>{verifiedDoc.file_name}</em>
                      {verifiedDoc.uploaded_at && (
                        <small style={{ display: 'block', color: 'var(--text-muted)' }}>
                          Uploaded: {formatDateTime(verifiedDoc.uploaded_at)}
                        </small>
                      )}
                    </span>
                  )}

                  {mismatchedDoc && (
                    <div className="slot-mismatch-banner">
                      <p className="mismatch-msg">
                        <strong>Expected:</strong> {formatDocumentType(docType)}<br />
                        <strong>Detected:</strong> {formatDocumentType(mismatchedDoc.detected_type)}
                      </p>
                      {mismatchedDoc.message && (
                        <small className="mismatch-explanation">{mismatchedDoc.message}</small>
                      )}
                    </div>
                  )}

                  {problemDoc && problemDoc.message && (
                    <div className="slot-problem-banner">
                      <small className="problem-explanation">{problemDoc.message}</small>
                    </div>
                  )}
                </div>

                <div className="doc-checklist-action-row" style={{ marginTop: '0.6rem' }}>
                  {verifiedDoc ? (
                    <button
                      type="button"
                      className="secondary-button slot-action-btn"
                      onClick={() => triggerSlotPicker(docType)}
                      disabled={uploading}
                    >
                      🔄 Replace File
                    </button>
                  ) : mismatchedDoc ? (
                    <button
                      type="button"
                      className="primary-button slot-action-btn btn-danger-action"
                      onClick={() => triggerSlotPicker(docType)}
                      disabled={uploading}
                    >
                      ⚠ Upload Correct {formatDocumentType(docType)}
                    </button>
                  ) : problemDoc ? (
                    <button
                      type="button"
                      className="primary-button slot-action-btn"
                      onClick={() => triggerSlotPicker(docType)}
                      disabled={uploading}
                    >
                      🔄 Re-upload Clear {formatDocumentType(docType)}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="primary-button slot-action-btn"
                      onClick={() => triggerSlotPicker(docType)}
                      disabled={uploading}
                    >
                      ⬆ Upload {formatDocumentType(docType)}
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
