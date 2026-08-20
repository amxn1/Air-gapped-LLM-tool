import React, { useState } from 'react';
import UserManagement from '../components/admin/UserManagement';
import SystemStats from '../components/admin/SystemStats';
import RoleManagement from '../components/admin/RoleManagement';
import ModelRegistryManagement from '../components/admin/ModelRegistryManagement';
import AuditLogViewer from '../components/admin/AuditLogViewer';
import './AdminDashboard.css';

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'stats' | 'models' | 'users' | 'roles' | 'audit'>('stats');

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <h2>Administration & Infrastructure Center</h2>
        <nav className="admin-nav">
          <button
            className={activeTab === 'stats' ? 'active' : ''}
            onClick={() => setActiveTab('stats')}
          >
            System Overview
          </button>
          <button
            className={activeTab === 'models' ? 'active' : ''}
            onClick={() => setActiveTab('models')}
          >
            Model Registry & Lifecycle
          </button>
          <button
            className={activeTab === 'users' ? 'active' : ''}
            onClick={() => setActiveTab('users')}
          >
            User Accounts
          </button>
          <button
            className={activeTab === 'roles' ? 'active' : ''}
            onClick={() => setActiveTab('roles')}
          >
            Role Permissions
          </button>
          <button
            className={activeTab === 'audit' ? 'active' : ''}
            onClick={() => setActiveTab('audit')}
          >
            Security Audit Trail
          </button>
        </nav>
      </div>

      <div className="admin-content">
        {activeTab === 'stats' && <SystemStats />}
        {activeTab === 'models' && <ModelRegistryManagement />}
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'roles' && <RoleManagement />}
        {activeTab === 'audit' && <AuditLogViewer />}
      </div>
    </div>
  );
};

export default AdminDashboard;