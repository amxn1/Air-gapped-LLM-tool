import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CollectionSelector from './CollectionSelector';
import './DocumentCard.css';

type Document = {
  id: number;
  filename: string;
  original_filename: string;
  file_path?: string;
  file_size?: number;
  media_type: string;
  collection_id?: number;
  import_status: string;
  processing_error?: string;
  created_at: string;
  updated_at: string;
};

type DocumentCardProps = {
  document: Document;
  onDocumentUpdated?: () => void;
  onViewDocument?: (documentId: number) => void;
};

const DocumentCard: React.FC<DocumentCardProps> =
  ({ document, onDocumentUpdated, onViewDocument }) => {
  const navigate = useNavigate();
  const [moveToCollectionId, setMoveToCollectionId] = useState<number | null>(null);
  const [moveToCollectionLoading, setMoveToCollectionLoading] = useState(false);
  const [moveToCollectionError, setMoveToCollectionError] = useState<string | null>(null);
  const [collections, setCollections] = useState<Array<{id: number; name: string}>>([]);

  const getFileIcon = (mediaType: string): string => {
    if (mediaType.includes('pdf')) return '📄';
    if (mediaType.includes('word')) return '📝';
    if (mediaType.includes('text')) return '📃';
    if (mediaType.includes('markdown')) return '📓';
    return '📎';
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#28a745'; // green
      case 'processing': return '#ffc107'; // yellow
      case 'failed': return '#dc3545'; // red
      case 'pending': return '#6c757d'; // gray
      default: return '#6c757d';
    }
  };

  // Fetch collections for the move to collection dropdown
  useEffect(() => {
    const fetchCollections = async () => {
      try {
        const response = await fetch('http://localhost:8000/v1/collections');
        if (!response.ok) {
          throw new Error(`Failed to fetch collections: ${response.status}`);
        }
        const data = await response.json();
        setCollections(data);
      } catch (err) {
        console.error('Error fetching collections:', err);
      }
    };

    fetchCollections();
  }, []);

  const handleMoveToCollection = async () => {
    if (moveToCollectionId === null) return;

    setMoveToCollectionLoading(true);
    setMoveToCollectionError(null);

    try {
      const response = await fetch(`http://localhost:8000/v1/documents/${document.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          collection_id: moveToCollectionId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to move document: ${response.status}`);
      }

      setMoveToCollectionLoading(false);
      setMoveToCollectionId(null);
      if (onDocumentUpdated) {
        onDocumentUpdated();
      }
    } catch (err) {
      console.error('Error moving document:', err);
      setMoveToCollectionLoading(false);
      setMoveToCollectionError('Failed to move document');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Permanently delete '${document.original_filename}' and its embeddings?`)) {
      return;
    }
    try {
      const res = await fetch(`http://localhost:8000/v1/documents/${document.id}`, {
        method: 'DELETE',
      });
      if (res.ok && onDocumentUpdated) {
        onDocumentUpdated();
      }
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  const handleDownload = () => {
    window.open(`http://localhost:8000/v1/documents/${document.id}/download`, '_blank');
  };

  return (
    <div className="document-card">
      <div className="dc-header">
        <div className="dc-icon">{getFileIcon(document.media_type)}</div>
        <div className="dc-info">
          <h4>{document.original_filename}</h4>
          <p className="dc-filename">{document.filename}</p>
        </div>
      </div>

      <div className="dc-body">
        <div className="dc-meta">
          <span className="dc-size">
            {document.file_size ?
              `${(document.file_size / 1024).toFixed(1)} KB` :
              'Unknown size'}
          </span>
          <span className="dc-type">
            {document.media_type.split('/').pop() || document.media_type}
          </span>
        </div>

        <div className="dc-status">
          <span
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              backgroundColor: getStatusColor(document.import_status),
              borderRadius: '50%',
              marginRight: '8px'
            }}
          />
          {document.import_status.charAt(0).toUpperCase() + document.import_status.slice(1)}
        </div>

        <div className="dc-date">
          {new Date(document.created_at).toLocaleDateString()}
        </div>
      </div>

      <div className="dc-actions">
        <button
          className="dc-btn dc-chat"
          style={{ background: '#2563eb', color: '#ffffff', fontWeight: 600 }}
          onClick={() => navigate(`/?docId=${document.id}&docName=${encodeURIComponent(document.original_filename)}`)}
          title="Open in Chat and ask Llama about this document"
        >
          💬 Ask LLM
        </button>
        <button
          className="dc-btn dc-view"
          onClick={() => {
            if (onViewDocument) {
              onViewDocument(document.id);
            }
          }}
        >
          View
        </button>
        <button
          className="dc-btn dc-download"
          onClick={handleDownload}
        >
          Download
        </button>
        <button
          className="dc-btn dc-delete"
          onClick={handleDelete}
        >
          Delete
        </button>
        {document.collection_id !== moveToCollectionId && (
          <button
            className="dc-btn dc-move"
            onClick={() => {
              // Show move to collection dropdown
              setMoveToCollectionId(document.collection_id || null);
            }}
            disabled={moveToCollectionLoading}
          >
            Move to Collection
          </button>
        )}
        {moveToCollectionId !== null && (
          <div className="dc-move-collection">
            <CollectionSelector
              value={moveToCollectionId}
              onChange={setMoveToCollectionId}
            />
            <button
              className="dc-btn dc-move-confirm"
              onClick={handleMoveToCollection}
              disabled={moveToCollectionLoading}
            >
              {moveToCollectionLoading ? 'Moving...' : 'Move'}
            </button>
            <button
              className="dc-btn dc-move-cancel"
              onClick={() => setMoveToCollectionId(null)}
            >
              Cancel
            </button>
            {moveToCollectionError && (
              <div className="dc-move-error">{moveToCollectionError}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentCard;