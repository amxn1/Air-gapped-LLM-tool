import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './DocumentDetailModal.css';

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

type DocumentDetailModalProps = {
  isOpen: boolean;
  onClose: () => void;
  documentId: number | null;
};

const DocumentDetailModal: React.FC<DocumentDetailModalProps> =
  ({ isOpen, onClose, documentId }) => {
  const navigate = useNavigate();
  if (!isOpen || documentId === null) return null;

  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Array<{id: number; text: string; chunk_index: number}>>([]);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch document details
        const docResponse = await fetch(`http://localhost:8000/v1/documents/${documentId}`);
        if (!docResponse.ok) {
          throw new Error(`Failed to fetch document: ${docResponse.status}`);
        }
        const docData = await docResponse.json();
        setDocument(docData);

        // Fetch document chunks
        const chunksResponse = await fetch(`http://localhost:8000/v1/documents/${documentId}/chunks`);
        if (!chunksResponse.ok) {
          throw new Error(`Failed to fetch document chunks: ${chunksResponse.status}`);
        }
        const chunksData = await chunksResponse.json();
        setChunks(chunksData);
      } catch (err) {
        console.error('Error fetching document details:', err);
        setError('Failed to load document details');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [documentId]);

  if (loading) {
    return (
      <div className="detail-modal-overlay">
        <div className="detail-modal">
          <div className="detail-modal-content">
            <h3>Loading document details...</h3>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="detail-modal-overlay">
        <div className="detail-modal">
          <div className="detail-modal-content">
            <h3>Error</h3>
            <p>{error}</p>
            <button onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="detail-modal-overlay">
        <div className="detail-modal">
          <div className="detail-modal-content">
            <h3>Document not found</h3>
            <button onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    );
  }

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

  return (
    <div className="detail-modal-overlay" onClick={onClose}>
      <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="detail-modal-header">
          <h3>Document Details</h3>
          <button onClick={onClose} className="detail-modal-close">
            ×
          </button>
        </div>
        <div className="detail-modal-body">
          <div className="detail-modal-info">
            <div className="detail-modal-icon">{getFileIcon(document.media_type)}</div>
            <div>
              <h4>{document.original_filename}</h4>
              <p className="detail-filename">{document.filename}</p>
            </div>
          </div>

          <div className="detail-modal-meta">
            <div className="detail-meta-item">
              <span className="detail-meta-label">Size:</span>
              <span className="detail-meta-value">
                {document.file_size ? `${(document.file_size / 1024).toFixed(1)} KB` : 'Unknown'}
              </span>
            </div>
            <div className="detail-meta-item">
              <span className="detail-meta-label">Type:</span>
              <span className="detail-meta-value">
                {document.media_type.split('/').pop() || document.media_type}
              </span>
            </div>
            <div className="detail-meta-item">
              <span className="detail-meta-label">Status:</span>
              <span className="detail-meta-value" style={{
                display: 'inline-block',
                width: '10px',
                height: '10px',
                backgroundColor: getStatusColor(document.import_status),
                borderRadius: '50%',
                marginRight: '8px',
                verticalAlign: 'middle'
              }}>
              </span>
              {document.import_status.charAt(0).toUpperCase() + document.import_status.slice(1)}
            </div>
            <div className="detail-meta-item">
              <span className="detail-meta-label">Uploaded:</span>
              <span className="detail-meta-value">
                {new Date(document.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          {document.processing_error && (
            <div className="detail-modal-error">
              <strong>Processing Error:</strong> {document.processing_error}
            </div>
          )}

          <div className="detail-modal-chunks">
            <h4>Document Chunks ({chunks.length})</h4>
            {chunks.length === 0 ? (
              <p>No chunks available</p>
            ) : (
              <div className="chunks-list">
                {chunks.map((chunk, index) => (
                  <div key={chunk.id} className="chunk-item">
                    <div className="chunk-header">
                      <strong>Chunk {chunk.chunk_index + 1}</strong>
                    </div>
                    <p className="chunk-text">
                      {chunk.text.length > 200 ?
                        `${chunk.text.substring(0, 200)}...` :
                        chunk.text
                      }
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="detail-modal-actions">
            <button
              className="detail-modal-btn"
              style={{ background: '#2563eb', color: '#ffffff', fontWeight: 600 }}
              onClick={() => {
                onClose();
                navigate(`/?docId=${document.id}&docName=${encodeURIComponent(document.original_filename)}`);
              }}
            >
              💬 Ask Llama 3.2 about this Document
            </button>
            <button
              className="detail-modal-btn detail-modal-download"
              onClick={() => {
                window.open(`http://localhost:8000/v1/documents/${document.id}/download`, '_blank');
              }}
            >
              Download Original File
            </button>
            <button
              className="detail-modal-btn detail-modal-close"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentDetailModal;