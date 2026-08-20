import React, { useState, useEffect } from 'react';
import './CollectionManager.css';

type Collection = {
  id: number;
  name: string;
  description?: string;
  classification: string;
  access_policy: string;
  documentCount: number;
};

type CollectionManagerProps = {
  onCollectionSelect: (id: number | null) => void;
  selectedCollectionId: number | null;
};

const CollectionManager: React.FC<CollectionManagerProps> =
  ({ onCollectionSelect, selectedCollectionId }) => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCollections = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('http://localhost:8000/v1/collections');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Transform data to include document count
        const collectionsWithCount: Collection[] = data.map((col: any) => ({
          ...col,
          documentCount: 0 // Would need to fetch or calculate this
        }));
        setCollections(collectionsWithCount);
      } catch (err) {
        console.error('Error fetching collections:', err);
        setError('Failed to load collections: ' + (err as any).message);
      } finally {
        setLoading(false);
      }
    };

    fetchCollections();
  }, []);

  const handleRetry = () => {
    // Trigger a refetch
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading collections...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠️</div>
        <p className="error-message">{error}</p>
        <button onClick={handleRetry} className="retry-button">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="collection-manager">
      <div className="cm-header">
        <h3>Collections</h3>
        <button onClick={() => {
          // In a real implementation, this would open a modal to create a new collection
          alert('Create new collection functionality would go here');
        }}>
          + New Collection
        </button>
      </div>
      <div className="collection-list">
        {collections.map(collection => (
          <div
            key={collection.id}
            className={`collection-item ${collection.id === selectedCollectionId ? 'selected' : ''}`}
            onClick={() => onCollectionSelect(collection.id)}
          >
            <div className="collection-header">
              <h4>{collection.name}</h4>
              <span className="classification">{collection.classification}</span>
            </div>
            {collection.description && (
              <p className="collection-description">{collection.description}</p>
            )}
            <div className="collection-meta">
              <span>{collection.documentCount} documents</span>
              <span>{collection.access_policy} access</span>
            </div>
          </div>
        ))}
        {collections.length === 0 && (
          <div className="empty-state">
            No collections yet. Create one to get started.
          </div>
        )}
      </div>
    </div>
  );
};

export default CollectionManager;