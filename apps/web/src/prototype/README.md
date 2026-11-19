# Early interface prototype

This folder holds the first clickable prototype of the application, built
before the backend existed. Its pages read from a local mock store rather than
from the API, which let the team agree the screen flow and the wording of each
step while the server modules were still being written.

It is retained as a record of that design stage. **It is not part of the
running application:** no page here is routed, and nothing outside this folder
imports from it. The one exception is `softly.css`, which holds base styles the
delivered interface still uses and is imported by `App.tsx`.

The flow prototyped here — evidence, job description, match, review, resume,
cover letter, tracker — is the flow the delivered application implements, in
`src/features/`. Where the two differ, `src/features/` is correct.
