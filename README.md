# Offline LLM Assistant

A fully air-gapped, on-premises assistant that generates natural language responses without any network connection.

## Overview

This project implements an offline LLM assistant supporting:
- General question answering and drafting
- Text and document summarization
- Science and technology material processing
- News and editorial content analysis
- Context-aware rewriting and grammar correction
- Retrieval-augmented generation (RAG) over local document collections

The system is designed to be completely air-gapped with no runtime internet connections, ensuring data privacy and security.

## Architecture

The system follows a modular architecture:
- **Frontend**: React/TypeScript single-page application
- **Backend**: Python/FastAPI API service
- **Services**: 
  - Inference (llama.cpp server)
  - Ingestion (document processing pipeline)
  - Retrieval (vector search with Qdrant)
- **Data Stores**:
  - PostgreSQL (metadata, users, access control)
  - Qdrant (vector embeddings)
  - Encrypted file storage (documents, models)

## Directory Structure

```
offline-llm-assistant/
├── apps/
│   ├── api/              # FastAPI backend
│   └── web/              # React/TypeScript frontend
├── services/
│   ├── ingestion/        # Document processing workers
│   ├── inference/        # Model inference adapters
│   └── retrieval/        # Vector search and citation assembly
├── packages/
│   ├── contracts/        # API schemas and shared types
│   └── prompts/          # Versioned task templates
├── infrastructure/
│   ├── compose/          # Docker Compose deployment
│   ├── ansible-or-scripts/# Offline installation automation
│   └── monitoring/       # Local dashboards and alert rules
├── docs/                 # Documentation
├── tests/                # Test suites
└── release/              # Release manifests (no model weights/secrets)
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ and npm (for frontend development)
- Python 3.9+ (for backend development)

### Development Setup

1. Clone the repository
2. Set up the backend:
   ```bash
   cd apps/api
   pip install -r requirements.txt
   ```
3. Set up the frontend:
   ```bash
   cd ../web
   npm install
   ```
4. Start the services:
   ```bash
   cd ../../infrastructure/compose
   docker-compose up
   ```

### Production Deployment

For air-gapped deployment:
1. Build the offline release bundle
2. Transfer via approved air-gap process
3. Verify checksums and signatures
4. Deploy using `docker-compose up -d`

## Features Implemented (Phase 1 MVP)

- [x] Basic FastAPI application structure
- [x] API routing with health, models, chat, and summary endpoints
- [x] React/TypeScript frontend with chat interface
- [ ] Authentication and RBAC
- [ ] llama.cpp integration
- [ ] Audit logging
- [ ] Docker Compose orchestration

## Future Phases

**Phase 2: Document Intelligence**
- Document ingestion pipeline
- Text extraction and chunking
- Embedding generation and vector storage
- Retrieval-augmented generation
- Specialized templates for different content types

**Phase 3: Multi-model, Administration, and Scale**
- Model registry and activation workflow
- Multiple inference workers with queuing
- Administrator dashboards
- Offline update bundles
- Load balancing and high availability

## Security & Air-Gap Considerations

- Default-deny egress network policies
- No external dependencies in production
- Local identity provider integration
- Role-based access control before data retrieval
- Encryption at rest for sensitive data
- Comprehensive audit logging
- Tamper-proof release bundles with checksums/signatures

## License

[Specify your license here]

## Acknowledgments

- Based on architecture and implementation specifications
- llama.cpp for efficient local LLM inference
- React and FastAPI communities