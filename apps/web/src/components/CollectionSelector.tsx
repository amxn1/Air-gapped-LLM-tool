import React, { useState, useEffect } from 'react';
import './CollectionSelector.css';

type Collection = {
  id: number;
  name: string;
};

type CollectionSelectorProps = {
  value: number | null;
  onChange: (value: number | null) => void;
};

const CollectionSelector: React.FC<CollectionSelectorProps> =
  ({ value, onChange }) => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCollections = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/v1/collections');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setCollections(data);
      } catch (err) {
        console.error('Error fetching collections:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchCollections();
  }, []);

  if (loading) {
    return (
      <select
        value={value ?? ''}
        onChange={(e) => onChange(Number(e.target.value) || null)}
        disabled
      >
        <option value="">Loading collections...</option>
      </select>
    );
  }

  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(Number(e.target.value) || null)}
    >
      <option value="">No Collection</option>
      {collections.map(collection => (
        <option key={collection.id} value={collection.id}>
          {collection.name}
        </option>
      ))}
    </select>
  );
};

export default CollectionSelector;