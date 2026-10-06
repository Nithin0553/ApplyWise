# F14 Sharing UI

Feature-owned UI for controlled peer-review sharing and feedback.

`ShareManager` is an owner-facing, prop-driven component. It displays share lifecycle state,
emits create/revoke/copy actions, and may display a newly created share URL supplied by its
parent. It does not persist the URL or secret itself.

`PeerFeedbackPanel` displays feedback attached to one saved resume version. Supplying an
`onSubmitFeedback` callback enables the reviewer form; omitting it gives the owner a read-only
feedback history. The component does not make role decisions itself.

F01 remains responsible for authenticated Job Seeker/Reviewer identity and authorization.
F10 remains responsible for rendering the actual resume beside the reviewer feedback surface.
The F14 UI therefore does not invent authentication, fetch Career Evidence Profile data, or
implement a temporary document renderer.
