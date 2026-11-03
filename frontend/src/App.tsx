import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import IngestionDashboard from './components/IngestionDashboard'
import ChatPage from './components/ChatInterface'
import KnowledgeBrowser from './components/KnowledgeBrowser'
import EntityBrowser from './components/EntityBrowser'
import EvaluationDashboard from './components/EvaluationDashboard'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<IngestionDashboard />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/knowledge" element={<KnowledgeBrowser />} />
        <Route path="/entities" element={<EntityBrowser />} />
        <Route path="/evaluation" element={<EvaluationDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
