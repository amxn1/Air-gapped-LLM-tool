import React, { useState, useEffect } from 'react';
import './UserManagement.css';

type User = {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  role: string;
  created_at: string;
};

type UserManagementProps = {};

const UserManagement: React.FC<UserManagementProps> = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [userForm, setUserForm] = useState<Partial<User>>({});

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/v1/admin/users');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setUsers(data);
      } catch (err) {
        console.error('Error fetching users:', err);
        setError('Failed to load users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleEdit = (user: User) => {
    setEditingUserId(user.id);
    setUserForm({
      username: user.username,
      email: user.email,
      full_name: user.full_name || '',
      is_active: user.is_active,
      role: user.role
    });
  };

  const handleCancelEdit = () => {
    setEditingUserId(null);
    setUserForm({});
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUserId) return;

    try {
      const response = await fetch(`http://localhost:8000/v1/admin/users/${editingUserId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userForm),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Refresh the user list
      const usersResponse = await fetch('http://localhost:8000/v1/admin/users');
      if (usersResponse.ok) {
        const data = await usersResponse.json();
        setUsers(data);
      }

      setEditingUserId(null);
      setUserForm({});
    } catch (err) {
      console.error('Error updating user:', err);
      setError('Failed to update user');
    }
  };

  const handleToggleStatus = async (userId: number) => {
    try {
      // First get the current user to toggle the status
      const user = users.find(u => u.id === userId);
      if (!user) return;

      const response = await fetch(`http://localhost:8000/v1/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_active: !user.is_active
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Refresh the user list
      const usersResponse = await fetch('http://localhost:8000/v1/admin/users');
      if (usersResponse.ok) {
        const data = await usersResponse.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Error toggling user status:', err);
      setError('Failed to update user status');
    }
  };

  const handleDelete = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/v1/admin/users/${userId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Refresh the user list
      const usersResponse = await fetch('http://localhost:8000/v1/admin/users');
      if (usersResponse.ok) {
        const data = await usersResponse.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      setError('Failed to delete user');
    }
  };

  if (loading) {
    return <div className="loading">Loading users...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="user-management">
      <div className="um-header">
        <h3>User Management</h3>
        <button className="um-add-button" onClick={() => {
          setEditingUserId(0); // Special ID to indicate new user
          setUserForm({
            username: '',
            email: '',
            full_name: '',
            is_active: true,
            role: 'user'
          });
        }}>
          Add New User
        </button>
      </div>

      {editingUserId !== null && (
        <div className="um-form">
          <h4>{editingUserId === 0 ? 'Add New User' : 'Edit User'}</h4>
          <form onSubmit={handleSaveEdit}>
            <div className="um-field">
              <label>Username:</label>
              <input
                type="text"
                value={userForm.username || ''}
                onChange={(e) => setUserForm(prev => ({ ...prev, username: e.target.value }))}
                required
              />
            </div>
            <div className="um-field">
              <label>Email:</label>
              <input
                type="email"
                value={userForm.email || ''}
                onChange={(e) => setUserForm(prev => ({ ...prev, email: e.target.value }))}
                required
              />
            </div>
            <div className="um-field">
              <label>Full Name:</label>
              <input
                type="text"
                value={userForm.full_name || ''}
                onChange={(e) => setUserForm(prev => ({ ...prev, full_name: e.target.value }))}
              />
            </div>
            <div className="um-field">
              <label>Role:</label>
              <select
                value={userForm.role || 'user'}
                onChange={(e) => setUserForm(prev => ({ ...prev, role: e.target.value }))}
              >
                <option value="admin">Administrator</option>
                <option value="user">Standard User</option>
                <option value="collection_steward">Collection Steward</option>
                <option value="viewer">Viewer Only</option>
              </select>
            </div>
            <div className="um-field">
              <label>Status:</label>
              <select
                value={userForm.is_active !== undefined ? String(userForm.is_active) : 'true'}
                onChange={(e) => setUserForm(prev => ({ ...prev, is_active: e.target.value === 'true' }))}
              >
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>
            <div className="um-actions">
              <button type="button" onClick={handleCancelEdit} className="um-cancel">
                Cancel
              </button>
              <button type="submit" className="um-save">
                {editingUserId === 0 ? 'Create User' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="um-table-container">
        <table className="um-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Full Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id} className={user.is_active ? '' : 'inactive'}>
                <td>{user.username}</td>
                <td>{user.email}</td>
                <td>{user.full_name || '-'}</td>
                <td>
                  <span className={`role-badge role-${user.role}`}>
                    {user.role}
                  </span>
                </td>
                <td>
                  <span className={user.is_active ? 'status-active' : 'status-inactive'}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="um-actions-cell">
                  {!editingUserId || editingUserId !== user.id ? (
                    <>
                      <button onClick={() => handleEdit(user)} className="um-action-button um-edit">
                        Edit
                      </button>
                      <button onClick={() => handleToggleStatus(user.id)} className="um-action-button um-toggle">
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button onClick={() => handleDelete(user.id)} className="um-action-button um-delete">
                        Delete
                      </button>
                    </>
                  ) : null}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={6} className="um-empty-state">
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UserManagement;