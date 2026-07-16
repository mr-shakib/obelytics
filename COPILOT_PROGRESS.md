# Copilot MVP Progress Tracker

Last updated: 2026-07-16

## Target

Deliver a persistent, role-aware, read-only OBE copilot using the DeepSeek API, with a ChatGPT-style streaming interface.

## Progress

- [x] Define MVP scope and delivery phases.
- [x] Verify current DeepSeek Chat Completions, streaming, and tool-call API contract.
- [x] Add `copilot` PostgreSQL schema and persistence models.
- [x] Add conversation and message CRUD APIs.
- [x] Add organization/user ownership enforcement.
- [x] Add DeepSeek provider configuration and streaming client.
- [x] Add permission-aware system context.
- [x] Add initial permission-aware read-only OBE context retrieval.
- [ ] Add model-selected function/tool calling for broader OBE queries.
- [x] Build conversation sidebar and chat interface.
- [x] Add streamed response rendering.
- [ ] Add conversation rename/archive/delete controls.
- [x] Add backend tests for conversation lifecycle and owner isolation.
- [x] Run frontend typecheck, lint, and production build.

## Provider Decision

- Provider: DeepSeek
- API format: OpenAI-compatible Chat Completions
- Base URL: `https://api.deepseek.com`
- Initial model: `deepseek-v4-flash`
- Transport: Server-Sent Events (SSE)
- Secrets: backend environment variables only

## Current Work

Implementing model-selected function/tool calling and broader OBE queries.

## Verification Log

- Backend Ruff checks: passed
- Copilot integration tests: 2 passed
- Frontend TypeScript: passed
- Frontend ESLint for changed copilot files: passed
- Frontend production build: passed (`/copilot` generated successfully)

## Deferred Beyond MVP

- pgvector and document ingestion
- MinIO evidence indexing
- confirmed write actions
- email and notification sending
- long-conversation summarization
- advanced evaluation and quota dashboards
