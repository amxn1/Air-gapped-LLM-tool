"""
SQLAlchemy models for documents and collections.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from ..database import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    classification = Column(String, default="internal")  # e.g., public, internal, confidential, restricted
    access_policy = Column(String, default="authenticated")  # e.g., public, authenticated, role-based
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    documents = relationship("Document", back_populates="collection")
    owner = relationship("User", back_populates="owned_collections")
    owner_id = Column(Integer, ForeignKey("users.id"))


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # Path to stored file
    file_size = Column(Integer, nullable=True)
    media_type = Column(String, nullable=False)  # MIME type
    checksum = Column(String, nullable=True)  # SHA-256 for integrity
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    import_status = Column(String, default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="documents")
    owner = relationship("User", back_populates="owned_documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order of chunk within document
    text = Column(Text, nullable=False)
    # Note: Embeddings are stored in the vector store (Qdrant), not in SQL
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")