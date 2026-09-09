# Repository-analysis prompt contract

This is the reusable prompt reference for `code-repository-analyzer`; runtime behavior is
defined by the sibling `SKILL.md` loaded by the existing Skill loader.

Route source facts to CodeGraph and natural-language design facts to OpenViking. For an
implementation-versus-design question, collect both evidence sets before judging. Use
`COMPLIANT`, `PARTIALLY_COMPLIANT`, `NON_COMPLIANT`, `UNKNOWN`, or `DOCUMENT_OUTDATED` only
when the cited evidence supports that label. Every code claim needs a file path and symbol;
every documentation claim needs an OpenViking URI.
