import React, { useState, useEffect } from 'react';
import DocumentCard from './DocumentCard';
import DocumentDetailModal from './DocumentDetailModal';
import './DocumentList.css';

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

type Filters = {
  search: string;
  status: string;
  dateFrom: string;
  dateTo: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
};

type DocumentListProps = {
  collectionId?: number | null;
};

const DocumentList: React.FC<DocumentListProps> =
  ({ collectionId }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    search: '',
    status: 'all',
    dateFrom: '',
    dateTo: '',
    sortBy: 'created_at',
    sortOrder: 'desc'
  });

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      let url = 'http://localhost:8000/v1/documents';

      // Build query parameters from filters
      const params = new URLSearchParams();
      if (collectionId !== null && collectionId !== undefined) {
        params.append('collection_id', collectionId.toString());
      }
      if (filters.search) {
        params.append('search', filters.search);
      }
      if (filters.status && filters.status !== 'all') {
        params.append('status', filters.status);
      }
      if (filters.dateFrom) {
        params.append('date_from', filters.dateFrom);
      }
      if (filters.dateTo) {
        params.append('date_to', filters.dateTo);
      }
      if (filters.sortBy) {
        params.append('sort_by', filters.sortBy);
      }
      if (filters.sortOrder) {
        params.append('sort_order', filters.sortOrder);
      }

      const queryString = params.toString();
      if (queryString) {
        url += `?${queryString}`;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      console.error('Error fetching documents:', err);
      setError('Failed to load documents: ' + (err as any).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [collectionId, filters]);

  const handleFilterChange = (filterName: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters(prev => ({
      ...prev,
      search: e.target.value
    }));
  };

  const handleRetry = () => {
    fetchDocuments();
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading documents...</p>
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
    <div className="document-list">
      <div className="dl-header">
        <h3>Documents</h3>
        <div className="dl-filters">
          <div className="filter-group">
            <label htmlFor="search-input">Search:</label>
            <input
              id="search-input"
              type="text"
              placeholder="Search documents..."
              value={filters.search}
              onChange={handleSearchChange}
              className="filter-input"
            />
          </div>

          <div className="filter-group">
            <label htmlFor="status-filter">Status:</label>
            <select
              id="status-filter"
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="filter-select"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="sort-by">Sort by:</label>
            <select
              id="sort-by"
              value={filters.sortBy}
              onChange={(e) => handleFilterChange('sortBy', e.target.value)}
              className="filter-select"
            >
              <option value="created_at">Date Uploaded</option>
              <option value="original_filename">Filename</option>
              <option value="file_size">File Size</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="sort-order">Order:</label>
            <select
              id="sort-order"
              value={filters.sortOrder}
              onChange={(e) => handleFilterChange('sortOrder', e.target.value)}
              className="filter-select"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>

          <button
            onClick={() => {
              // Reset filters
              setFilters({
                search: '',
                status: 'all',
                dateFrom: '',
                dateTo: '',
                sortBy: 'created_at',
                sortOrder: 'desc'
              });
            }}
            className="reset-filters-btn"
          >
            Reset Filters
          </button>
        </div>
        <div className="dl-actions">
          <div className="doc-count">
            {documents.length} documents
          </div>
        </div>
      </div>

      <div className="dl-grid">
        {documents.map(doc => (
          <DocumentCard
            key={doc.id}
            document={doc}
            onDocumentUpdated={fetchDocuments}
            onViewDocument={(id) => {
              setSelectedDocId(id);
              setIsDetailModalOpen(true);
            }}
          />
        ))}
        {documents.length === 0 && (
          <div className="empty-state">
            <p>No documents found matching the filters.</p>
            {!collectionId && (
              <>
                <p>Upload some documents or adjust your filters.</p>
              </>
            )}
          </div>
        )}
      </div>

      <DocumentDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedDocId(null);
        }}
        documentId={selectedDocId}
      />
    </div>
  );
};

export default DocumentList;