import { useCallback, useRef, useState, useEffect } from 'react'
import Modal from '../Modal/Modal'
import { useLanguage } from '../../context/LanguageContext'
import {
  FileText,
  FolderUp,
  Paperclip,
  Lightbulb,
  Mic,
  Square,
  Volume2,
  Play,
  Pause,
  User,
  Landmark,
  X,
  AlertTriangle,
  Zap,
  CheckCircle2,
} from 'lucide-react'
import './UploadPage.css'

/* ─────────────────────────────────────────────────────────────────────────────
   Validation constants
   ───────────────────────────────────────────────────────────────────────────── */
const ALLOWED_TYPES  = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
const ALLOWED_EXTS   = ['.pdf', '.jpg', '.jpeg', '.png', '.tif', '.tiff']
const MAX_SIZE_MB    = 10
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

/* ─────────────────────────────────────────────────────────────────────────────
   Helpers
   ───────────────────────────────────────────────────────────────────────────── */
function formatBytes(bytes) {
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1024 ** 2)  return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 ** 2).toFixed(2)} MB`
}

/* ─────────────────────────────────────────────────────────────────────────────
   ValidationMessage sub-component
   ───────────────────────────────────────────────────────────────────────────── */
function ValidationMessage({ result }) {
  if (!result) return null

  const icons = {
    error: <AlertTriangle size={16} strokeWidth={2} />,
    warning: <Zap size={16} strokeWidth={2} />,
    success: <CheckCircle2 size={16} strokeWidth={2} />,
  }
  const cls   = { error: 'is-error', warning: 'is-warning', success: 'is-success' }

  return (
    <div className={`validation-msg ${cls[result.level]}`} role="alert" aria-live="polite">
      <span className="msg-icon" aria-hidden="true">{icons[result.level]}</span>
      <span>{result.message}</span>
    </div>
  )
}


/* ─────────────────────────────────────────────────────────────────────────────
   Sidebar — Official Instructions & Service Status
   ───────────────────────────────────────────────────────────────────────────── */
function Sidebar({ t }) {
  return (
    <aside aria-label="Help and information">
      {/* Instructions */}
      <div className="sidebar-card">
        <div className="sidebar-card-header">{t.sidebarInstTitle}</div>
        <div className="sidebar-card-body">
          <ul>
            <li>{t.inst1}</li>
            <li>{t.inst2}</li>
            <li>{t.inst3}</li>
            <li>{t.inst4}</li>
            <li>{t.inst5}</li>
          </ul>
        </div>
      </div>

      {/* Accepted file types */}
      <div className="sidebar-card">
        <div className="sidebar-card-header">{t.sidebarFtTitle}</div>
        <div className="sidebar-card-body">
          <ul>
            <li>{t.ft1}</li>
            <li>{t.ft2}</li>
            <li>{t.ft3}</li>
            <li>{t.ft4}</li>
          </ul>
        </div>
      </div>
    </aside>
  )
}


/* ─────────────────────────────────────────────────────────────────────────────
   Main UploadPage component
   ───────────────────────────────────────────────────────────────────────────── */
export default function UploadPage() {
  const { t, languages, currentLanguage } = useLanguage()

  const [file, setFile]             = useState(null)
  const [validation, setValidation] = useState(null)
  const [targetLangName, setTargetLangName] = useState(currentLanguage?.name || 'English')
  const [dragOver, setDragOver]     = useState(false)
  const [uploading, setUploading]   = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [modalOpen, setModalOpen]   = useState(false)

  // Sync selected target language with the application language
  useEffect(() => {
    if (currentLanguage?.name) {
      setTargetLangName(currentLanguage.name)
    }
  }, [currentLanguage])

  // Extracted text & audio state from /process
  const [extractedText, setExtractedText] = useState('')
  const [audioUrl, setAudioUrl]           = useState(null)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [toasts, setToasts]               = useState([])

  // Voice Query (AWS Transcribe & Gemini Q&A)
  const [isRecording, setIsRecording]     = useState(false)
  const [voiceProcessing, setVoiceProcessing] = useState(false)
  const [voiceQuery, setVoiceQuery]       = useState(null) // { question, answer, source }

  const inputRef = useRef(null)
  const audioPlayerRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])


  const showToast = useCallback((msg, type = 'error') => {
    const id = Date.now() + Math.random().toString(36).slice(2, 6)
    setToasts((prev) => [...prev, { id, message: msg, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id))
    }, 5000)
  }, [])

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }


  /**
   * Play audio given a base64 string or URL
   */
  const playAudio = useCallback((base64Data, mime = 'audio/mp3') => {
    if (!base64Data) return
    try {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
        audioPlayerRef.current = null
      }
      const sound = new Audio(`data:${mime};base64,${base64Data}`)
      audioPlayerRef.current = sound
      setIsPlayingAudio(true)

      sound.onended = () => {
        setIsPlayingAudio(false)
      }
      sound.onerror = (e) => {
        console.warn('Audio playback error:', e)
        setIsPlayingAudio(false)
      }

      const playPromise = sound.play()
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.warn('Auto-play was prevented by browser policy, user can click play manually:', err)
          setIsPlayingAudio(false)
        })
      }
    } catch (err) {
      console.warn('Audio initialization error:', err)
      setIsPlayingAudio(false)
    }
  }, [])

  /**
   * Validate a File object with localized messages
   */
  const validateFile = useCallback((f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()

    if (!ALLOWED_TYPES.includes(f.type) && !ALLOWED_EXTS.includes(ext)) {
      return {
        valid: false,
        level: 'error',
        message: t.valInvalidType,
      }
    }

    if (f.size === 0) {
      return { valid: false, level: 'error', message: t.valEmpty }
    }

    if (f.size > MAX_SIZE_BYTES) {
      return {
        valid: false,
        level: 'error',
        message: t.valTooLarge,
      }
    }

    if (f.size > 5 * 1024 * 1024) {
      return {
        valid: true,
        level: 'warning',
        message: t.valLargeWarn,
      }
    }

    return { valid: true, level: 'success', message: t.valReady }
  }, [t])

  /* ── File selection handler ─────────────────────────────────────────────── */
  const handleFileSelect = useCallback((selectedFile) => {
    if (!selectedFile) return
    setUploadResult(null)
    setExtractedText('')
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current = null
      setIsPlayingAudio(false)
    }
    const result = validateFile(selectedFile)
    setValidation(result)
    if (result.valid) {
      setFile(selectedFile)
    } else {
      setFile(null)
    }
  }, [validateFile])

  /* ── Input change ───────────────────────────────────────────────────────── */
  const onInputChange = (e) => {
    const f = e.target.files?.[0]
    if (f) handleFileSelect(f)
  }

  /* ── Drag-and-drop ──────────────────────────────────────────────────────── */
  const onDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const onDragLeave = () => setDragOver(false)

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFileSelect(f)
  }

  /* ── Remove file ────────────────────────────────────────────────────────── */
  const removeFile = () => {
    setFile(null)
    setValidation(null)
    setUploadResult(null)
    setExtractedText('')
    setAudioUrl(null)
    setVoiceQuery(null)
    if (mediaRecorderRef.current && isRecording) {
      try {
        mediaRecorderRef.current.stop()
      } catch (e) {
        // ignore
      }
    }
    setIsRecording(false)
    setVoiceProcessing(false)
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current = null
      setIsPlayingAudio(false)
    }
    setModalOpen(false)
    if (inputRef.current) inputRef.current.value = ''
  }

  /* ── Reset form ─────────────────────────────────────────────────────────── */
  const resetForm = () => {
    removeFile()
    setTargetLangName(currentLanguage?.name || 'English')
  }

  /* ── Voice Query (Microphone & AWS Transcribe) Handlers ─────────────────── */
  const startRecording = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('Your browser does not support audio recording.', 'error')
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      audioChunksRef.current = []

      // Choose mime type supported by browser
      let mimeType = 'audio/webm'
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4'
        } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
          mimeType = 'audio/ogg'
        }
      }

      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        // Stop all audio tracks to release microphone
        stream.getTracks().forEach((track) => track.stop())
        const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || 'audio/webm' })
        sendVoiceQuery(audioBlob)
      }

      mediaRecorder.start()
      setIsRecording(true)
      showToast('Microphone activated. Please speak your question clearly.', 'success')
    } catch (err) {
      console.error('Microphone access denied or error:', err)
      showToast('Microphone access was denied or is unavailable. Please grant microphone permission.', 'error')
      setIsRecording(false)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const sendVoiceQuery = async (audioBlob) => {
    if (!audioBlob || audioBlob.size === 0) {
      showToast('No audio was recorded.', 'error')
      return
    }

    setVoiceProcessing(true)
    showToast('Transcribing your question with AWS Transcribe...', 'info')

    try {
      const formData = new FormData()
      const ext = audioBlob.type.includes('ogg') ? 'ogg' : audioBlob.type.includes('mp4') ? 'mp4' : 'webm'
      formData.append('file', audioBlob, `voice_question.${ext}`)
      formData.append('document_context', extractedText)
      formData.append('language', targetLangName)

      const response = await fetch('/api/ask-voice', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok || data.status !== 'success') {
        const errorDetail = data?.detail || 'Failed to process voice query.'
        showToast(errorDetail, 'error')
        return
      }

      setVoiceQuery({
        question: data.question || '',
        answer: data.answer || '',
        audioBase64: data.audio_base64 || null,
        audioFormat: data.audio_format || 'audio/mp3',
        source: data.transcribe_source || 'aws_transcribe',
      })

      // Auto-play the AI answer audio as soon as rendered (identical to /explain audio)
      if (data.audio_base64) {
        playAudio(data.audio_base64, data.audio_format || 'audio/mp3')
      }

      showToast('Question answered successfully!', 'success')
    } catch (err) {
      console.error('Voice query error:', err)
      showToast(err.message || 'Error processing your voice question.', 'error')
    } finally {

      setVoiceProcessing(false)
    }
  }



  /* ── Submit & Process Pipeline ─────────────────────────────────────────── */
  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!file) {
      setValidation({ valid: false, level: 'error', message: t.valRequired })
      showToast(t.valRequired, 'error')
      return
    }

    if (validation && !validation.valid) {
      showToast(validation.message || 'Please select a valid document.', 'error')
      return
    }

    setUploading(true)
    setUploadResult(null)
    setExtractedText('')
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current = null
      setIsPlayingAudio(false)
    }

    try {
      // Step 1: Upload document to /api/upload
      const formData = new FormData()
      formData.append('file', file)
      const uploadResponse = await fetch(`/api/upload?language=${encodeURIComponent(targetLangName)}`, {
        method: 'POST',
        body: formData,
      })

      const uploadData = await uploadResponse.json()

      if (!uploadResponse.ok) {
        throw new Error(uploadData?.detail || `Upload failed with status code ${uploadResponse.status}`)
      }

      // Step 2: Request the python backend endpoint /process to extract text
      const processPayload = {
        key: uploadData.key || uploadData.filename,
        bucket: uploadData.bucket,
        s3_uri: uploadData.s3_uri,
        document_id: uploadData.key || uploadData.filename,
      }

      const processResponse = await fetch('/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(processPayload),
      })

      const processData = await processResponse.json()

      if (!processResponse.ok || processData.status !== 'success') {
        const errorDetail = processData?.detail || 'Document processing failed on the server.'
        showToast(errorDetail, 'error')
        return
      }

      const extractedDocumentText = processData.text || ''

      if (!extractedDocumentText.trim()) {
        showToast('No text could be extracted from the document to explain.', 'error')
        return
      }

      // Step 3: Request the python backend endpoint /explain with the extracted text & selected language
      const explainPayload = {
        text: extractedDocumentText,
        language: targetLangName,
      }

      const explainResponse = await fetch('/api/explain', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(explainPayload),
      })

      const explainData = await explainResponse.json()

      if (!explainResponse.ok || explainData.status !== 'success') {
        const errorDetail = explainData?.detail || 'Failed to generate explanation from the server.'
        showToast(errorDetail, 'error')
        return
      }

      // Render only the explanation text returned by /explain
      const explanationResult = explainData.simplified_text || ''
      setExtractedText(explanationResult)

      // Play the audio received from /explain immediately as soon as the explanation is rendered
      if (explainData.audio_base64) {
        setAudioUrl(explainData.audio_base64)
        playAudio(explainData.audio_base64, explainData.audio_format || 'audio/mp3')
      } else {
        setAudioUrl(null)
      }

      showToast('Document explained successfully!', 'success')
    } catch (err) {
      const msg = err.message || 'An unexpected error occurred during processing.'
      showToast(msg, 'error')
    } finally {
      setUploading(false)
    }
  }

  /* ── Derive drop zone class ─────────────────────────────────────────────── */
  let dropZoneClass = 'drop-zone'
  if (dragOver)                                           dropZoneClass += ' drag-over'
  else if (file)                                          dropZoneClass += ' has-file'
  else if (validation && !validation.valid)               dropZoneClass += ' error'

  /* ── Render ─────────────────────────────────────────────────────────────── */
  return (
    <>
      {/* Main content column */}
      <main id="main-content">
        <h2 className="page-section-title">
          {t.pageTitle}
          <small>{t.pageSubtitle}</small>
        </h2>

        <form
          onSubmit={handleSubmit}
          noValidate
          aria-label="Document upload form"
        >
          <div className="form-panel">
            {/* Panel header */}
            <div className="form-panel-header">
              <span className="panel-icon" aria-hidden="true">
                <FileText size={18} />
              </span>
              {t.formHeader}
            </div>

            <div className="form-panel-body">
              {/* Info notice */}
              <div className="info-notice" role="note">
                {t.notice}
              </div>

              {/* ── Drop zone ─────────────────────────────────────────────── */}
              <div
                className={dropZoneClass}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                role="button"
                tabIndex={0}
                aria-label={t.dzLabel}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
              >
                <input
                  ref={inputRef}
                  type="file"
                  id="file-upload-input"
                  accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff"
                  onChange={onInputChange}
                  aria-describedby="file-upload-hint"
                  tabIndex={-1}
                />

                <span className="drop-zone-icon" aria-hidden="true">
                  {file ? <FileText size={42} strokeWidth={1.5} /> : <FolderUp size={42} strokeWidth={1.5} />}
                </span>

                {file ? (
                  <>
                    <p className="drop-zone-label">{t.dzSelected}</p>
                    <p className="drop-zone-sub" id="file-upload-hint">
                      {t.dzReplace}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="drop-zone-label">
                      {t.dzLabel}
                    </p>
                    <p className="drop-zone-sub" id="file-upload-hint">
                      {t.dzSub}
                    </p>
                  </>
                )}
              </div>

              {/* Selected file info row */}
              {file && (
                <div className="file-info-row" aria-label="Selected file details">
                  <span className="file-icon" aria-hidden="true">
                    <Paperclip size={18} />
                  </span>
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">{formatBytes(file.size)}</span>
                  <button
                    type="button"
                    className="file-remove-btn"
                    onClick={removeFile}
                    aria-label={`${t.removeFile}: ${file.name}`}
                    title={t.removeFile}
                  >
                    <X size={16} strokeWidth={2} />
                  </button>
                </div>
              )}


              {/* Validation feedback */}
              <ValidationMessage result={validation} />

              {/* ── Output Language selector ───────────────────────────────── */}
              <div className="form-group">
                <label htmlFor="language-select">
                  {t.langLabel}
                  <span className="required-mark" aria-hidden="true">*</span>
                </label>
                <select
                  id="language-select"
                  value={targetLangName}
                  onChange={(e) => setTargetLangName(e.target.value)}
                  required
                  aria-required="true"
                >
                  {languages.map((l) => (
                    <option key={l.code} value={l.name}>
                      {l.native} — {l.name}
                    </option>
                  ))}
                </select>
                <p className="field-hint">
                  {t.langHint}
                </p>
              </div>

              {/* ── Action buttons ─────────────────────────────────────────── */}
              <div className="form-actions">
                <button
                  type="submit"
                  className="btn-submit"
                  disabled={uploading || !file || (validation && !validation.valid)}
                  aria-busy={uploading}
                >
                  {uploading && <span className="spinner" aria-hidden="true" />}
                  {uploading ? t.btnUploading : t.btnSubmit}
                </button>

                <button
                  type="button"
                  className="btn-reset"
                  onClick={resetForm}
                  disabled={uploading}
                >
                  {t.btnReset}
                </button>

                {uploading && (
                  <span
                    role="status"
                    aria-live="polite"
                    style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}
                  >
                    {t.uploadWait}
                  </span>
                )}
              </div>

            </div>
          </div>
        </form>

        {/* ── Render Only Explanation Result from /explain with Polly Audio ── */}
        {extractedText && (
          <section
            className="extracted-text-section"
            aria-label="Document Explanation Content"
          >
            <div className="extracted-text-header">
              <div className="extracted-text-title">
                <Lightbulb size={18} className="text-amber-400" aria-hidden="true" />
                <span>Document Explanation</span>
              </div>
              {audioUrl && (
                <div className="audio-controls-group">
                  {isPlayingAudio && (
                    <span className="audio-playing-indicator" aria-live="polite">
                      <Volume2 size={15} aria-hidden="true" style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                      Playing Audio…
                    </span>
                  )}
                  <button
                    type="button"
                    className="btn-audio-action"
                    onClick={() => {
                      if (isPlayingAudio && audioPlayerRef.current) {
                        audioPlayerRef.current.pause()
                        setIsPlayingAudio(false)
                      } else {
                        playAudio(audioUrl)
                      }
                    }}
                    title={isPlayingAudio ? "Pause Audio" : "Listen to Audio"}
                    aria-label={isPlayingAudio ? "Pause Audio" : "Listen to Audio"}
                  >
                    {isPlayingAudio ? (
                      <>
                        <Pause size={14} aria-hidden="true" />
                        <span>Pause</span>
                      </>
                    ) : (
                      <>
                        <Play size={14} aria-hidden="true" />
                        <span>Listen</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
            <div className="extracted-text-body">
              <div className="rendered-document-content" tabIndex={0}>
                {extractedText}
              </div>
            </div>

            {/* ── Citizen Voice Assistant Section (AWS Transcribe + AI) ── */}
            <div className="voice-assistant-section">
              <div className="voice-assistant-header">
                <span className="voice-header-icon" aria-hidden="true">
                  <Mic size={22} />
                </span>
                <div>
                  <h3 className="voice-assistant-title">Ask a Question by Voice</h3>
                  <p className="voice-assistant-subtitle">
                    Click the microphone at the bottom to ask your question. Amazon Transcribe converts your speech to text and AI provides the answer.
                  </p>
                </div>
              </div>

              {/* Conversation Display (Goes up above the microphone button) */}
              {voiceQuery && (
                <div className="voice-qa-card" role="region" aria-label="Voice Query Conversation">
                  <div className="qa-bubble user-question">
                    <div className="qa-label">
                      <User size={14} aria-hidden="true" />
                      <span>Your Question (Transcribed)</span>
                    </div>
                    <div className="qa-text">"{voiceQuery.question}"</div>
                  </div>

                  <div className="qa-bubble ai-answer">
                    <div className="qa-label-row">
                      <div className="qa-label">
                        <Landmark size={14} aria-hidden="true" />
                        <span>Official Assistant Answer</span>
                      </div>
                      {voiceQuery.audioBase64 && (
                        <button
                          type="button"
                          className="btn-voice-audio-play"
                          onClick={() => {
                            if (isPlayingAudio && audioPlayerRef.current) {
                              audioPlayerRef.current.pause()
                              setIsPlayingAudio(false)
                            } else {
                              playAudio(voiceQuery.audioBase64, voiceQuery.audioFormat || 'audio/mp3')
                            }
                          }}
                          aria-label={isPlayingAudio ? "Pause answer audio" : "Listen to answer audio"}
                          title={isPlayingAudio ? "Pause Audio" : "Listen to Audio"}
                        >
                          {isPlayingAudio ? (
                            <>
                              <Pause size={12} aria-hidden="true" />
                              <span>Pause</span>
                            </>
                          ) : (
                            <>
                              <Play size={12} aria-hidden="true" />
                              <span>Listen</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                    <div className="qa-text">{voiceQuery.answer}</div>
                  </div>
                </div>
              )}

              {voiceProcessing && (
                <div className="voice-processing-status" role="status" aria-live="polite">
                  <span className="spinner" aria-hidden="true" />
                  <span>Transcribing with Amazon Transcribe and generating answer...</span>
                </div>
              )}

              {/* Microphone Button at the last / bottom */}
              <div className="voice-mic-container">
                {!isRecording ? (
                  <button
                    type="button"
                    className={`btn-voice-mic ${voiceProcessing ? 'loading' : ''}`}
                    onClick={startRecording}
                    disabled={voiceProcessing}
                    aria-label="Click to start speaking your question"
                  >
                    <span className="mic-icon" aria-hidden="true">
                      <Mic size={18} />
                    </span>
                    <span>{voiceProcessing ? 'Processing Speech...' : 'Click to Ask by Voice'}</span>
                  </button>
                ) : (
                  <div className="recording-controls">
                    <button
                      type="button"
                      className="btn-voice-mic is-recording"
                      onClick={stopRecording}
                      aria-label="Stop recording and get answer"
                    >
                      <span className="recording-pulse" aria-hidden="true" />
                      <span className="mic-icon" aria-hidden="true">
                        <Square size={16} fill="currentColor" />
                      </span>
                      <span>Listening... Click to Submit Question</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      {/* Sidebar */}
      <Sidebar t={t} />

      {/* ── Toast Notifications ─────────────────────────────────────────── */}
      {toasts.length > 0 && (
        <div className="toast-container" aria-live="polite">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`toast-message toast-${toast.type}`}
              role="alert"
            >
              <span>{toast.message}</span>
              <button
                type="button"
                className="toast-close-btn"
                onClick={() => removeToast(toast.id)}
                aria-label="Close notification"
              >
                <X size={14} strokeWidth={2} />
              </button>
            </div>
          ))}
        </div>
      )}

    </>
  )
}
