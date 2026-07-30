import { HashRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tickets from './pages/Tickets'
import TicketDetail from './pages/TicketDetail'
import AskAI from './pages/AskAI'
import AuditTrail from './pages/AuditTrail'
import Policies from './pages/Policies'
import Pipeline from './pages/Pipeline'
import PolicyDetail from './pages/PolicyDetail'
import Circulars from './pages/Circulars'
import Evaluation from './pages/Evaluation'
import './App.css'

function App() {
  return (
    <HashRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tickets" element={<Tickets />} />
          <Route path="/tickets/:ticketId" element={<TicketDetail />} />
          <Route path="/ask-ai" element={<AskAI />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/policies/:filename" element={<PolicyDetail />} />
          <Route path="/circulars" element={<Circulars />} />
          <Route path="/evaluation" element={<Evaluation />} />
        </Routes>
      </Layout>
    </HashRouter>
  )
}

export default App
