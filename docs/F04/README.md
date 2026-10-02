# F04 Job Description Analysis

Owner: Sampreet Ajjanagouda Patil (@Sampreet26)
Branch: `feat/F04-job-analysis`
Submission: initial contract and deterministic parser prototype

A supplied plain-text job description becomes a versioned JSON contract for F05/F06. Requirements contain categories, importance, source context and review flags. This is a local prototype, not a production AI parser or a complete authentication integration.

## Run on your Mac

Use Python 3.12 or newer and Node 22. From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e './apps/api[dev]'
python -m uvicorn app.modules.job_analysis.demo:create_demo_app --factory --app-dir apps/api --host 127.0.0.1 --port 8000
```

Keep that terminal running. Open another terminal at the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:5173/src/features/job-analysis/demo.html`.
The API's interactive documentation is at `http://127.0.0.1:8000/docs`.

The demo is deliberately a separate app. The shared production app and the shared frontend home remain unchanged. Do not deploy the demo publicly. F01 authentication must be connected before mounting this router in the authenticated product.

## Demonstration

1. Select **Load sample posting**, then **Analyze requirements**.
2. Review the skills, education, experience and responsibility records.
3. Confirm that required, preferred and optional sections produce their corresponding importance values.
4. Open a source context and compare it with the input text.
5. Download the JSON result for a downstream consumer.
6. Try `Qualifications:` followed by `Python or Java` on a new line. The alternatives remain together and are flagged for review.
7. Try `SQL required but preferred`. Conflicting priority cues produce null importance and a review flag.
8. Try a punctuation-only input or a plain paragraph without requirements. The API returns a clear 422 error.

No API key, database, real resume or external AI service is needed. The analysis is not persisted.

## Requirement coverage

| SRS requirement | Prototype behavior | Verification |
|---|---|---|
| Req-Func-Sw-18 | POST `/api/f04/analyze` accepts a supplied plain-text job description | API and invalid-input tests |
| Req-Func-Sw-19 | Categories cover skill, education, experience, responsibility and qualification | Two representative posting fixtures |
| Req-Func-Sw-20 | Critical, Preferred and Optional values; explicit statements override section defaults | Importance and ambiguity tests |
| Req-Func-Sw-21 | Exact source text, start/end character offsets, line and section | Source offset tests including CRLF and Unicode bullets |
| Req-Func-Sw-22 | Review screen shows requirements, priorities, evidence context and review reasons | Frontend interaction tests and local demo |

An unstated or contradictory importance is null rather than a guessed category. This is an explicit prototype contract decision requiring team agreement before production integration of Req-Func-Sw-20.

## Stable consumer contract

Python consumers import only DTOs:

```python
from app.modules.job_analysis.contracts import AnalysisResult

analysis = AnalysisResult.model_validate(payload)
for requirement in analysis.requirements:
    if requirement.needs_review:
        continue  # Route to review; do not silently treat ambiguity as mandatory.
    # Match requirement.text and requirement.categories against approved evidence.
```

F05/F06 must not import `parser.py`, regexes or parsing helpers. `analysis-result.schema.json` describes the same public DTOs for non-Python consumers. `example-result.json` is a generated result from the software-engineer fixture. Frontend consumer types are in `contract.ts`.

- `schema_version`: `1.0`. Breaking field or semantic changes require a schema version change and coordinated review.
- `document_id`: SHA-256 of the original input, identifying a particular text revision.
- `id`: deterministic within a document revision. IDs may change when preceding input text changes; use `(document_id, id)` as the composite reference.
- `categories`: one or more category values because a clause can combine education and experience. These are classifications, not separate mandatory conditions.
- `importance`: `Critical`, `Preferred`, `Optional`, or null when unclear.
- `importance_basis`: explicit wording, section heading, unspecified or conflicting.
- `source.start` / `source.end`: zero-based Python Unicode character offsets, end excluded. Slice the original text, not a trimmed copy. JavaScript offsets use UTF-16; convert with `Array.from(original).slice(start, end).join("")` when needed. The UI displays `source.text` directly.
- `experience`: numeric values normalized to years. A stated amount without a bound is `stated_years`, not a claim that exactly that amount is mandatory. Ranges retain both bounds. Multiple alternatives retain their text and are flagged instead of collapsed into one range.
- `needs_review` / `review_reasons`: explicit ambiguity indicators. Keep `or` alternatives together; they are not an AND list.

An F04 producer calls `service.analyze_job_description(AnalysisRequest(...))`. The REST response uses the same `AnalysisResult` contract. Errors return HTTP 422 with a nonempty `detail`.

## Validation and prototype limits

Input must be a nonempty string of at most 50,000 characters without unsupported control characters. HTML/markup and JSON documents must be converted to plain text first. Whitespace is preserved for source offsets. Plain text with no recognizable requirement signals returns an explanatory validation error.

The parser uses English section headings, phrase rules and a limited skill signal vocabulary. It splits line/bullet entries and semicolon clauses, preserves alternatives, and skips recognized company/benefit sections. It does not provide general NLP understanding, an exhaustive skill taxonomy, PDF parsing, multilingual support or reliable interpretation of arbitrary prose. Review is required before matching; broader corpora and extraction quality measurements are follow-on work. No claim of extraction accuracy is made.

## Shared-file change and integration

`apps/web/vite.config.ts` adds a localhost API proxy and an independently built demo HTML entry. This is the only shared application configuration change. Backend and frontend implementation stays in the assigned job-analysis directories. No F13 files are included.

The standalone demo checks for `APP_ENV=development`. Normal product authentication is not bypassed: the router is not registered in `app.main`. F01 and the Technical Manager should agree on the authenticated route integration. F05/F06 consume only the public contract or its serialized output.

## Verification commands

From the root after creating the virtual environment:

```bash
cd apps/api
../../.venv/bin/ruff check .
../../.venv/bin/pytest -q
cd ../web
npm run lint
npm test -- --run
npm run build
```

The submission includes unit/API tests for representative postings, exact source context, ambiguous alternatives, conflicting importance, experience ranges, malformed/empty/oversized inputs, deterministic IDs, DTO serialization and parser-independent consumer imports. UI tests cover sample loading, result/source display, stale-result notices and API errors.
