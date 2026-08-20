import React, { useState, useEffect } from 'react';
import './RoleManagement.css';

type RoleInfo = {
  value: string;
  label: string;
  description: string;
};

type RoleManagementProps = {};

const RoleManagement: React.FC<RoleManagementProps> = () => {
  const [availableRoles, setAvailableRoles] = useState<RoleInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRoles = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/v1/admin/roles');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setAvailableRoles(data.roles);
      } catch (err) {
        console.error('Error fetching roles:', err);
        setError('Failed to load role information');
      } finally {
        setLoading(false);
      }
    };

    fetchRoles();
  }, []);

  if (loading) {
    return <div className="loading">Loading role information...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="role-management">
      <div className="rm-header">
        <h3>Roles & Permissions</h3>
        <p className="rm-description">
          Define and manage user roles and their permissions within the system.
        </p>
      </div>

      <div className="rm-roles-container">
        {availableRoles.map(role => (
          <div key={role.value} className="rm-role-card">
            <div className="rm-role-header">
              <h4>{role.label}</h4>
              <span className={`rm-role-badge rm-role-${role.value}`}>
                {role.value}
              </span>
            </div>
            <p className="rm-role-description">{role.description}</p>
            <div className="rm-role-permissions">
              <h5>Typical Permissions:</h5>
              <ul className="rm-permissions-list">
                {getPermissionsForRole(role.value).map(perm => (
                  <li key={perm}>{perm}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Helper function to get permissions for each role
const getPermissionsForRole = (role: string): string[] => {
  switch (role) {
    case 'admin':
      return [
        'Full system access',
        'Manage all users (create, edit, delete)',
        'Manage roles and permissions',
        'Access all documents and collections',
        'View system statistics and logs',
        'Configure system settings',
        'Manage AI models and configurations'
      ];
    case 'user':
      return [
        'Create and manage own documents',
        'Create and manage own collections',
        'Chat with AI models',
        'Use summarization features',
        'Upload and process files',
        'Access own conversation history'
      ];
    case 'collection_steward':
      return [
        'Manage collections (create, edit, delete)',
        'Assign documents to collections',
        'View all documents in managed collections',
        'Share collections with other users',
        'Set collection access policies',
        'Basic chat and summarization features'
      ];
    case 'viewer':
      return [
        'View documents in shared collections',
        'View conversation history (if shared)',
        'Basic chat functionality',
        'No upload or modification permissions'
      ];
    default:
      return ['Standard user permissions'];
  }
};

export default RoleManagement;