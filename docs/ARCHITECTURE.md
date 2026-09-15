# ApplyWise Architecture Foundation

## Goals
The architecture protects the product vision's main constraints:
- Generated content remains traceable to approved evidence.
- Unsupported content never reaches final export.
- Users explicitly approve generated statements.
- Reviewer access is limited to one shared resume version.
- Frontend, backend, persistence, and AI responsibilities are clearly separated.
- Six developers can work in parallel with minimal file overlap.

## Chosen foundation
This repository uses a **modular monolith**:
- React + TypeScript frontend
- FastAPI backend
- PostgreSQL
- AI provider interface
- document import/export interfaces

This technology choice is an engineering decision, not a requirement stated by the source documents.

## Backend boundaries
| Module | Features |
|---|---|
| auth | F01 |
| evidence | F02, F03 |
| job_analysis | F04 |
| matching | F05, F06 |
| generation | F07, F11, F15 |
| verification | F08, F09 |
| documents | F10, F12 |
| applications | F13 |
| sharing | F14 |
| market | F16 |
| admin | templates/taxonomy/configuration |

## Hard invariants
- Imported evidence begins unconfirmed.
- Only approved evidence may support finalized generated content.
- Generated statements retain provenance.
- Verification states are VERIFIED, INFERRED, or UNSUPPORTED.
- UNSUPPORTED statements cannot be exported.
- Edited statements must be reverified.
- Verification does not equal approval.
- Explicit user approval is required for final inclusion.
- Saved resume versions preserve the evidence/provenance/approval snapshot.
- Reviewer links expose only the intended resume version and comments.
- Authorization is enforced server-side.

## Dependency rule
Modules interact through explicit service/API contracts, not by reaching into one another's tables or implementation details.
