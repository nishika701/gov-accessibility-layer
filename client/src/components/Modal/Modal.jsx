import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import './Modal.css'

/**
 * Modal
 *
 * Props:
 *   open        {boolean}   — whether the modal is visible
 *   type        {'success'|'error'}
 *   title       {string}    — header title text
 *   onClose     {function}  — called when user dismisses
 *   children    {ReactNode} — body content
 */
export default function Modal({ open, type = 'success', title, onClose, children }) {
  const dialogRef = useRef(null)

  /* Focus trap: move focus into dialog when it opens */
  useEffect(() => {
    if (open) {
      dialogRef.current?.focus()
    }
  }, [open])

  /* Close on Escape key */
  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  /* Prevent body scroll while modal is open */
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  const icons = { success: '✓', error: '⚠' }

  return createPortal(
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        ref={dialogRef}
        className="modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
      >
        {/* Header */}
        <div className={`modal-header type-${type}`}>
          <span className="modal-header-icon" aria-hidden="true">
            {icons[type]}
          </span>
          <span className="modal-header-title" id="modal-title">
            {title}
          </span>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">{children}</div>

        {/* Footer */}
        <div className="modal-footer">
          <button
            type="button"
            className="modal-btn-primary"
            onClick={onClose}
            autoFocus
          >
            {type === 'success' ? 'Done' : 'Close'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
