"""Scripted provider for UI demos and offline development (``AI_PROVIDER=demo``).

It stands in for a language model: it rewrites each evidence item into a
resume-style statement, orders statements by how well they match the job, and
leads with the job requirement each one speaks to. It never adds a fact that is
not in the evidence it cites.

Two of its outputs are deliberately ungrounded — one cites an evidence
reference that was never supplied, one cites nothing at all — so the
generation service's rejection path can be seen in the UI.

Offline and deterministic: no network call, no API key, same output for the
same input. A real model plugs in beside it behind ``AIProvider``.
"""

from __future__ import annotations

from .provider import (
    CoverLetterRequest,
    CoverLetterResponse,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    RawParagraph,
    RawStatement,
)

# Past tense -> gerund, so two clauses can be joined with "while".
_GERUNDS = {
    "built": "building",
    "created": "creating",
    "designed": "designing",
    "developed": "developing",
    "delivered": "delivering",
    "led": "leading",
    "maintained": "maintaining",
    "owned": "owning",
    "automated": "automating",
    "supported": "supporting",
    "wrote": "writing",
    "used": "using",
    "ran": "running",
    "tested": "testing",
}

_STOPWORDS = frozenset(
    {
        "and",
        "for",
        "the",
        "with",
        "you",
        "our",
        "will",
        "this",
        "that",
        "work",
        "years",
        "experience",
        "strong",
        "familiarity",
        "required",
        "preferred",
    }
)


def _segments(text: str) -> dict[str, str]:
    """Split a flattened evidence line into its labelled parts."""
    parts = [part.strip() for part in text.split("|") if part.strip()]
    head = parts[0]
    if head.startswith("["):
        head = head.split("]", 1)[-1].strip()

    etype = ""
    if parts[0].startswith("["):
        etype = parts[0].split("]", 1)[0].lstrip("[").strip().upper()

    found = {"title": head, "detail": "", "etype": etype}
    labels = (
        "role",
        "organization",
        "location",
        "skill",
        "proficiency",
        "credential",
        "dates",
    )
    for part in parts[1:]:
        for label in labels:
            if part.startswith(f"{label}:"):
                found[label] = part.removeprefix(f"{label}:").strip()
                break
        else:
            # Unlabelled segment: the description.
            found["detail"] = part

    # Skill and certification evidence often carries no description. Build one
    # from the structured fields so the statement still says something real.
    if not found["detail"]:
        if found.get("skill"):
            level = found.get("proficiency")
            found["detail"] = (
                f"Used {found['skill']} at {level} level" if level else f"Used {found['skill']}"
            )
        elif found.get("credential"):
            found["detail"] = f"Holds {found['credential']}"
    return found


def _job_keywords(job_context: str) -> list[str]:
    """Phrases the job asks for, in the posting's own spelling."""
    keywords: list[str] = []
    for line in job_context.splitlines():
        if line.lower().startswith("requirements:"):
            keywords.extend(
                phrase.strip()
                for phrase in line.removeprefix("Requirements:").split(";")
                if phrase.strip()
            )
    # Fall back to notable words from the whole posting.
    if not keywords:
        for word in job_context.lower().replace(",", " ").replace(".", " ").split():
            cleaned = word.strip("()-:")
            if len(cleaned) > 4 and cleaned not in _STOPWORDS and cleaned not in keywords:
                keywords.append(cleaned)
    return keywords


def _matches(evidence_text: str, keywords: list[str]) -> list[str]:
    haystack = evidence_text.lower()
    return [keyword for keyword in keywords if keyword.lower() in haystack]


def _rewrite(detail: str, title: str) -> str:
    """Restructure the evidence into one sentence. Same facts, new shape."""
    detail = detail.strip()

    # "Used for test automation and backend services" -> a sentence with a subject.
    lowered = detail.lower()
    for prefix in ("used for ", "used in ", "used to "):
        if lowered.startswith(prefix):
            detail = f"Used {title} for {detail[len(prefix) :]}"
            break

    clauses = [clause.strip(" .") for clause in detail.split(" and ") if clause.strip(" .")]
    sentence = detail.strip(" .")

    # Lead with the second clause only when it can carry a sentence on its own.
    if len(clauses) == 2:
        lead, support = clauses[1], clauses[0]
        support_verb = support.split(" ", 1)[0].lower()
        lead_verb = lead.split(" ", 1)[0].lower()
        gerund = _GERUNDS.get(support_verb)
        if gerund and (lead_verb in _GERUNDS or lead_verb.endswith("ed")):
            rest = support.split(" ", 1)[1] if " " in support else ""
            sentence = f"{lead} while {gerund} {rest}".strip()

    sentence = f"{sentence[0].upper()}{sentence[1:]}" if sentence else ""
    return f"{sentence}." if sentence and not sentence.endswith(".") else sentence


