# Semantic screening and security review

The injection guard masks known PII and checks deterministic attack patterns
before calling a dedicated, tool-free semantic classifier. Only the current
masked message is sent; order identifiers are replaced. Conversation history,
database records, credentials, and application prompts are not provided to it.
The Groq request has a 10-second network timeout, no retries, and a token limit.

Verdicts must satisfy a strict JSON schema with finite confidence, consistent
category/boolean values, and evidence taken from the supplied text. The 0.85
acceptance threshold is a heuristic requiring evaluation, not a measured attack
probability. Invalid, uncertain, low-confidence, or unavailable verdicts hold
execution for review. They do not authorize a transaction or prove an attack.
The classifier itself remains susceptible to adversarial inputs.

Closed gaps:

- Blocked input no longer reaches the translation model.
- Known PII is removed from model-bound history, stored turn messages, API JSON,
  and streaming events. Semantic logs contain categories, not model explanations.
- Model-generated order IDs cannot select transaction targets. Cross-account
  order amounts are not pulled into triage results.
- RAG and grounding separate trusted instructions from untrusted content.
  Grounding accepts exact YES or verbatim source extracts, not word overlap.
- Refund amounts must be finite, positive, and within the original order total.
- Arbitrary supervisor-looking strings are rejected by a demo ID allowlist.
- Failed refund tool execution is not described by the graph as successful.

Remaining deployment requirements:

- The application still uses demo identities supplied by clients. Authenticate
  users and supervisors, bind sessions to verified identities, and authorize
  chat history, audit, approvals, and administrative endpoints server-side.
  An allowlisted ID is not proof of identity. This must be solved in code/auth,
  never by an LLM.
- Make refund eligibility and recording a single guarded transaction with
  duplicate-request protection; separate prechecks can race under concurrency.
- Current masking covers known phone/email/card/Aadhaar/OTP patterns. It is not
  comprehensive anonymization of names, addresses, or sensitive narratives.
  Masked customer text is still sent to the configured external Groq provider;
  evaluate retention and data residency before production use.
- The PII node drops raw redaction values and overwrites the current query,
  but graph input checkpoints and request transport can still capture the
  original input before that node. Define and enforce retention/redaction at
  ingestion and checkpoint storage before accepting real personal data.
- Rate-limit public endpoints and evaluate missed attacks/false positives using
  held-out multilingual payloads. Synthetic mocked verdicts do not establish
  real model detection accuracy.

Offline verification: `python tests/test_semantic_security.py`,
`python tests/test_redteam_sandbox.py`, and `python tests/test_faq_index_sync.py`.
