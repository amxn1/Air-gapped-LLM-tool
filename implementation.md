# Implementation Plan — Offline LLM Assistant

## 1. Objective

Build and deploy a fully **air-gapped**, on-premises assistant that generates useful natural-language responses without any network connection. The system must support:

1. General question answering and drafting using locally installed open-weight LLMs.
2. Summarisation of supplied text and documents.
3. Summarisation of science and technology material.
4. Summarisation of news headlines and editorial content supplied to the system.
5. Context-aware rewriting, grammar correction, and formatting.
6. Additional capabilities through modular local models and tools.

The solution must make no runtime calls to cloud APIs, telemetry services, package registries, or internet search engines.

## 2. Scope and Assumptions

### In scope

- A browser-based local user interface, accessible only from an approved intranet or the host machine.
- A local REST API for UI and optional approved client integrations.
- CPU and GPU inference configurations.
- Ingestion of text, PDF, DOCX, TXT, Markdown, and optionally HTML files.
- Grounded answers over documents deliberately uploaded/imported into the local knowledge base.
- Model selection, model lifecycle management, audit logging, and role-based access.

### Out of scope

- Live web browsing, live news collection, or SaaS integrations. News and editorial material is processed only after controlled offline import.
- Training a foundation model from scratch.
- Automatically copying data between classification domains.

### Key design assumptions

- The deployment environment is isolated from the internet. Models, packages, operating system patches, and approved documents enter through an authorised transfer process.
- All documents and prompts are potentially sensitive; no data leaves the deployment boundary.
- An NVIDIA GPU is preferred for responsive multi-user performance, but a CPU-only profile remains available for smaller installations.

## 3. Recommended Technology Stack

| Layer | Recommended implementation | Reason |
|---|---|---|
| User interface | React + TypeScript, served locally | Responsive, maintainable single-page experience |
| API service | Python + FastAPI | Clear APIs, streaming support, strong ML ecosystem |
| Inference runtime | `llama.cpp`/`llama-server` for GGUF models; optional vLLM for GPU servers | Supports CPU and GPU deployments and a broad model catalog |
| Base models | Approved instruction-tuned models in GGUF or Safetensors format | Enables interchangeable model profiles |
| Embeddings | Local embedding model, e.g. BGE or E5 family | Semantic retrieval without external calls |
| Vector retrieval | Qdrant local mode/server or FAISS | Efficient offline semantic search |
| Metadata and users | PostgreSQL | Transactional storage, auditing, and access control |
| Document extraction | Apache Tika or Python extractors (`pypdf`, `python-docx`) | Local parsing of common office formats |
| Containerisation | Docker Compose or Podman Compose | Repeatable, isolated deployment |
| Observability | Local structured logs and Prometheus-compatible metrics endpoint | Operable without cloud monitoring |

The exact model should be decided after evaluation on representative authorised data. The model abstraction must support at least two approved model families and quantisation levels.

## 4. Functional Implementation

### 4.1 Conversational assistant

- Provide chat sessions, conversation titles, message history, streaming responses, and copy/export actions.
- Accept a system policy selected by an administrator and task-specific user instructions.
- Allow selection of an approved model profile and response length.
- Show model name, knowledge-base sources used, and generation timestamp with each answer.
- Permit users to delete conversations according to retention policy.

### 4.2 Text and document summarisation

Implement three modes:

| Mode | Behaviour |
|---|---|
| Quick summary | Short factual summary for a supplied text or selected document |
| Structured brief | Executive summary, key points, entities, dates, implications, and open questions |
| Long-document summary | Chunk-level summaries followed by a synthesis, preserving page/section references |

For long content, use a map-reduce workflow:

1. Extract text and preserve source metadata such as filename, page, heading, and import date.
2. Split text by headings and token length with a small overlap.
3. Summarise each chunk using a fixed, factual prompt.
4. Combine chunk summaries into a final summary using a second local inference call.
5. Return citations to the contributing sections/pages.

### 4.3 Science and technology material

Add a dedicated prompt template that produces:

- Topic and purpose.
- Method, system, or technology described.
- Principal findings or claims.
- Evidence, limitations, assumptions, and unresolved questions.
- Acronym expansion on first use.
- A distinction between statements in the source and assistant inference.

This mode should prioritise faithful summaries and source citations over stylistic fluency.

### 4.4 News and editorial material

The platform does not retrieve current news. It provides a controlled **offline news-analysis workspace** for articles, headlines, bulletin feeds, or editorial pages that authorised users import.

