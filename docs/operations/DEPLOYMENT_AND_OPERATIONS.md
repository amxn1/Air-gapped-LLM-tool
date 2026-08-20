# Operations & Deployment Guide — Offline LLM Assistant

## 1. Sizing and Scalability Topologies

### Tier 1: Single-Host Pilot (Evaluation / Workstation)
- **Hardware**: 32 GB RAM, 8+ CPU cores, optional 12–16 GB VRAM GPU.
- **Model Size**: 7B–8B parameter quantised GGUF model (`q4_k_m`).
- **Topology**: All containers (API, Web, DB, Qdrant, llama.cpp) co-located via single Docker Compose manifest.

### Tier 2: Departmental Deployment (5–25 Concurrent Users)
- **Hardware**: 64–128 GB RAM, 24 GB+ VRAM (NVIDIA RTX 4090 / A5000 / A10G).
- **Model Size**: 8B–14B parameter quantised model.
- **Topology**: Dedicated inference worker with GPU access; API, PostgreSQL, and Qdrant hosted on application node.

### Tier 3: Enterprise Cluster (High-Availability & Multi-Tenant)
- **Hardware**: Dedicated GPU inference pool (multi-node), high-performance NVMe storage for PostgreSQL and Qdrant.
- **Topology**: Stateless UI/API behind intranet reverse proxy, asynchronous request queue, segmented network zones.

---

## 2. Model Lifecycle & Rollback Procedures

1. **Intake**: Transfer model weights (`.gguf` / `.safetensors`) via air-gap import media with SHA-256 manifest.
2. **Staging**: Register model via `POST /v1/models/stage` (status set to `staged`).
3. **Smoke Testing**: Execute automated diagnostic test via `POST /v1/models/{id}/test` to verify inference latency and output formatting.
4. **Promotion**: Promote to active status via `POST /v1/models/{id}/activate`. The previous active model is retained as rollback predecessor.
5. **Rollback**: If runtime degradation or hardware regression occurs, invoke `POST /v1/models/{id}/rollback` to immediately revert traffic to the predecessor.

---

## 3. Backup and Disaster Recovery (DR)

### Backup Checklist
- **Relational Metadata**: `pg_dump -U offline_llm offline_llm > backup_meta_$(date +%Y%m%d).sql`
- **Vector Embeddings**: Qdrant snapshot API (`/collections/document_chunks/snapshots`)
- **Document Store**: Encrypted archive of `./storage` volume

### Restoration Test Procedure
1. Load database snapshot into staging instance.
2. Restore vector store snapshot to Qdrant storage volume.
3. Validate `/health` endpoint and run sample chat query.
