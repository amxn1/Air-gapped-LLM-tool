import React, { useState, useEffect } from 'react';
import './ModelRegistryManagement.css';

interface ModelProfile {
  id: number;
  model_name: string;
  version: string;
  format: string;
  quantization: string;
  context_length: number;
  max_output: number;
  hardware_profile: string;
  checksum?: string;
  status: string;
}

const ModelRegistryManagement: React.FC = () => {
  const [models, setModels] = useState<ModelProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ [key: number]: any }>({});
  
  // Staging modal / form state
  const [showStageModal, setShowStageModal] = useState(false);
  const [formName, setFormName] = useState('');
  const [formVersion, setFormVersion] = useState('1.0');
  const [formFormat, setFormFormat] = useState('GGUF');
  const [formQuant, setFormQuant] = useState('q4_0');
  const [formHardware, setFormHardware] = useState('CPU/GPU');
  const [formChecksum, setFormChecksum] = useState('');

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/v1/models');
      if (res.ok) {
        const data = await res.json();
        setModels(data);
      }
    } catch (e) {
      console.error('Failed to fetch models:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleActivate = async (id: number) => {
    try {
      const res = await fetch(`http://localhost:8000/v1/models/${id}/activate`, {
        method: 'POST',
      });
      if (res.ok) {
        setMessage(`Model #${id} successfully activated.`);
        fetchModels();
      }
    } catch (e) {
      setMessage(`Failed to activate model #${id}`);
    }
  };

  const handleRollback = async (id: number) => {
    try {
      const res = await fetch(`http://localhost:8000/v1/models/${id}/rollback`, {
        method: 'POST',
      });
      if (res.ok) {
        setMessage(`Rolled back from model #${id}.`);
        fetchModels();
      }
    } catch (e) {
      setMessage(`Failed rollback on model #${id}`);
    }
  };

  const handleSmokeTest = async (id: number) => {
    try {
      setTestResult(prev => ({ ...prev, [id]: { status: 'testing...' } }));
      const res = await fetch(`http://localhost:8000/v1/models/${id}/test`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setTestResult(prev => ({ ...prev, [id]: data }));
      }
    } catch (e) {
      setTestResult(prev => ({ ...prev, [id]: { status: 'failed', error: String(e) } }));
    }
  };

  const handleStageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:8000/v1/models/stage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_name: formName,
          version: formVersion,
          format: formFormat,
          quantization: formQuant,
          hardware_profile: formHardware,
          checksum: formChecksum || undefined,
          context_length: 4096,
          max_output: 1024,
        }),
      });
      if (res.ok) {
        setShowStageModal(false);
        setFormName('');
        setMessage(`New model staged successfully.`);
        fetchModels();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="model-registry">
      <div className="registry-header">
        <div>
          <h3>Approved Model Registry & Lifecycle</h3>
          <p className="subtitle">Manage staged, active, and deprecated offline LLM profiles.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowStageModal(true)}>
          + Stage Approved Model
        </button>
      </div>

      {message && <div className="status-toast">{message}</div>}

      {loading ? (
        <div className="loading-state">Loading model profiles...</div>
      ) : (
        <div className="models-grid">
          {models.map(m => (
            <div key={m.id} className={`model-card ${m.status === 'active' ? 'active-model' : ''}`}>
              <div className="model-card-header">
                <span className="model-name">{m.model_name}</span>
                <span className={`status-badge status-${m.status}`}>{m.status.toUpperCase()}</span>
              </div>
              <div className="model-meta">
                <div><strong>Version:</strong> {m.version}</div>
                <div><strong>Format:</strong> {m.format} ({m.quantization})</div>
                <div><strong>Hardware Profile:</strong> {m.hardware_profile}</div>
                <div><strong>Context Limit:</strong> {m.context_length} tokens</div>
              </div>

              {testResult[m.id] && (
                <div className="test-diagnostic">
                  <strong>Diagnostic:</strong> {testResult[m.id].status} ({testResult[m.id].latency_ms}ms)
                </div>
              )}

              <div className="model-card-actions">
                <button
                  className="btn-secondary"
                  onClick={() => handleSmokeTest(m.id)}
                >
                  Run Smoke Test
                </button>
                {m.status !== 'active' ? (
                  <button
                    className="btn-activate"
                    onClick={() => handleActivate(m.id)}
                  >
                    Activate Profile
                  </button>
                ) : (
                  <button
                    className="btn-rollback"
                    onClick={() => handleRollback(m.id)}
                  >
                    Rollback Predecessor
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showStageModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h4>Stage New Offline Model Profile</h4>
            <form onSubmit={handleStageSubmit}>
              <label>Model Name / Family:</label>
              <input required value={formName} onChange={e => setFormName(e.target.value)} placeholder="e.g. Llama-3-8B-Instruct" />

              <label>Version:</label>
              <input required value={formVersion} onChange={e => setFormVersion(e.target.value)} />

              <label>Format:</label>
              <select value={formFormat} onChange={e => setFormFormat(e.target.value)}>
                <option value="GGUF">GGUF</option>
                <option value="Safetensors">Safetensors</option>
              </select>

              <label>Quantization:</label>
              <input value={formQuant} onChange={e => setFormQuant(e.target.value)} placeholder="q4_k_m, q8_0, fp16" />

              <label>Hardware Profile:</label>
              <input value={formHardware} onChange={e => setFormHardware(e.target.value)} placeholder="CPU, Single-GPU 16GB, Multi-GPU" />

              <label>SHA-256 Checksum:</label>
              <input value={formChecksum} onChange={e => setFormChecksum(e.target.value)} placeholder="Verified file checksum" />

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowStageModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Confirm Staging</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelRegistryManagement;
