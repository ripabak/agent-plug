# Feature PRD: PDF Upload for Knowledge Base

## 1. Feature Name
PDF document upload as RAG knowledge source

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** Users can currently only feed the agent URLs. Many knowledge bases live in PDF files (product manuals, pricing sheets, policies) that are not easily indexable via URL.
**Solution:** Let users upload multiple PDF files per agent. Files are stored on disk, parsed to text (pypdf), then chunked/embedded exactly like URL sources — same per-agent `InMemoryVectorStore`, same status lifecycle, same citations.
**Impact:** Broader content coverage with zero extra setup; the RAG pipeline stays unified (kind=url | kind=pdf).

## 4. User Personas
- Maker / Developer
- Business Owner

## 5. User Stories
- As a user, I want to upload one or more PDFs so that the agent can answer from them.
- As a user, I want to see the indexing status per file (queued/reading/indexing/ready/failed) so that I know when it is usable.
- As a user, I want to remove a PDF source so that the agent stops using it.

## 6. Requirements
### Functional
- `POST /api/agents/{id}/sources/files` — multipart upload of 1..5 PDFs; validates extension `.pdf` and per-file size ≤ 10MB.
- Files stored under `backend/uploads/{agent_id}/` with unique names; source row `kind=pdf` with `file_name`/`file_size`.
- Indexing pipeline branches on `kind`: `url` → HTML fetch+parse, `pdf` → read stored file + parse with pypdf (per-page text join). Chunk/embed/store identical to URLs; chunks carry `url = file://…` + title metadata.
- Startup rebuild re-indexes PDFs from disk (no network).
- Delete source removes the file from disk too.
- `SourceResponse` exposes `kind`, `file_name`, `file_size`.
### Non-Functional
- Idempotent DB migration (ALTER ... ADD COLUMN IF NOT EXISTS) for existing dev databases.
- `uploads/` gitignored; per-agent subdirectories.
- No executable content executed (pypdf text extraction only).

## 7. Acceptance Criteria
- [ ] Uploading PDFs creates pending sources (kind=pdf) and saves files to disk.
- [ ] Non-PDF extension / oversized file → 422 with clear error, nothing created.
- [ ] Pipeline parses a real PDF to text and indexes chunks with `file://` source metadata (unit test with crafted PDF).
- [ ] Status reaches `ready` with chunk_count > 0 (pipeline test with fake embeddings).
- [ ] Deleting a PDF source removes its chunks and the file on disk.
- [ ] Frontend Knowledge tab shows an upload zone and PDF sources distinguishable from URLs.
- [ ] All backend + frontend tests pass.

## 8. Out of Scope
- DOCX/XLSX/other formats, OCR for scanned PDFs, file versioning, cloud storage (S3).