class DemoAIProvider:
    name = "demo"

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        keywords = _job_keywords(request.job_context)

        # Rank evidence by how much of the job it speaks to.
        ranked = sorted(
            request.evidence,
            key=lambda item: len(_matches(item.text, keywords)),
            reverse=True,
        )

        statements: list[RawStatement] = []
        for item in ranked[: request.max_statements]:
            parts = _segments(item.text)
            matched = _matches(item.text, keywords)
            detail = parts["detail"] or f"Applied {parts['title']} in day-to-day work"
            sentence = _rewrite(detail, parts["title"])

            if matched:
                # Lead with the requirement this statement answers. The phrase
                # appears in both the posting and the cited evidence.
                lead = matched[0]
                sentence = f"{lead[0].upper()}{lead[1:]}: {sentence[0].lower()}{sentence[1:]}"
            elif parts.get("role") and parts.get("organization"):
                opener = f"As {parts['role']} at {parts['organization']}, "
                sentence = opener + sentence[0].lower() + sentence[1:]

            statements.append(RawStatement(text=sentence, cited_refs=(item.ref,)))

        # One statement drawing on two items: an experience plus a skill that
        # supported it. Both are cited, so the UI shows two provenance chips.
        experience = next(
            (item for item in ranked if _segments(item.text)["etype"] != "SKILL"), None
        )
        skill = next(
            (item for item in ranked if _segments(item.text)["etype"] == "SKILL"), None
        )
        if experience is not None and skill is not None:
            parts = _segments(experience.text)
            base = _rewrite(
                parts["detail"] or f"Applied {parts['title']}", parts["title"]
            ).rstrip(".")
            statements.append(
                RawStatement(
                    text=f"{base}, using {_segments(skill.text)['title']}.",
                    cited_refs=(experience.ref, skill.ref),
                )
            )

        # Teaching case: a confident, attractive claim citing a source nobody
        # supplied. The generation service must reject it.
        statements.append(
            RawStatement(
                text="Reduced production incidents by 40% through an automated release gate.",
                cited_refs=(f"E{len(request.evidence) + 7}",),
            )
        )

        # Second failure mode: fluent text with no citation at all.
        statements.append(
            RawStatement(
                text="Recognised across the organisation as a quality champion.",
                cited_refs=(),
            )
        )

        return GroundedGenerationResponse(statements=tuple(statements))

    # --- F11 cover letters -------------------------------------------------

    def generate_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResponse:
        job_title = _job_title(request.job_context)
        company = _company(request.job_context)
        voice = {
            "professional": {
                "open": "I am writing to apply for the {role} position{at_company}.",
                "bridge": "In my most recent work I",
                "body": "Alongside that, I",
                "close": "I would welcome the opportunity to discuss how this experience "
                "would serve the {role} team.",
            },
            "warm": {
                "open": "The {role} role{at_company} caught my eye, and I would love to be "
                "part of it.",
                "bridge": "Something I am proud of: I",
                "body": "I also",
                "close": "I would really enjoy talking about how this could help your team.",
            },
            "direct": {
                "open": "I am applying for {role}{at_company}. Here is what I bring.",
                "bridge": "Most recently I",
                "body": "Also, I",
                "close": "Happy to walk through any of this.",
            },
        }[request.tone]
        at_company = f" at {company}" if company else ""

        paragraphs: list[RawParagraph] = []
        statements = request.statements[: request.max_paragraphs]

        if statements:
            first = statements[0]
            paragraphs.append(
                RawParagraph(
                    text=(
                        voice["open"].format(role=job_title, at_company=at_company)
                        + f" {_as_clause(first.text, voice['bridge'])}"
                    ),
                    cited_refs=(first.ref,),
                )
            )

        middle = statements[1:-1] if len(statements) > 2 else statements[1:]
        if middle:
            sentences = " ".join(_as_sentence(item.text) for item in middle)
            body = f"{voice['body']} {sentences[0].lower()}{sentences[1:]}"
            paragraphs.append(
                RawParagraph(text=body, cited_refs=tuple(item.ref for item in middle))
            )

        if len(statements) > 2:
            last = statements[-1]
            paragraphs.append(
                RawParagraph(
                    text=(
                        f"{_as_sentence(last.text)} "
                        + voice["close"].format(role=job_title)
                    ),
                    cited_refs=(last.ref,),
                )
            )

        # Teaching case: a flattering claim citing a statement nobody approved.
        paragraphs.append(
            RawParagraph(
                text=(
                    "Colleagues consistently describe me as the person who raised the "
                    "quality bar for the whole engineering organisation."
                ),
                cited_refs=(f"S{len(request.statements) + 7}",),
            )
        )

        # Second failure mode: pleasant filler citing nothing at all.
        paragraphs.append(
            RawParagraph(
                text="I am passionate about quality and excited by this opportunity.",
                cited_refs=(),
            )
        )

        return CoverLetterResponse(paragraphs=tuple(paragraphs))


def _job_title(job_context: str) -> str:
    for line in job_context.splitlines():
        if line.lower().startswith("job title:"):
            return line.split(":", 1)[1].strip() or "the role"
    return "the role"


def _company(job_context: str) -> str:
    for line in job_context.splitlines():
        if line.lower().startswith("company:"):
            return line.split(":", 1)[1].strip()
    return ""


def _as_sentence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned if cleaned.endswith(".") else f"{cleaned}."


def _as_clause(text: str, bridge: str) -> str:
    """Reuse an approved statement as a supporting clause, unchanged in meaning."""
    cleaned = text.strip().rstrip(".")
    if not cleaned:
        return ""
    return f"{bridge} {cleaned[0].lower()}{cleaned[1:]}."
