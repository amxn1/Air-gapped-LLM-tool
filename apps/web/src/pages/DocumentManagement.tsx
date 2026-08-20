import React, { useState, useEffect } from 'react';
import DocumentList from '../components/DocumentList';
import CollectionManager from '../components/CollectionManager';
import UploadDocumentModal from '../components/UploadDocumentModal';
import './DocumentManagement.css';

const DocumentManagement: React.FC = () => {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);

  const handleUploadComplete = () => {
    setShowUploadModal(false);
    // In a real implementation, we would refresh the document list
  };

  return (
    <div className="document-management">
      <div className="dm-header">
        <h2>Document Management</h2>
        <button onClick={() => setShowUploadModal(true)}>
          Upload Document
        </button>
        <nav>
          <a href="/">Back to Chat</a>
        </nav>
      </div>

      <div className="dm-body">
        <aside className="dm-sidebar">
          <CollectionManager
            onCollectionSelect={setSelectedCollectionId}
            selectedCollectionId={selectedCollectionId}
          />
        </aside>

        <main className="dm-main">
          <DocumentList
            collectionId={selectedCollectionId}
          />
        </main>
      </div>

      <UploadDocumentModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadComplete={handleUploadComplete}
        defaultCollectionId={selectedCollectionId}
      />
    </div>
  );
};

export default DocumentManagement;