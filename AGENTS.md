# AGENTS.md — JSP Digital Intelligence Platform

Authoritative engineering guidelines, architecture contracts, security guardrails, and verification workflows for autonomous agents and contributors working on the `avinash2you/jspdigitalteam` repository.

## 1. Monorepo Architecture & Directory Structure

```
.
├── apps/
│   ├── web/               # Next.js 15+ App Router, TypeScript (strict), Tailwind CSS
│   └── api/               # Python 3.11+ FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2
├── packages/
│   └── shared/            # Shared TypeScript schemas, enums, and validation contracts
├── tools/                 # Build and migration automation scripts
├── docker-compose.yml     # Local dev: PostgreSQL 16 + pgvector, MinIO, Mailpit
├── pnpm-workspace.yaml    # Node workspace orchestration
└── AGENTS.md              # Root architectural instructions (this file)
```

- **/apps/web**: Next.js App Router front-end with Clerk authentication, Tailwind CSS, TanStack Query, and Vitest.
- **/apps/api**: FastAPI backend serving authenticated REST endpoints, executing background pipelines, and enforcing domain logic.
- **/packages/shared**: Source of truth for shared schemas and enums (e.g., `UserRole`, `AssetType`, `VerificationStatus`).

## 2. Swappable Adapter Interfaces

All external cloud and AI integrations must be implemented against abstract `typing.Protocol` interfaces under `/apps/api/app/adapters/base.py` and resolved via `/apps/api/app/adapters/registry.py`. Direct vendor imports in route handlers or domain services are strictly forbidden.

### 2.1 StorageProvider
Selected via `STORAGE_BACKEND` (e.g., `r2`, `minio`, `mock`):
- `generate_upload_url(key: str, content_type: str, expires_sec: int = 900) -> str`
- `generate_download_url(key: str, expires_sec: int = 900) -> str`
- `head_object(key: str) -> ObjectMetadata`
- `delete_object(key: str) -> None`

### 2.2 OCRProvider
Selected via `OCR_BACKEND` (e.g., `tesseract`, `document_ai`, `mock`):
- `extract_text(file_bytes: bytes, mime_type: str, languages: list[str]) -> OCRResult`
  - Returns `OCRResult(full_text: str, pages: list[OCRPage], boxes_json: dict)`

### 2.3 SearchProvider
Selected via `SEARCH_BACKEND` (e.g., `postgres_hybrid`, `meilisearch`, `mock`):
- `index_asset(asset_doc: AssetSearchDocument) -> None`
- `delete_asset(asset_id: str) -> None`
- `search(query: str, filters: SearchFilters, limit: int = 20, offset: int = 0) -> SearchResponse`

### 2.4 AIProvider
Selected via `AI_BACKEND` (e.g., `gemini_free`, `gemini_paid`, `mock`):
- `extract_metadata_and_summary(text_or_bytes: str | bytes, asset_type: str, is_public: bool) -> AIExtractionResult`

## 3. RBAC, Security & Data Privacy Guardrails

1. **6-Role Server-Side RBAC**: Every FastAPI endpoint must validate the Clerk JWT and enforce role requirements server-side:
   - `super_admin`: Full system, tenant, user, and audit access.
   - `admin`: User management, taxonomy config, ingestion approval.
   - `researcher`: Read-write search, dossiers, annotations, asset upload.
   - `reviewer`: OCR verification, fact checking, quality sign-off.
   - `contributor`: Asset submission, metadata tagging.
   - `viewer`: Read-only access to published public assets.
2. **Private R2 Buckets Only**: Cloudflare R2 buckets must remain private (zero public read access). All file uploads and downloads must use short-lived presigned URLs generated server-side after RBAC verification.
3. **Immutable Audit Logs**: All read, upload, edit, review, and download actions must emit an append-only row into `audit_logs` (user ID, action, asset ID, IP, timestamp). No update or delete operations on audit records.
4. **Free-Tier AI Privacy Boundary**: Assets marked confidential or restricted MUST NEVER be transmitted to external free-tier AI APIs (such as Gemini Free Tier). Only public/non-confidential documents may use free-tier extraction.
5. **No Secret Commits**: Never commit `.env` files, API keys, or credentials. Always verify with `git status` and `git diff` prior to commit.

## 4. Verification Commands

Before opening any PR or pushing to `main`, every applicable verification command must pass with zero errors:

- **Web (Next.js)**:
  ```bash
  pnpm --filter web lint && pnpm --filter web typecheck && pnpm --filter web test
  ```
- **API (FastAPI)**:
  ```bash
  cd apps/api && ruff check . && mypy app && pytest
  ```

## 5. Explicit Phase 1 Non-Goals

Do NOT implement, scaffold, or integrate any of the following:
- Automated social media posting or account management
- WhatsApp bots or messaging automation
- Election campaign management workflows
- Voter databases, voter lists, or voter profiling
- Public self-registration (invite-only system only)
- Native mobile applications (iOS/Android)
- Real-time social sentiment scraping or monitoring
