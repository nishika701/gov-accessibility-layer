import './App.css'
import { LanguageProvider } from './context/LanguageContext'
import Layout from './components/Layout/Layout'
import UploadPage from './components/UploadPage/UploadPage'
import LanguagePicker from './components/LanguagePicker/LanguagePicker'

function App() {
  return (
    <LanguageProvider>
      <LanguagePicker />
      <Layout>
        <UploadPage />
      </Layout>
    </LanguageProvider>
  )
}

export default App
