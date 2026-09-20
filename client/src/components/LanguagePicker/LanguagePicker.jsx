import { useState } from 'react'
import { useLanguage } from '../../context/LanguageContext'
import { Compass } from 'lucide-react'
import './LanguagePicker.css'

export default function LanguagePicker() {
  const { isPickerOpen, langCode, selectLanguage, languages, t } = useLanguage()
  const [tentativeLang, setTentativeLang] = useState(langCode)

  if (!isPickerOpen) return null

  const handleConfirm = () => {
    selectLanguage(tentativeLang)
  }

  return (
    <div
      className="lang-picker-backdrop"
      role="presentation"
      aria-modal="true"
    >
      <div
        className="lang-picker-dialog"
        role="dialog"
        aria-labelledby="lang-picker-title"
      >
        <div className="lang-picker-header">
          <span className="lang-picker-emblem" aria-hidden="true">
            <Compass size={28} strokeWidth={1.8} />
          </span>
          <div className="lang-picker-titles">
            <h2 id="lang-picker-title">{t.lpTitle || 'Select Your Language'}</h2>
            <p>{t.lpSubtitle || 'Choose your preferred language to use this portal'}</p>
          </div>
        </div>

        <div className="lang-picker-body">
          <p className="lang-picker-instruction">
            Please choose one of the 28 languages below. The interface will immediately update to your selection.
          </p>

          <div className="lang-grid-options" role="radiogroup" aria-label="Languages">
            {languages.map((item) => {
              const isSelected = item.code === tentativeLang
              return (
                <button
                  key={item.code}
                  type="button"
                  className={`lang-option-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setTentativeLang(item.code)}
                  role="radio"
                  aria-checked={isSelected}
                >
                  <span className="lang-card-native">{item.native}</span>
                  <span className="lang-card-english">{item.name}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="lang-picker-footer">
          <div className="lang-footer-info">
            Selected: <strong>{languages.find(l => l.code === tentativeLang)?.native}</strong> ({languages.find(l => l.code === tentativeLang)?.name})
          </div>
          <button
            type="button"
            className="lang-confirm-btn"
            onClick={handleConfirm}
          >
            {t.lpConfirm || 'Continue'} &rarr;
          </button>
        </div>
      </div>
    </div>
  )
}