For each imported item, generate:

- Headline, source, publication date, and supplied category.
- One-paragraph overview.
- Key people, organisations, locations, and events mentioned.
- Claimed facts versus attributed opinions.
- A neutral multi-item topic brief when several articles are selected.

When source metadata is absent, label it as “not provided”; do not infer publication date or outlet.

### 4.5 Rewriting, formatting, and grammar checks

- Support grammar correction, formalisation, simplification, bullet conversion, and template-based formatting.
- Preserve meaning by default; show the revised text and a concise list of material changes.
- Offer optional modes: Indian English, UK English, US English, formal government correspondence, technical note, and plain language.
- Do not fabricate citations, facts, or references during rewriting.

### 4.6 Retrieval-augmented generation (RAG)

- Let authorised users upload/import documents into named collections.
- Extract, clean, chunk, embed, and index content locally.
- At question time, retrieve only collections the user is authorised to access.
- Supply top-ranked excerpts and document metadata to the LLM.
- Require citations for answers based on indexed content; display filename and page/section.
- If evidence is insufficient, answer that the supplied knowledge base does not establish the requested fact.

## 5. Delivery Phases

### Phase 0 — Discovery and acceptance criteria

1. Identify classification levels, user roles, retention rules, and approved import process.
2. Gather a representative, sanitised evaluation set: general prompts, technical documents, editorial content, grammar samples, and expected outputs.
3. Define measurable acceptance targets: quality, latency, concurrency, availability, and supported hardware.
4. Select at least two candidate base models and one embedding model for offline evaluation.

### Phase 1 — Minimum viable offline assistant

1. Build the local FastAPI service and React UI.
2. Integrate one local inference engine and one quantised instruction model.
3. Implement chat, streaming output, prompt templates, text summarisation, rewriting, and grammar workflows.
4. Add local authentication, roles, and append-only audit events.
5. Package a single-host installation using Compose.

**Exit criterion:** A permitted user can generate, summarise, and rewrite text with zero network connectivity.

### Phase 2 — Document intelligence

1. Implement document import, malware/format validation in the approved intake process, text extraction, and metadata capture.
2. Add the chunking, embedding, vector-search, and citation pipeline.
3. Build document and collection management screens.
4. Implement science/technology and news/editorial task templates.
5. Add retrieval quality tests and source-grounded response checks.

**Exit criterion:** Users can query authorised document collections and receive verifiable citations.

### Phase 3 — Multi-model, administration, and scale

1. Add a model registry with compatibility metadata, performance profiles, and activation/rollback controls.
2. Support multiple inference workers and queueing for concurrent requests.
3. Add administrator dashboards for model health, capacity, document ingestion, and audit review.
4. Establish offline update bundles for models, dependencies, and configuration.
5. Perform load, security, disaster-recovery, and usability testing.

**Exit criterion:** Administrators can switch approved models and operate the service reliably for the target user load.

## 6. API Contract (Initial)

All endpoints are served inside the trusted network and require authentication unless marked otherwise.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service, database, model-worker, and vector-store health |
| `GET` | `/v1/models` | Approved, available model profiles |
| `POST` | `/v1/chat/completions` | Stream or return a chat/rewrite/summarisation response |
| `POST` | `/v1/documents` | Upload a document to the controlled intake queue |
| `GET` | `/v1/documents/{id}` | Document status and extracted metadata |
| `POST` | `/v1/collections/{id}/query` | Retrieval-grounded question answering |
| `POST` | `/v1/summaries` | Structured text or document summary |
| `GET` | `/v1/audit/events` | Administrator audit review |

Use an OpenAI-compatible chat-completions subset where practical. It reduces client integration effort while all execution remains local.

## 7. Data Model (Initial)

| Entity | Important fields |
|---|---|
| `users` | id, username, role, status, password/identity reference |
| `conversations` | id, owner_id, title, retention_class, created_at |
| `messages` | id, conversation_id, role, content, model_profile, created_at |
| `model_profiles` | id, model_name, version, format, context_limit, hardware_profile, checksum, status |
| `documents` | id, collection_id, filename, media_type, checksum, classification, import_status, owner_id |
| `document_chunks` | id, document_id, page_or_section, ordinal, text, embedding_reference |
| `collections` | id, name, classification, access_policy |
| `audit_events` | id, actor_id, action, object_type, object_id, result, timestamp, request_id |

