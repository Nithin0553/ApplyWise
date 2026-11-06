# F03 Resume Import Contract

F03 turns an uploaded resume into **proposed** career evidence. It lives inside the F02 `evidence`
module (it creates records only through `EvidenceService`) and the `features/import` UI.

## Endpoint

`POST /api/evidence/import` (Job Seeker only, `multipart/form-data`, field `file`)

| Outcome | Status | `detail` / body |
|---|---|---|
| Records proposed | 201 | `{ "filename": str, "records": [EvidenceView, ...] }` |
| Not `.pdf` / `.docx` | 415 | `Only PDF (.pdf) and Word (.docx) resumes can be imported.` |
| Larger than 5 MB | 413 | `This file is larger than 5 MB. Upload a smaller PDF or Word resume.` |
| Corrupted, encrypted, image-only, or empty file | 422 | `This file could not be processed. ...` |
| Readable file with no recognizable resume sections | 422 | `No career details could be found in this file. ...` |
| No/invalid token, or Reviewer/Administrator role | 401 / 403 | same as other F02 routes |

On any error nothing is saved.

## Rules

- **Always unconfirmed (Req-Func-Sw-15).** Every imported record is created through
  `EvidenceService.create`, so it starts `UNCONFIRMED` with `approved_at = null`. Imported evidence
  does not appear in `/api/evidence/approved` or in any grounding context until the owner approves it.
- **Copy, never invent.** The parser only copies text found in the file. It does not use an AI
  provider and does not add skills, metrics, titles, or dates that are not in the file. `Present`
  leaves `end_date` empty. A year-only date is stored as 1 January (start) or 31 December (end) of
  that year, and the owner is expected to review it.
- **Correct before approval (Req-Func-Sw-16).** Imported records are ordinary F02 records, so the
  owner uses the existing edit, approve, and delete routes to correct or discard them.
- **Provenance.** Imported records have `source = "resume_import"`.
- **Notify on failure (Req-Func-Sw-17).** Error messages above are written for the job seeker and
  shown by the UI.
- **Formats (Req-Func-Sw-13).** PDF (text-based) and Word `.docx`. Legacy `.doc` is not supported.
  The file type is checked by extension and by content (`%PDF-` header, `.docx` zip with
  `word/document.xml`).

## Recognized sections

`Experience` (work experience), `Education`, `Projects`, `Certifications`, `Skills`. Other sections
are ignored. At most 100 records are proposed per upload.

## Related F02 change

`DELETE /api/evidence/{id}` (Req-Func-Sw-9) returns 204; a missing id and another user's id both
return the same 404, as for the other F02 routes. Saved resume versions keep their own snapshot, so
deleting live evidence does not change version history.
