import React, { useState, useEffect } from 'react';
import './SystemStats.css';

type Stats = {
  users: {
    total: number;
    active: number;
    inactive: number;
  };
  documents: {
    total: number;
    completed: number;
    processing: number;
    failed: number;
    pending: number;
  };
  collections: {
    total: number;
    active: number;
    inactive: number;
  };
  conversations: {
    total: number;
  };
  timestamp: string;
};

type SystemStatsProps = {};

const SystemStats: React.FC<SystemStatsProps> = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/v1/admin/stats');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setStats(data);
      } catch (err) {
        console.error('Error fetching stats:', err);
        setError('Failed to load system statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="stats-loading">
        <div className="stats-spinner"></div>
        <p>Loading system statistics...</p>
      </div>
    );
  }

  if (error) {
    return <div className="stats-error">Error: {error}</div>;
  }

  if (!stats) {
    return <div className="stats-empty">No statistics available</div>;
  }

  return (
    <div className="system-stats">
      <div className="stats-header">
        <h3>System Statistics</h3>
        <p className="stats-timestamp">Last updated: {new Date(stats.timestamp).toLocaleString()}</p>
      </div>

      <div className="stats-grid">
        <div className="stats-card">
          <h4>Users</h4>
          <div className="stats-value">{stats.users.total}</div>
          <div className="stats-label">Total Users</div>
          <div className="stats-details">
            <span>{stats.users.active} active</span>
            <span>{stats.users.inactive} inactive</span>
          </div>
        </div>

        <div className="stats-card">
          <h4>Documents</h4>
          <div className="stats-value">{stats.documents.total}</div>
          <div className="stats-label">Total Documents</div>
          <div className="stats-details">
            <span>{stats.documents.completed} completed</span>
            <span>{stats.documents.processing} processing</span>
            <span>{stats.documents.failed} failed</span>
            <span>{stats.documents.pending} pending</span>
          </div>
        </div>

        <div className="stats-card">
          <h4>Collections</h4>
          <div className="stats-value">{stats.collections.total}</div>
          <div className="stats-label">Total Collections</div>
          <div className="stats-details">
            <span>{stats.collections.active} active</span>
            <span>{stats.collections.inactive} inactive</span>
          </div>
        </div>

        <div className="stats-card">
          <h4>Conversations</h4>
          <div className="stats-value">{stats.conversations.total}</div>
          <div className="stats-label">Total Conversations</div>
        </div>
      </div>
    </div>
  );
};

export default SystemStats;