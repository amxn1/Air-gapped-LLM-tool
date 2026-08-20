import React, { useState } from 'react';
import CollectionSelector from './CollectionSelector';
import './UploadDocumentModal.css';

type UploadDocumentModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: () => void;
  defaultCollectionId?: number | null;
};

const UploadDocumentModal: React.FC<UploadDocumentModalProps> =
  ({ isOpen, onClose, onUploadComplete, defaultCollectionId }) => {
  if (!isOpen) return null;

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collectionId, setCollectionId] = useState<number | null>(defaultCollectionId ?? null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (collectionId !== null) {
        // In a real app, user_id would come from authentication
        formData.append('user_id', '1');
        formData.append('collection_id', collectionId.toString());
      }

      const response = await fetch('http://localhost:8000/v1/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      // Success
      setUploading(false);
      onUploadComplete();
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  const handleRetry = () => {
    // Reset error and retry upload if we have a file
    if (selectedFile) {
      // Trigger upload again by calling handleUpload with a fake event
      // In a real implementation, we might want to refactor this
      setError(null);
      setUploading(true);

      // Simulate form submission
      const fakeEvent = {
        preventDefault: () => {}
      } as React.FormEvent<HTMLFormElement>;

      handleUpload(fakeEvent);
    }
  };

  return (
    <div className="upload-modal-overlay">
      <div className="upload-modal">
        <div className="um-header">
          <h3>Upload Document</h3>
          <button onClick={onClose} className="um-close">
            ×
          </button>
        </div>

        <form onSubmit={handleUpload} className="um-form">
          <div className="um-field">
            <label htmlFor="file-input">Select Document</label>
            <input
              type="file"
              id="file-input"
              accept=".txt,.pdf,.docx,.md"
              onChange={handleFileChange}
              disabled={uploading}
              required
            />
            {selectedFile && (
              <p className="um-file-info">
                Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
              </p>
            )}
          </div>

          <div className="um-field">
            <label htmlFor="collection-select">Add to Collection (Optional)</label>
            <CollectionSelector
              value={collectionId}
              onChange={setCollectionId}
            />
          </div>

          {error && (
            <div className="um-error-container">
              <div className="um-error-icon">⚠️</div>
              <p className="um-error-message">{error}</p>
              <button onClick={handleRetry} className="um-retry-button">
                Try Again
              </button>
            </div>
          )}

          <div className="um-actions">
            <button
              type="button"
              onClick={onClose}
              className="um-btn um-cancel"
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="um-btn um-submit"
              disabled={uploading || !selectedFile}
            >
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadDocumentModal;