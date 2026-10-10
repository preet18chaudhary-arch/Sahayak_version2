export const DOCUMENT_TYPE_LABELS = {
  aadhaar: 'Aadhaar Card',
  marksheet_10th: '10th Marksheet',
  marksheet_12th: '12th Marksheet',
  income_certificate: 'Income Certificate',
  caste_certificate: 'Caste Certificate',
  domicile_certificate: 'Domicile Certificate',
  bank_passbook: 'Bank Passbook',
  pan_card: 'PAN Card',
  itr_computation: 'ITR Computation',
  itr_acknowledgement: 'ITR Acknowledgement',
  unknown: 'Unknown Document',
  other: 'Other Document',
}

export function formatDocumentType(type) {
  if (!type) return 'Unknown Document'
  const key = String(type).toLowerCase()
  return DOCUMENT_TYPE_LABELS[key] || type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export const FIELD_NAME_LABELS = {
  name: 'Student Name',
  date_of_birth: 'Date of Birth',
  income: 'Annual Family Income',
  percentage: 'Academic Percentage',
  gender: 'Gender',
  father_name: "Father's Name",
  category: 'Social Category',
}

export function formatFieldName(name) {
  if (!name) return 'Unknown Field'
  return FIELD_NAME_LABELS[name] || name.replace(/_/g, ' ')
}

export function formatFieldValue(fieldName, value) {
  if (value === null || value === undefined || value === '') return '—'

  if (fieldName === 'income') {
    const num = Number(value)
    if (!isNaN(num)) {
      return `₹${num.toLocaleString('en-IN')}`
    }
  }

  if (fieldName === 'percentage') {
    const num = Number(value)
    if (!isNaN(num)) {
      return `${num}%`
    }
  }

  return String(value)
}

export function formatStatusLabel(status) {
  switch (status) {
    case 'READY_FOR_SUBMISSION':
      return 'Ready for Submission'
    case 'ACTION_REQUIRED':
      return 'Action Required'
    case 'IN_REVIEW':
      return 'Human Review Required'
    case 'INCOMPLETE':
      return 'Incomplete'
    default:
      return status || 'Pending'
  }
}

export function getStatusBadgeClass(status) {
  switch (status) {
    case 'READY_FOR_SUBMISSION':
      return 'badge-success'
    case 'ACTION_REQUIRED':
      return 'badge-danger'
    case 'IN_REVIEW':
      return 'badge-warning'
    case 'INCOMPLETE':
      return 'badge-neutral'
    default:
      return 'badge-neutral'
  }
}

export function formatVerificationStatus(status) {
  switch (status) {
    case 'VERIFIED':
      return 'Verified'
    case 'DOCUMENT_TYPE_MISMATCH':
      return 'Wrong Document Type'
    case 'UNKNOWN_DOCUMENT':
      return 'Unrecognized Document'
    case 'UNREADABLE':
      return 'Unreadable Document'
    default:
      return status || 'Pending'
  }
}

export function getVerificationStatusBadge(status) {
  switch (status) {
    case 'VERIFIED':
      return { label: 'Verified', className: 'tag-green', icon: '✓' }
    case 'DOCUMENT_TYPE_MISMATCH':
      return { label: 'Type Mismatch', className: 'tag-red', icon: '⚠' }
    case 'UNKNOWN_DOCUMENT':
      return { label: 'Unrecognized', className: 'tag-orange', icon: '?' }
    case 'UNREADABLE':
      return { label: 'Unreadable', className: 'tag-red', icon: '✕' }
    default:
      return { label: status || 'Pending', className: 'tag-neutral', icon: '•' }
  }
}

export function formatDateTime(isoString) {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoString
  }
}
