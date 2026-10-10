import { useRef, useState } from 'react'
import {
  DOCUMENT_TYPE_LABELS,
  formatDocumentType,
} from '../utils/formatters'

export function DocumentUpload({
  onUploadFiles,
  uploading,
  uploadProgress,
  lastUploadResult,
  error,
  ruleConfig,
}) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [targetSlot, setTargetSlot] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files)
      setSelectedFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name))
        const filteredNew = newFiles.filter((f) => !existingNames.has(f.name))
        return [...prev, ...filteredNew]
      })
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files)
      setSelectedFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name))
        const filteredNew = droppedFiles.filter((f) => !existingNames.has(f.name))
        return [...prev, ...filteredNew]
      })
    }
  }

  const handleRemoveFile = (fileName) => {
    setSelectedFiles((prev) => prev.filter((f) => f.name !== fileName))
  }

  const handleTriggerUpload = async () => {
    if (selectedFiles.length === 0 || uploading) return
    const filesToUpload = [...selectedFiles]
    const chosenSlot = targetSlot ? targetSlot : null
    const success = await onUploadFiles(filesToUpload, chosenSlot)
    if (success) {
      setSelectedFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // Determine slot options
  const requiredDocs = ruleConfig?.required_documents || []
  const otherCommonSlots = Object.keys(DOCUMENT_TYPE_LABELS).filter(
    (key) =>
      !requiredDocs.includes(key) &&
      key !== 'unknown' &&
      key !== 'other' &&
      key !== 'itr_computation' &&
      key !== 'itr_acknowledgement'
  )

  return (
    <section className="dashboard-card upload-section-card">
      <div className="section-card-header">
        <div>
          <h3>Upload Scholarship Documents</h3>
          <p className="section-card-subtitle">
            Upload PDF (text or scanned) or image files (PNG, JPG, JPEG, WEBP). Max 15MB each.
          </p>
        </div>
      </div>

      {/* Target Slot Selection */}
      <div className="target-slot-selector-row">
        <label htmlFor="slot-select" className="slot-select-label">
          Target Document Slot (Optional):
        </label>
        <select
          id="slot-select"
          className="slot-select-dropdown"
          value={targetSlot}
          onChange={(e) => setTargetSlot(e.target.value)}
          disabled={uploading}
        >
          <option value="">Auto-Detect Document Type (General Upload)</option>
          {requiredDocs.length > 0 && (
            <optgroup label="Mandatory Scheme Documents">
              {requiredDocs.map((docType) => (
                <option key={docType} value={docType}>
                  ★ {formatDocumentType(docType)} (Required)
                </option>
              ))}
            </optgroup>
          )}
          <optgroup label="Other Standard Documents">
            {otherCommonSlots.map((docType) => (
              <option key={docType} value={docType}>
                {formatDocumentType(docType)}
              </option>
            ))}
          </optgroup>
        </select>
        <small className="slot-select-hint">
          {targetSlot
            ? `Uploading as "${formatDocumentType(targetSlot)}". The engine will verify document type matches this slot.`
            : 'Engine will automatically identify and categorize the uploaded file.'}
        </small>
      </div>

      <div
        className={`dropzone-container ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.pdf,.webp"
          style={{ display: 'none' }}
          onChange={handleFileChange}
          disabled={uploading}
        />

        <div className="dropzone-icon">📁</div>
        <p className="dropzone-headline">
          {uploading ? 'Processing documents...' : 'Click to browse or drag & drop files here'}
        </p>
        <span className="dropzone-hint">
          Supports PDF (both text and scanned) and PNG, JPG, JPEG, WEBP (Max 15MB per file)
        </span>
      </div>

      {selectedFiles.length > 0 && (
        <div className="selected-queue">
          <div className="selected-queue-header">
            <strong>Ready to Upload ({selectedFiles.length})</strong>
            <button
              type="button"
              className="text-button text-danger"
              onClick={() => setSelectedFiles([])}
              disabled={uploading}
            >
              Clear All
            </button>
          </div>

          <div className="selected-file-list">
            {selectedFiles.map((file) => (
              <div className="selected-file-item" key={file.name}>
                <div className="file-info">
                  <span className="file-icon">📄</span>
                  <div>
                    <span className="file-name">{file.name}</span>
                    <small className="file-size">
                      {(file.size / 1024).toFixed(1)} KB
                    </small>
                  </div>
                </div>

                {!uploading && (
                  <button
                    type="button"
                    className="remove-file-button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveFile(file.name)
                    }}
                    title="Remove file"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="upload-action-row">
            <button
              className="primary-button upload-submit-btn"
              type="button"
              onClick={handleTriggerUpload}
              disabled={uploading}
            >
              {uploading
                ? `Uploading ${uploadProgress.current} of ${uploadProgress.total}...`
                : targetSlot
                ? `Upload to "${formatDocumentType(targetSlot)}" Slot`
                : `Upload & Verify ${selectedFiles.length} Document${selectedFiles.length > 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      )}

      {uploading && (
        <div className="upload-progress-box">
          <div className="spinner"></div>
          <div className="progress-text">
            <strong>
              Uploading & Verifying {uploadProgress.current} of {uploadProgress.total}
            </strong>
            <span>Currently processing: <em>{uploadProgress.currentFileName}</em></span>
          </div>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{
                width: `${(uploadProgress.current / Math.max(uploadProgress.total, 1)) * 100}%`,
              }}
            ></div>
          </div>
        </div>
      )}

      {/* Upload Feedback Banners */}
      {lastUploadResult && !uploading && (() => {
        const isMismatch =
          lastUploadResult.verification_status === 'DOCUMENT_TYPE_MISMATCH' ||
          lastUploadResult.classification_status === 'MISMATCH'
        const isUnreadable =
          lastUploadResult.verification_status === 'UNREADABLE'
        const isUnknown =
          lastUploadResult.verification_status === 'UNKNOWN_DOCUMENT' ||
          lastUploadResult.detected_type === 'unknown'

        if (isMismatch) {
          return (
            <div className="mismatch-alert-box">
              <div className="alert-icon">⚠</div>
              <div className="alert-content">
                <strong>Document Type Mismatch</strong>
                <p>
                  You uploaded <em>{lastUploadResult.file_name}</em> into the{' '}
                  <strong>{formatDocumentType(lastUploadResult.expected_type)}</strong> slot,
                  but it was detected as <strong>{formatDocumentType(lastUploadResult.detected_type)}</strong>.
                </p>
                <div className="alert-action-guidance">
                  {lastUploadResult.message ||
                    `Please upload a valid ${formatDocumentType(lastUploadResult.expected_type)} to fulfill this requirement.`}
                </div>
              </div>
            </div>
          )
        }

        if (isUnreadable) {
          return (
            <div className="unreadable-alert-box">
              <div className="alert-icon">✕</div>
              <div className="alert-content">
                <strong>Document Unreadable</strong>
                <p>
                  We could not extract readable text from <em>{lastUploadResult.file_name}</em>.
                </p>
                <div className="alert-action-guidance">
                  {lastUploadResult.message ||
                    'Please upload a clearer scan, a high-resolution image, or a valid PDF document.'}
                </div>
              </div>
            </div>
          )
        }

        if (isUnknown) {
          return (
            <div className="unknown-alert-box">
              <div className="alert-icon">?</div>
              <div className="alert-content">
                <strong>Unrecognized Document</strong>
                <p>
                  The engine could not identify <em>{lastUploadResult.file_name}</em> as a recognized scholarship document.
                </p>
                <div className="alert-action-guidance">
                  {lastUploadResult.message ||
                    'Please verify the file contains visible headers such as Aadhaar, Marksheet, or Income Certificate.'}
                </div>
              </div>
            </div>
          )
        }

        return (
          <div className="upload-success-banner">
            <span className="banner-check">✓</span>
            <div>
              <strong>Document Processed: {lastUploadResult.file_name}</strong>
              <p>
                Verified as: <strong>{formatDocumentType(lastUploadResult.detected_type)}</strong>
                {lastUploadResult.expected_type && (
                  <span> (Slot: {formatDocumentType(lastUploadResult.expected_type)})</span>
                )}
              </p>
            </div>
          </div>
        )
      })()}

      {error && <div className="error-banner">{error}</div>}
    </section>
  )
}