Store raw documents in an encrypted local object/filesystem store, structured metadata in PostgreSQL, and vector embeddings in the local vector database. Store only necessary prompt and response content in audit logs; use configurable redaction and retention rules.

## 8. Security and Air-Gap Controls

1. Bind services to `localhost` by default; expose an intranet interface only after network approval.
2. Deny outbound network traffic from application and model containers at the host firewall/network level.
3. Disable telemetry, automatic update checks, remote model downloads, and browser CDN dependencies.
4. Package JavaScript, fonts, models, Python wheels, and container images in an approved offline release bundle.
5. Verify every imported release/model with an approved manifest, SHA-256 checksum, signature where available, and malware scan at the controlled transfer boundary.
6. Enforce role-based access to models, document collections, administration, and audit review.
7. Encrypt data at rest and use TLS for any intranet traffic; manage keys through the organisation’s approved mechanism.
8. Record authentication, model activation, file import, retrieval, export, and administration events.
9. Protect against prompt injection by treating document text as untrusted data, separating system instructions from retrieved context, and preventing tools from executing retrieved instructions.

## 9. Hardware Profiles

| Profile | Suggested use | Example capacity |
|---|---|---|
| Evaluation workstation | Pilot, single user | 32 GB RAM; modern 8+ core CPU; optional 12–16 GB VRAM GPU; 7–8B quantised model |
| Department server | Small concurrent group | 64–128 GB RAM; 24 GB+ VRAM GPU; 8–14B quantised model; separate database storage |
| Enterprise node pool | Multiple teams/high availability | Multiple GPU inference nodes, dedicated PostgreSQL/vector nodes, load balancer, shared approved storage |

Actual sizing must be measured with the chosen models, context size, document volume, and simultaneous-user target. Larger context windows and models require substantially more memory.

## 10. Offline Build and Release Process

1. Build and test application artifacts in a connected, controlled build environment.
2. Produce immutable container images, offline dependency wheels/packages, model files, SBOM, checksums, licences, configuration defaults, and release notes.
3. Scan, approve, and sign the release bundle before transfer.
4. Transfer media through the organisation’s approved air-gap process.
5. Verify checksums and signatures in the target environment before installation.
6. Deploy using versioned Compose/manifests and a non-production configuration first.
7. Run the offline acceptance test suite with all network interfaces disabled.
8. Promote the release, keep the previous approved version for rollback, and record the deployment in the audit log.

## 11. Testing and Acceptance

### Automated tests

- Unit tests for prompting, document extraction, chunking, access checks, redaction, and API validation.
- Integration tests for inference streaming, model switching, ingestion, retrieval citations, and offline startup.
- Security tests for unauthorised collection access, malicious document content, path traversal, oversized uploads, and input sanitisation.
- Regression tests using a fixed, versioned local evaluation corpus.

### Operational tests

- Disconnect all external network routes and prove all core workflows continue to function.
- Restart services and confirm graceful recovery of jobs and conversations.
- Measure time-to-first-token, tokens per second, summary latency, retrieval latency, and concurrent-request behaviour.
- Restore a backup into an isolated test instance.

### Suggested acceptance measures

- No observed outbound connections during a full test suite.
- Every RAG response identifies the source documents/sections used.
- Authorisation tests show no cross-collection document leakage.
- Quality reviewers score summaries, rewrites, and technical briefs against the agreed evaluation set.
- Performance meets the thresholds agreed in Phase 0 for each target hardware profile.

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated or unsupported answers | RAG citations, evidence-first prompts, explicit uncertainty responses, reviewer evaluation |
| Weak performance on local hardware | Benchmark multiple quantisations/models; apply request queueing; size GPU/RAM from observed load |
| Imported-model supply-chain risk | Approved offline bundle, SBOM, signatures, checksums, controlled transfer and scanning |
| Sensitive-data exposure | RBAC, encryption, retention limits, redaction, audit events, separate collections by classification |
| Poor document extraction | Type-specific extractors, import preview, OCR only where approved, quality metrics |
| Vendor/model lock-in | Stable inference API and model registry supporting multiple formats/runtimes |
| Prompt injection in documents | Treat retrieved content as data, restrict tools, source-label all context, adversarial testing |

## 13. Project Deliverables

1. Offline deployment package and installation guide.
2. Architecture and security design documentation.
3. Web UI and locally hosted API service.
4. Approved model registry and at least two validated model profiles.
5. Document ingestion, retrieval, and citation capability.
6. Administrator and operator guides.
7. Test plan, benchmark report, SBOM, release manifest, and rollback procedure.

