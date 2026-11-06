# F03 Resume Import UI

Feature-owned UI for importing and confirming proposed evidence.

`ResumeImport` uploads a PDF or Word (`.docx`) resume to `POST /api/evidence/import`. Every
record that comes back is `unconfirmed`; the Career Evidence Profile is where the job seeker
corrects, approves, or deletes them. Unsupported, corrupted, empty, or oversized files are
rejected by the API with a message that this component shows to the user.
