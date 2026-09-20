import { createContext, useContext, useState, useEffect } from 'react'
import TRANSLATIONS, { LANGUAGES } from '../locales'

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  // Default to English as requested
  const [langCode, setLangCode] = useState(() => {
    return localStorage.getItem('gov_selected_language') || 'en'
  })

  // Has the user seen and confirmed the startup popup?
  const [hasChosenLanguage, setHasChosenLanguage] = useState(() => {
    return !!localStorage.getItem('gov_language_chosen')
  })

  // Whether the language selection dialog is visible
  const [isPickerOpen, setIsPickerOpen] = useState(() => {
    return !localStorage.getItem('gov_language_chosen')
  })

  const currentLanguage = LANGUAGES.find((l) => l.code === langCode) || LANGUAGES[0]
  const t = TRANSLATIONS[langCode] || TRANSLATIONS['en']

  const selectLanguage = (code) => {
    setLangCode(code)
    localStorage.setItem('gov_selected_language', code)
    localStorage.setItem('gov_language_chosen', 'true')
    setHasChosenLanguage(true)
    setIsPickerOpen(false)
  }

  const openPicker = () => {
    setIsPickerOpen(true)
  }

  const closePicker = () => {
    setIsPickerOpen(false)
  }

  // Update HTML document direction and lang attributes when language changes
  useEffect(() => {
    if (currentLanguage) {
      document.documentElement.lang = currentLanguage.code
      document.documentElement.dir = currentLanguage.dir || 'ltr'
    }
  }, [currentLanguage])

  return (
    <LanguageContext.Provider
      value={{
        langCode,
        currentLanguage,
        t,
        selectLanguage,
        isPickerOpen,
        openPicker,
        closePicker,
        hasChosenLanguage,
        languages: LANGUAGES,
      }}
    >
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return ctx
}
