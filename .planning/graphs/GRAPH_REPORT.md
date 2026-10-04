# Graph Report - SentinelCX  (2026-10-04)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 575 nodes · 1291 edges · 31 communities (16 shown, 15 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `08561116`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- mock_db.py
- client.ts
- server.py
- graph.py
- test_foundation.py
- package.json
- shared.py
- test_policy.py
- mask_pii
- compilerOptions
- test_security.py
- compilerOptions
- detect_language
- rag_agent.py
- TriageOutput
- pii_guard.py
- .oxlintrc.json
- test_assert_no_raw_pii_reaches_llm
- injection_guard.py
- tsconfig.json
- run_verification
- run_demo.sh

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 35 edges
2. `mask_pii()` - 35 edges
3. `reset_db()` - 31 edges
4. `get_order()` - 30 edges
5. `execute_refund()` - 26 edges
6. `get_audit_logs()` - 25 edges
7. `SupportState` - 21 edges
8. `get_refunds_for_order()` - 21 edges
9. `check_refund_policy()` - 21 edges
10. `check_injection()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `trigger_redteam()` --calls--> `run_redteam()`  [EXTRACTED]
  api/server.py → evaluation/redteam.py
- `run_redteam()` --calls--> `build_graph()`  [EXTRACTED]
  evaluation/redteam.py → core/graph.py
- `check_refund_policy()` --calls--> `evaluate_refund_policy()`  [EXTRACTED]
  tools/order_tools.py → policy/policy_gate.py
- `run_verification()` --calls--> `check_refund_policy()`  [EXTRACTED]
  tests/verify_action_layer.py → tools/order_tools.py
- `run_verification()` --calls--> `execute_refund()`  [EXTRACTED]
  tests/verify_action_layer.py → tools/order_tools.py

## Import Cycles
- None detected.

## Communities (31 total, 15 thin omitted)

### Community 0 - "mock_db.py"
Cohesion: 0.06
Nodes (28): print_redteam_table(), run_redteam(), evaluate_refund_policy(), _parse_datetime(), test_scenario_a_faq_answered_with_citations(), test_scenario_b_eligible_refund_auto_executed(), test_scenario_c_expired_order_rejected_with_policy_quote(), test_scenario_d1_high_value_refund_hitl_approve() (+20 more)

### Community 1 - "client.ts"
Cohesion: 0.07
Nodes (58): API_BASE_URL, AuditRecord, ChatResponse, Citation, fetchApprovals(), fetchAuditLogs(), fetchDemoUsers(), fetchHealth() (+50 more)

### Community 2 - "server.py"
Cohesion: 0.05
Nodes (25): ApprovalDecisionRequest, chat_stream(), sse_generator(), chat_turn(), ChatRequest, ChatResponse, decide_approval(), get_demo_users() (+17 more)

### Community 3 - "graph.py"
Cohesion: 0.09
Nodes (25): _extract_amount_from_query(), _heuristic_triage_fallback(), triage_agent(), generate_handoff_dossier(), auto_execute_node(), build_graph(), build_why_decision(), escalate_node() (+17 more)

### Community 4 - "test_foundation.py"
Cohesion: 0.08
Nodes (18): confidence_agent(), get_embeddings(), get_retriever(), get_vectorstore(), load_retriever(), resolve_doc_path(), retrieve_with_scores(), compiled_graph() (+10 more)

### Community 5 - "package.json"
Cohesion: 0.05
Nodes (39): dependencies, clsx, framer-motion, lucide-react, react, react-dom, recharts, tailwind-merge (+31 more)

### Community 6 - "shared.py"
Cohesion: 0.10
Nodes (16): graph(), test_faq_verifiable_answer_and_citations(), test_ui_panels_render(), test_unanswerable_query_routes_to_handoff(), render_customer_portal(), render_message_item(), add_message(), get_badge_html() (+8 more)

### Community 7 - "test_policy.py"
Cohesion: 0.11
Nodes (17): clean_database(), record_result(), test_adversarial_llm_fakes_supervisor_approval_on_high_value(), test_adversarial_llm_proposes_refund_for_ineligible_order(), test_already_refunded_order(), test_cancelled_order(), test_cross_user_order_ownership_mismatch(), test_eligible_order_delivered_3_days_ago() (+9 more)

### Community 8 - "mask_pii"
Cohesion: 0.08
Nodes (18): mask_pii(), test_pii_aadhaar_continuous(), test_pii_aadhaar_hyphenated(), test_pii_aadhaar_spaced(), test_pii_card_mastercard_luhn_checked(), test_pii_card_visa_luhn_checked(), test_pii_email_complex_plus_subdomain(), test_pii_email_standard() (+10 more)

### Community 9 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 10 - "test_security.py"
Cohesion: 0.18
Nodes (13): check_injection(), setup_test_db(), test_injection_english_act_as_admin(), test_injection_english_approve_my_refund(), test_injection_english_bypass_policy(), test_injection_english_dan_mode(), test_injection_english_developer_message(), test_injection_english_ignore_instructions() (+5 more)

### Community 11 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 12 - "detect_language"
Cohesion: 0.33
Nodes (7): intent_agent(), test_hinglish_query_1_refund_parcel_not_delivered(), test_hinglish_query_2_login_forgot_password(), test_hinglish_query_3_subscription_cancel(), test_hinglish_query_4_billing_double_charge(), test_hinglish_query_5_refund_timeline(), detect_language()

### Community 13 - "rag_agent.py"
Cohesion: 0.36
Nodes (5): is_grounded(), rag_agent(), rewrite_query(), build_citation(), normalize_to_english()

### Community 16 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 17 - "test_assert_no_raw_pii_reaches_llm"
Cohesion: 0.33
Nodes (4): make_mock_llm_response(), test_assert_no_raw_pii_reaches_llm(), mock_invoke_capture(), test_hinglish_rag_reply_style_instruction()

## Knowledge Gaps
- **82 isolated node(s):** `ChatResponse`, `DemoScenarioChipsProps`, `ScenarioChip`, `ScenarioDefinition`, `NodeConfig` (+77 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 243 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `graph.py` to `mock_db.py`, `server.py`, `test_foundation.py`, `shared.py`, `test_security.py`, `test_assert_no_raw_pii_reaches_llm`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `reset_db()` connect `mock_db.py` to `server.py`, `graph.py`, `shared.py`, `test_policy.py`, `test_security.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `mask_pii()` connect `mask_pii` to `mock_db.py`, `server.py`, `graph.py`, `test_security.py`, `detect_language`, `rag_agent.py`, `pii_guard.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `build_graph()` (e.g. with `auto_execute_node()` and `safe_invoke()`) actually correct?**
  _`build_graph()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `mask_pii()` (e.g. with `replace_otp_bwd()` and `replace_otp_fwd()`) actually correct?**
  _`mask_pii()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ChatResponse`, `DemoScenarioChipsProps`, `ScenarioChip` to the rest of the system?**
  _82 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `mock_db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06288568909785483 - nodes in this community are weakly interconnected._