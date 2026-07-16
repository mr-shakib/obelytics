# Role-Aware OBE Copilot Implementation Plan

## Purpose

Build a role-aware OBE copilot with persistent ChatGPT-style conversations, structured access to application data, retrieval over institutional documents, and safely confirmed actions.

The copilot should assist users according to their existing permissions and organizational scope. It should begin as a read-only assistant and gradually gain the ability to prepare drafts and execute explicitly confirmed actions.

## Core Architecture

```text
Chat UI
   │
   ▼
FastAPI Agent API
   ├── Authentication and role scope
   ├── Conversation memory
   ├── Agent orchestration
   ├── Read-only OBE tools
   ├── Confirmed action tools
   └── Audit logging
          │
          ├── Existing PostgreSQL data
          ├── Vector knowledge base
          ├── MinIO documents
          └── LLM provider
```

The agent should never query arbitrary database tables using model-generated SQL. It should receive predefined, permission-aware tools such as:

- `get_course_outcomes`
- `analyze_co_po_mapping`
- `find_incomplete_delivery_plans`
- `get_pending_approvals`
- `get_attainment_summary`
- `search_accreditation_evidence`
- `draft_notification`
- `create_course_outcome_draft`

## Phase 1: Agent Foundation

Create a new backend module:

```text
backend/app/modules/copilot/
├── router.py
├── service.py
├── agent.py
├── tools/
├── models.py
├── schemas.py
├── prompts.py
└── retrieval.py
```

Initial endpoints:

```text
POST   /api/v1/copilot/conversations
GET    /api/v1/copilot/conversations
GET    /api/v1/copilot/conversations/{id}
PATCH  /api/v1/copilot/conversations/{id}
DELETE /api/v1/copilot/conversations/{id}

GET    /api/v1/copilot/conversations/{id}/messages
POST   /api/v1/copilot/conversations/{id}/messages
POST   /api/v1/copilot/conversations/{id}/stream
POST   /api/v1/copilot/actions/{id}/confirm
POST   /api/v1/copilot/actions/{id}/reject
```

Use Server-Sent Events for streaming responses. SSE is simpler than WebSockets for one-way token streaming and works well with FastAPI and Next.js.

## Phase 2: Persistent Conversation Storage

Add a new PostgreSQL schema named `copilot`.

### `copilot.conversations`

- `id`
- `organization_id`
- `user_id`
- `title`
- `course_id`, nullable
- `program_id`, nullable
- `batch_id`, nullable
- `academic_term_id`, nullable
- `status`: active or archived
- `created_at`
- `updated_at`
- `last_message_at`

### `copilot.messages`

- `id`
- `conversation_id`
- `role`: user, assistant, system, or tool
- `content`
- `model`
- `status`: streaming, complete, or failed
- `token_usage`
- `tool_calls`, JSONB
- `citations`, JSONB
- `created_at`

### `copilot.action_requests`

This table stores proposed operations requiring user confirmation:

- `id`
- `conversation_id`
- `message_id`
- `tool_name`
- `arguments`, JSONB
- `risk_level`
- `status`: pending, confirmed, rejected, executed, or failed
- `confirmed_by`
- `confirmed_at`
- `result`, JSONB

### `copilot.conversation_summaries`

This table stores compressed memory for long conversations:

- `conversation_id`
- `summary`
- `through_message_id`
- `updated_at`

Messages should be immutable after completion. Deletion can use soft deletion or organization-level retention policies.

## Phase 3: ChatGPT-Style Frontend

Create a route such as `/copilot`.

Suggested layout:

```text
┌─────────────────┬──────────────────────────────────────┐
│ New conversation│ Conversation title                   │
│ Search chats    │                                      │
│                 │ User message                         │
│ Today           │ Assistant response                   │
│ Previous 7 days │ Sources and suggested actions        │
│ Older           │                                      │
│                 │                                      │
│ Settings        │ [ Attach ] [ Message... ] [ Send ]   │
└─────────────────┴──────────────────────────────────────┘
```

Features:

- Conversation sidebar
- New, rename, archive, and delete conversation
- Streaming assistant messages
- Markdown, tables, and code rendering
- Stop generation and regenerate
- Copy response
- Suggested prompts
- Source citations
- Tool execution indicators
- Confirmation cards for write operations
- Course/program context indicator
- Mobile drawer for conversation history
- Automatic conversation titles
- Paginated message loading

Also add a compact copilot drawer that can open from course, result, mapping, and accreditation pages. It should pass the current page context when starting a conversation.

## Phase 4: Role-Aware Behavior

Do not rely only on role names. Use the existing permission manifest and resource scope.

For every request, construct an authorization context:

```json
{
  "organization_id": "...",
  "user_id": "...",
  "permissions": ["co.read", "co.create"],
  "program_ids": ["..."],
  "course_ids": ["..."],
  "active_program_id": "...",
  "page_context": {
    "route": "/courses/123/mappings",
    "course_id": "123"
  }
}
```

Apply authorization twice:

1. The agent only sees tools permitted for the user.
2. Every tool independently validates permissions and resource scope.

Example behavior by role:

- A teacher can read assigned sections and draft course content.
- A Module Leader can inspect assigned courses and review section submissions.
- A Program Coordinator can analyze authorized programs.
- A student can only access their own published results.
- A Super Admin can operate across the organization, subject to explicit permissions.

Never accept `organization_id`, accessible program IDs, or course scope directly from the model. Derive these values from the authenticated user.

## Phase 5: Using PostgreSQL as a Knowledge Base

Use structured retrieval and semantic retrieval together.

