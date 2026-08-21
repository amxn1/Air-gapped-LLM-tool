import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import DocumentManagement from './pages/DocumentManagement';
import AdminDashboard from './pages/AdminDashboard';
import './index.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="app-navbar">
          <div className="navbar-brand">
            <div>
              <h1 className="brand-title">Offline LLM Assistant</h1>
              <span className="brand-subtitle">Enterprise Air-Gapped Intelligence</span>
            </div>
          </div>
        </header>

        <main className="app-main-content">
          <Routes>
            <Route path="/" element={<ChatInterface />} />
            <Route path="/documents" element={<DocumentManagement />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;