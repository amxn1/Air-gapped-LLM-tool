import React, { useState, useEffect } from 'react';
import './AuditLogViewer.css';

interface AuditEvent {
  id: number;
  actor_id?: number;
  action: string;
  object_type?: string;
  object_id?: string;
  result?: string;
  timestamp: string;
  request_id?: string;
  details?: string;
}

const AuditLogViewer: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterAction, setFilterAction] = useState('');

  const fetchEvents = async () => {
    setLoading(true);
    try {
      let url = 'http://localhost:8000/v1/admin/audit/events?limit=100';
      if (filterAction) {
        url += `&action=${encodeURIComponent(filterAction)}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEvents(data);
      }
    } catch (e) {
      console.error('Failed to load audit events:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [filterAction]);

  return (
    <div className="audit-viewer">
      <div className="audit-header">
        <div>
          <h3>Immutable Security & Access Audit Log</h3>
          <p className="subtitle">Append-only operational record of all queries, file uploads, and model switches.</p>
        </div>
        <div className="audit-controls">
          <input
            type="text"
            placeholder="Filter action (e.g. POST /v1/chat)"
            value={filterAction}
            onChange={e => setFilterAction(e.target.value)}
          />
          <button className="btn-secondary" onClick={fetchEvents}>Refresh</button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading audit trail...</div>
      ) : events.length === 0 ? (
        <div className="empty-state">No audit events recorded matching filter.</div>
      ) : (
        <div className="audit-table-wrapper">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Result</th>
                <th>Request ID</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map(ev => (
                <tr key={ev.id}>
                  <td className="timestamp-cell">
                    {new Date(ev.timestamp).toLocaleString()}
                  </td>
                  <td><code className="action-code">{ev.action}</code></td>
                  <td>
                    <span className={`pill ${ev.result === 'success' ? 'pill-success' : 'pill-failure'}`}>
                      {ev.result || 'recorded'}
                    </span>
                  </td>
                  <td className="reqid-cell">{ev.request_id ? ev.request_id.slice(0, 8) : '-'}</td>
                  <td className="details-cell">
                    {ev.details ? (
                      <span title={ev.details}>{ev.details.slice(0, 60)}...</span>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AuditLogViewer;