### 5.1 Structured Retrieval

For live application facts, use normal SQLAlchemy services through controlled tools.

Examples:

- Current pending approvals
- Course outcomes
- CO-PO mappings
- Delivery-plan completion
- Published results
- Attainment percentages
- Assigned teachers

This is more accurate than embeddings for structured data.

The agent should call tools such as:

```text
get_course_context(course_id)
get_attainment_trends(program_id, term_range)
find_missing_course_configuration(program_id)
```

Each tool returns compact JSON that the model can explain.

### 5.2 Semantic Retrieval with pgvector

Use PostgreSQL with the `pgvector` extension for unstructured knowledge:

- Accreditation policies
- BAETE manuals
- Course outlines
- Self-study reports
- Meeting minutes
- Institutional policies
- Teacher feedback
- Improvement plans
- Uploaded evidence

Suggested tables follow.

### `copilot.knowledge_sources`

- `id`
- `organization_id`
- `title`
- `source_type`
- `storage_key`
- `mime_type`
- `program_id`, nullable
- `course_id`, nullable
- `access_scope`
- `status`
- `content_hash`
- `created_by`
- `created_at`

### `copilot.knowledge_chunks`

- `id`
- `source_id`
- `organization_id`
- `content`
- `embedding vector(...)`
- `page_number`
- `section_title`
- `metadata`, JSONB
- `token_count`

Documents remain in MinIO. Extracted text and embeddings reside in PostgreSQL.

## Retrieval Pipeline

When a user asks a question:

1. Authenticate the user.
2. Determine organization and resource scope.
3. Classify the request.
4. Query structured tools if live OBE data is required.
5. Generate an embedding for semantic questions.
6. Search only permitted knowledge chunks.
7. Optionally combine vector similarity with PostgreSQL full-text search.
8. Rerank the retrieved chunks.
9. Generate an answer with citations.
10. Record the response, tool calls, and sources.

A hybrid query should combine:

- Vector similarity
- PostgreSQL full-text relevance
- Organization filter
- Program/course scope
- Document type
- Recency where relevant

Every knowledge query must include `organization_id`. Program and course constraints must be applied before results reach the model.

## Converting Database Records into Knowledge

Do not embed every database row. Frequently changing structured records should remain accessible through tools.

Create searchable documents only for records where semantic understanding helps, such as:

```text
Course: CSE 321
CO: CO2
Statement: Analyze distributed system failure modes.
Bloom levels: Analyze
Mapped POs: PO2, PO5
```

Refresh these derived documents through the existing outbox/event system when:

- A CO is published
- A mapping is approved
- A course outline changes
- A result is published
- An improvement action is recorded

Use deterministic source identifiers so an existing embedding is replaced instead of duplicated.

## Phase 6: Initial Agent Tools

Start with read-only tools.

### Course Design

- Get course configuration
- Analyze CO wording
- Suggest Bloom levels
- Suggest CO-PO mappings
- Check delivery-plan coverage
- Identify missing course information

### Results and Attainment

- Summarize section results
- Compare CO attainment
- Explain PO attainment
- Detect unusual changes
- Identify outcomes below thresholds

### Approvals

- Summarize pending approvals
- Compare submitted and previous versions
- Highlight validation issues
- Draft reviewer feedback

### Accreditation

- Search evidence
- Find missing evidence
- Summarize documents
- Draft report sections with citations

## Phase 7: Confirmed Actions

After read-only tools are stable, add write tools:

- Save a CO as a draft
- Update a delivery-plan draft
- Create a mapping draft
- Draft an in-app notification
- Send a confirmed notification
- Create an improvement action

Execution sequence:

```text
Agent proposes action
       ↓
UI displays exact changes
       ↓
User confirms
       ↓
Backend rechecks permission
       ↓
Action executes
       ↓
Audit event is recorded
```

Marks, result publication, approvals, role changes, and destructive operations should initially remain outside agent control.

## Phase 8: Communication

The agent can identify the responsible person using assignments already stored in the database.

Example interaction:

> Three sections have not submitted their end reports. Would you like me to draft reminders for the assigned teachers?

The agent should:

1. Find responsible users through assignment records.
2. Draft personalized messages.
3. Show recipients and message bodies.
4. Require confirmation.
5. Send through the existing notification module.
6. Log delivery and confirmation.

Email integration can be added later. Start with in-app notifications.

## Security and Governance

Required protections:

- Organization isolation
- Permission and program/course scope checks
- No unrestricted model-generated SQL
- No raw database credentials exposed to the model
- Encryption for stored provider credentials
- Configurable chat retention
- PII filtering where appropriate
- Prompt-injection defenses for uploaded documents
- Full audit trail
- Provider request and token logging without exposing secrets
- Rate limits and organization usage quotas
- Clear AI-generated labels
- Human confirmation for mutations

## Recommended Delivery Order

1. Conversation and message persistence
2. ChatGPT-style streaming interface
3. Authentication, permission, and page context
4. Read-only structured OBE tools
5. PostgreSQL/pgvector knowledge base
6. Document ingestion from MinIO
7. Citations and source viewer
8. Course-design assistant
9. Attainment and approval analysis
10. Confirmed draft actions
11. In-app communication
12. Monitoring, evaluations, and usage controls

## Recommended First Release

The first release should be a persistent, read-only copilot that answers questions about courses, mappings, delivery plans, approvals, and attainment.

Once its authorization and accuracy are proven, enable draft creation and confirmed communication. Fully autonomous messaging, approvals, result publication, marks modification, and destructive operations should remain disabled until stronger evaluation and governance controls exist.
