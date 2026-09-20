import './Layout.css'
import { useLanguage } from '../../context/LanguageContext'
import { Globe, Compass } from 'lucide-react'

/**
 * Layout
 * Official government layout with tricolour accent, header, navigation,
 * language switcher button, breadcrumbs, and official footer.
 * No internal technical details or API endpoints are exposed.
 */
export default function Layout({ children }) {
  const { t, currentLanguage, openPicker } = useLanguage()

  return (
    <>
      {/* Indian tricolour accent bar */}
      <div className="tricolour-bar" aria-hidden="true" />

      {/* ── Official Site Header ───────────────────────────────── */}
      <header className="site-header" role="banner">
        <div className="header-top">
          <span className="header-emblem" aria-hidden="true">
            <Compass size={28} strokeWidth={1.8} />
          </span>
          <div className="header-titles">
            <p className="ministry">{t.ministry}</p>
            <h1>{t.projectName}</h1>
            <p className="tagline">{t.tagline}</p>
          </div>
          <div className="header-actions">
            <button
              type="button"
              className="lang-switcher-btn"
              onClick={openPicker}
              title={t.changeLanguage}
              aria-label={t.changeLanguage}
            >
              <Globe size={16} aria-hidden="true" />
              <span>{currentLanguage?.native || 'Language'}</span>
            </button>
          </div>
        </div>


        {/* ── Official Navigation ─────────────────────────────── */}
        <nav className="site-nav" aria-label="Main navigation">
          <ul>
            <li>
              <a href="#" className="active" onClick={(e) => e.preventDefault()}>
                {t.navHome}
              </a>
            </li>
            <li>
              <button
                type="button"
                className="nav-btn-link"
                onClick={openPicker}
              >
                {t.changeLanguage}
              </button>
            </li>
          </ul>
        </nav>
      </header>

      {/* ── Breadcrumb Bar ──────────────────────────────────── */}
      <div className="breadcrumb-bar">
        <ol className="breadcrumb" aria-label="Breadcrumb">
          <li>
            <a href="#" onClick={(e) => e.preventDefault()}>{t.bcHome}</a>
          </li>
          <li>{t.bcUpload}</li>
        </ol>
      </div>

      {/* ── Main Page Content ────────────────────────────────── */}
      <div className="page-wrapper">{children}</div>

      {/* ── Official Footer ─────────────────────────────────── */}
      <footer className="site-footer" role="contentinfo">
        <p>
          <strong>{t.footerLine1}</strong>
        </p>
        <p>{t.footerLine2}</p>
      </footer>
    </>
  )
}
