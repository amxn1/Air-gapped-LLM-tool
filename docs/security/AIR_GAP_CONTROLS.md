# Security Architecture & Air-Gap Boundary Controls

## 1. Network Boundary & Egress Prevention

The Offline LLM Assistant is architected for strict network isolation:

- **Default-Deny Egress**: Container and host firewalls deny all outbound network connections.
- **Zero Cloud Runtime Dependencies**: No telemetry, crash reporting, web search engines, or remote model hubs (HuggingFace/OpenAI).
- **Self-Contained Frontend Assets**: All JavaScript bundles, stylesheets, and fonts are served locally from static files without browser CDNs.
- **Local Identity & Session Management**: Authentication is issued via HMAC SHA-256 JWT tokens with configurable expiration and local password hashing.

## 2. Role-Based Access Control (RBAC) Matrix

| Role | Permissions |
|---|---|
| `admin` | Full system control: User management, model activation/rollback, infrastructure configuration, full audit review. |
| `model_operator` | Stage, smoke test, activate, and rollback approved model profiles. |
| `collection_steward` | Create and manage document collections and assign classification / access policies. |
| `security_auditor` | Read-only inspection of append-only audit event logs. |
| `user` | Chat, document summarization, rewriting, and querying authorized collections. |

## 3. Pre-Retrieval Authorization

- User roles and collection permissions are evaluated **before** vector searches occur.
- Unauthorized document collections are excluded from semantic search queries, eliminating vector-level information leakage.

## 4. Prompt Injection & Document Data Delimitation

All imported documents and retrieved excerpts are treated as **untrusted reference data**:
- Retrieved text is delimited using strict XML `<retrieved_context>` tags.
- System instructions explicitly direct the model to treat retrieved passages as reference data that cannot override system safety policy or issue commands.
- The assistant is isolated from shell execution or autonomous tool dispatch.

## 5. Append-Only Audit Logging

All security-relevant events (authentication, model state changes, document uploads, collection modifications, and API calls) are written to the append-only `audit_events` relational table with:
- Timestamp (UTC)
- Actor ID & IP address
- Action & Request ID
- Result (`success` / `failure`)
- Execution latency
