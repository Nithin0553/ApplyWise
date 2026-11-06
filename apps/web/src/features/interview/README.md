# F15 Interview Defensibility UI

Feature-owned UI for statement-based interview preparation.

`InterviewPrepPage` takes approved statements and renders, per statement, the
questions an interviewer is likely to ask and the supporting points drawn from
the user's own evidence.

The backend lives in `app/modules/generation/` (`interview_schemas.py`,
`interview_service.py`, `interview_router.py`). See
`docs/contracts/F15_INTERVIEW_DEFENSIBILITY_CONTRACT.md`.

**Defensibility is not verification.** A `HARD_TO_DEFEND` result means the
user's evidence does not answer the obvious follow-up question. It is advice.
F08 owns `VERIFIED / INFERRED / UNSUPPORTED` and F09 owns approval, and nothing
in this folder may render a defensibility result as either.
