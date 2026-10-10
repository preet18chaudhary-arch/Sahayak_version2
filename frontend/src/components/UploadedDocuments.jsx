import {
  formatDateTime,
  formatDocumentType,
  getVerificationStatusBadge,
} from '../utils/formatters'

export function UploadedDocuments({ documents = [], onDeleteDocument, deletingDocId }) {
  return (
    <section className="dashboard-card">
      <div className="section-card-header">
        <div>
          <h3>Uploaded Documents ({documents.length})</h3>
          <p className="section-card-subtitle">
            Files analyzed and verified by the Sahayak verification engine
          </p>
        </div>
      </div>

      {documents.length === 0 ? (
        <div className="empty-state-box">
          <p>No documents uploaded yet.</p>
          <small>Select and upload your files above to start verification.</small>
        </div>
      ) : (
        <div className="uploaded-docs-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document File</th>
                <th>Target Slot</th>
                <th>Detected Type</th>
                <th>Verification Status</th>
                <th>Upload Time</th>
                {onDeleteDocument && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const badge = getVerificationStatusBadge(doc.verification_status)
                const isMismatch =
                  doc.verification_status === 'DOCUMENT_TYPE_MISMATCH' ||
                  doc.classification_status === 'MISMATCH'
                const isUnreadable =
                  doc.verification_status === 'UNREADABLE' ||
                  doc.verification_status === 'UNKNOWN_DOCUMENT'

                return (
                  <tr key={doc.doc_id} className={isMismatch ? 'row-mismatch' : ''}>
                    <td>
                      <div className="doc-file-cell">
                        <span className="file-icon-small">📄</span>
                        <div>
                          <strong>{doc.file_name}</strong>
                          <span className="doc-id-subtext">{doc.doc_id}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="slot-type-label">
                        {doc.expected_type
                          ? formatDocumentType(doc.expected_type)
                          : 'Auto / General'}
                      </span>
                    </td>
                    <td>
                      <span className="detected-type-badge">
                        {formatDocumentType(doc.detected_type)}
                      </span>
                    </td>
                    <td>
                      <div className="status-cell-content">
                        <span className={`status-tag ${badge.className}`}>
                          <span className="badge-icon">{badge.icon}</span> {badge.label}
                        </span>
                        {doc.message && (isMismatch || isUnreadable) && (
                          <div className="doc-table-message-note">
                            {doc.message}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="timestamp-cell">
                      {formatDateTime(doc.uploaded_at)}
                    </td>
                    {onDeleteDocument && (
                      <td>
                        <button
                          type="button"
                          className="delete-doc-btn"
                          title="Remove this document"
                          onClick={() => onDeleteDocument(doc.doc_id)}
                          disabled={deletingDocId === doc.doc_id}
                        >
                          {deletingDocId === doc.doc_id ? 'Removing...' : '🗑 Remove'}
                        </button>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
