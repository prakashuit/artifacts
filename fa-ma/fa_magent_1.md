# Enterprise Agent Framework: Implementation Guide & Visual Reference
## Supplementary Document - Diagrams, Technical Details, and Implementation Patterns

---

## Table of Contents

1. [Visual Architecture Diagrams](#visual-architecture-diagrams)
2. [Tool Implementation Details](#tool-implementation-details)
3. [Workflow Execution Patterns](#workflow-execution-patterns)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Deployment Architecture](#deployment-architecture)
6. [Security & Access Control](#security--access-control)
7. [Code Examples & Patterns](#code-examples--patterns)
8. [Monitoring & Observability](#monitoring--observability)
9. [Integration Patterns](#integration-patterns)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## 1. Visual Architecture Diagrams

### 1.1 Conceptual Architecture - The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS USER LAYER                              │
│                                                                           │
│  "Reconcile yesterday's trades"  →  "Generate MiFID report"             │
│  "Process dividend for AAPL"     →  "Resolve failed settlements"        │
│                                                                           │
│                    [Natural Language Instructions]                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENT AGENT LAYER                               │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    FOUNDATIONAL AGENT                              │ │
│  │                                                                     │ │
│  │  "I understand you want to reconcile trades. Let me break this    │ │
│  │   down into steps:                                                 │ │
│  │   1. Query database for settled trades                            │ │
│  │   2. Fetch custodian confirmations via API                        │ │
│  │   3. Match trades to confirmations                                │ │
│  │   4. Create breaks for unmatched items                            │ │
│  │   5. Generate reconciliation report"                              │ │
│  │                                                                     │ │
│  │  [Task Planning] → [Tool Selection] → [Execution] → [Validation]  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │              MATERIALIZED AGENTS (Pre-Configured)                  │ │
│  │                                                                     │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │ │
│  │  │  Settlement     │  │  Regulatory     │  │  Corporate      │  │ │
│  │  │  Recon Agent    │  │  Reporting      │  │  Action Agent   │  │ │
│  │  │                 │  │  Agent          │  │                 │  │ │
│  │  │  Tools: SQL,    │  │  Tools: SQL,    │  │  Tools: API,    │  │ │
│  │  │  API, MQ        │  │  API, SFTP      │  │  Browser, MQ    │  │ │
│  │  │                 │  │                 │  │                 │  │ │
│  │  │  Workflow: 8    │  │  Workflow: 7    │  │  Workflow: 8    │  │ │
│  │  │  steps defined  │  │  steps defined  │  │  steps defined  │  │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         TOOL EXECUTION LAYER                             │
│                                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │   API    │  │ Browser  │  │   Non-   │  │   SQL    │  │Middleware│ │
│  │   Tool   │  │   Tool   │  │ Browser  │  │   Tool   │  │   Tool   │ │
│  │          │  │          │  │   Tool   │  │          │  │          │ │
│  │ "Call    │  │ "Navigate│  │ "Execute │  │ "Query   │  │ "Send    │ │
│  │  REST    │  │  to URL, │  │  command │  │  trades  │  │  message │ │
│  │  endpoint│  │  click   │  │  in      │  │  from    │  │  to MQ   │ │
│  │  with    │  │  button, │  │  terminal│  │  database│  │  queue"  │ │
│  │  params" │  │  extract"│  │  app"    │  │  table"  │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      ENTERPRISE SYSTEMS LAYER                            │
│                                                                           │
│  [Trade APIs] [Web Portals] [Bloomberg] [Databases] [MQ/Kafka/SFTP]    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 1.2 Foundational Agent Internal Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FOUNDATIONAL AGENT                                │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  INPUT PROCESSING                                                  │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Natural Language Understanding (NLU)                        │ │ │
│  │  │  - Parse user intent                                         │ │ │
│  │  │  - Extract entities (dates, amounts, instruments)            │ │ │
│  │  │  - Identify business process type                            │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  REASONING & PLANNING ENGINE                                      │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Task Decomposition                                          │ │ │
│  │  │  "Reconcile trades" →                                        │ │ │
│  │  │    Step 1: Get internal trades                               │ │ │
│  │  │    Step 2: Get external confirmations                        │ │ │
│  │  │    Step 3: Match and compare                                 │ │ │
│  │  │    Step 4: Handle exceptions                                 │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Tool Selection                                              │ │ │
│  │  │  Step 1 needs: SQL Tool (query trade database)              │ │ │
│  │  │  Step 2 needs: API Tool (call custodian API)                │ │ │
│  │  │  Step 3 needs: Agent Logic (matching algorithm)             │ │ │
│  │  │  Step 4 needs: API Tool (create breaks) + MQ Tool (alert)   │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Dependency Resolution                                       │ │ │
│  │  │  Step 2 depends on: Step 1 (need trade IDs)                 │ │ │
│  │  │  Step 3 depends on: Step 1 + Step 2 (need both datasets)    │ │ │
│  │  │  Step 4 depends on: Step 3 (need match results)             │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  EXECUTION ENGINE                                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Tool Orchestrator                                           │ │ │
│  │  │  - Invoke tools in correct sequence                          │ │ │
│  │  │  - Pass data between steps                                   │ │ │
│  │  │  - Handle parallel execution where possible                  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  State Manager                                               │ │ │
│  │  │  - Track execution progress                                  │ │ │
│  │  │  - Store intermediate results                                │ │ │
│  │  │  - Enable resume after failures                              │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Error Handler                                               │ │ │
│  │  │  - Detect failures                                           │ │ │
│  │  │  - Implement retry logic                                     │ │ │
│  │  │  - Escalate when needed                                      │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  OUTPUT & VALIDATION                                              │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Result Validator                                            │ │ │
│  │  │  - Verify output correctness                                 │ │ │
│  │  │  - Check business rules                                      │ │ │
│  │  │  - Ensure data quality                                       │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Response Generator                                          │ │ │
│  │  │  - Format results for user                                   │ │ │
│  │  │  - Generate reports/summaries                                │ │ │
│  │  │  - Log audit trail                                           │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  CROSS-CUTTING CONCERNS                                           │ │
│  │  [Logging] [Monitoring] [Security] [Caching] [Configuration]     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 1.3 Tool Architecture - Detailed View

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            TOOL LAYER                                    │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      TOOL INTERFACE (Abstract)                     │ │
│  │                                                                     │ │
│  │  execute(instruction: str, context: dict) → result: dict          │ │
│  │  validate(config: dict) → bool                                     │ │
│  │  health_check() → status: dict                                     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   API TOOL   │  │ BROWSER TOOL │  │  SQL TOOL    │  │MIDDLEWARE  │ │
│  │              │  │              │  │              │  │   TOOL     │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌────────┐ │ │
│  │ │ Registry │ │  │ │ Selenium │ │  │ │   NL2SQL │ │  │ │MQ Conn │ │ │
│  │ │ Manager  │ │  │ │ Driver   │ │  │ │  Engine  │ │  │ │        │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │  │ └────────┘ │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌────────┐ │ │
│  │ │  Auth    │ │  │ │ Element  │ │  │ │ Schema   │ │  │ │Kafka   │ │ │
│  │ │ Handler  │ │  │ │ Locator  │ │  │ │ Manager  │ │  │ │Conn    │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │  │ └────────┘ │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌────────┐ │ │
│  │ │ Request  │ │  │ │ Action   │ │  │ │ Query    │ │  │ │SFTP    │ │ │
│  │ │ Builder  │ │  │ │ Executor │ │  │ │Optimizer │ │  │ │Conn    │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │  │ └────────┘ │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌────────┐ │ │
│  │ │ Response │ │  │ │ Data     │ │  │ │ Result   │ │  │ │Message │ │ │
│  │ │ Parser   │ │  │ │Extractor │ │  │ │ Parser   │ │  │ │Handler │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │  │ └────────┘ │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌────────┐ │ │
│  │ │  Retry   │ │  │ │ Screen   │ │  │ │ Conn     │ │  │ │ Retry  │ │ │
│  │ │  Logic   │ │  │ │ Capture  │ │  │ │ Pool     │ │  │ │ Logic  │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │  │ └────────┘ │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    TOOL REGISTRY & CONFIGURATION                   │ │
│  │                                                                     │ │
│  │  {                                                                 │ │
│  │    "api_tools": [                                                  │ │
│  │      {                                                             │ │
│  │        "name": "trade_booking_api",                                │ │
│  │        "base_url": "https://api.tradebook.internal/v2",           │ │
│  │        "auth_type": "oauth2",                                      │ │
│  │        "endpoints": {...}                                          │ │
│  │      }                                                             │ │
│  │    ],                                                              │ │
│  │    "browser_tools": [...],                                         │ │
│  │    "sql_tools": [...],                                             │ │
│  │    "middleware_tools": [...]                                       │ │
│  │  }                                                                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 1.4 Materialized Agent Creation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  MATERIALIZED AGENT CREATION PROCESS                     │
│                                                                           │
│  Step 1: BUSINESS REQUIREMENT                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Business User: "We need to automate trade settlement              │ │
│  │                  reconciliation process"                            │ │
│  │                                                                     │ │
│  │  Current Process:                                                  │ │
│  │  - Manual: 4 hours/day                                             │ │
│  │  - Error-prone: 5% error rate                                      │ │
│  │  - Systems involved: Trade DB, Custodian API, Break Mgmt System   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 2: PROCESS ANALYSIS                                                │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Process Mapping:                                                  │ │
│  │  1. Retrieve settled trades from internal system                  │ │
│  │  2. Fetch confirmations from custodian                             │ │
│  │  3. Match trades to confirmations                                  │ │
│  │  4. Identify breaks (unmatched items)                              │ │
│  │  5. Create break records                                           │ │
│  │  6. Alert operations team                                          │ │
│  │  7. Generate reconciliation report                                 │ │
│  │                                                                     │ │
│  │  Decision Points:                                                  │ │
│  │  - If amount mismatch < $100 → auto-approve                        │ │
│  │  - If break > $1M → escalate immediately                           │ │
│  │  - If custodian API fails → use browser fallback                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 3: TOOL SELECTION                                                  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Required Tools:                                                   │ │
│  │  ✓ SQL Tool - Query trade database                                │ │
│  │  ✓ API Tool - Call custodian API, break management API            │ │
│  │  ✓ Browser Tool - Fallback for custodian portal                   │ │
│  │  ✓ Middleware Tool - Send alerts via MQ                           │ │
│  │  ✗ Non-Browser Tool - Not needed for this use case                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 4: TOOL CONFIGURATION                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  SQL Tool Config:                                                  │ │
│  │  - Data Source: trade_repository_prod                             │ │
│  │  - Tables: trades, settlement_instructions                         │ │
│  │  - Queries: get_settled_trades_by_date                            │ │
│  │                                                                     │ │
│  │  API Tool Config:                                                  │ │
│  │  - Custodian API: GET /confirmations                              │ │
│  │  - Break Mgmt API: POST /breaks/create                            │ │
│  │                                                                     │ │
│  │  Browser Tool Config:                                              │ │
│  │  - URL: https://custodian.portal.com/confirmations                │ │
│  │  - Actions: login, filter_by_date, extract_table                  │ │
│  │                                                                     │ │
│  │  Middleware Tool Config:                                           │ │
│  │  - MQ Queue: OPERATIONS.ALERTS                                     │ │
│  │  - Message Format: JSON                                            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 5: WORKFLOW DEFINITION                                             │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  workflow:                                                         │ │
│  │    name: "settlement_reconciliation"                               │ │
│  │    steps:                                                          │ │
│  │      - id: "get_trades"                                            │ │
│  │        tool: "sql"                                                 │ │
│  │        action: "query"                                             │ │
│  │        params:                                                     │ │
│  │          query: "get_settled_trades_by_date"                      │ │
│  │          date: "{{settlement_date}}"                               │ │
│  │        output: "internal_trades"                                   │ │
│  │                                                                     │ │
│  │      - id: "get_confirmations"                                     │ │
│  │        tool: "api"                                                 │ │
│  │        action: "call"                                              │ │
│  │        params:                                                     │ │
│  │          endpoint: "custodian_api.get_confirmations"              │ │
│  │          date: "{{settlement_date}}"                               │ │
│  │        fallback:                                                   │ │
│  │          tool: "browser"                                           │ │
│  │          action: "extract_confirmations"                           │ │
│  │        output: "custodian_confirmations"                           │ │
│  │                                                                     │ │
│  │      - id: "match_trades"                                          │ │
│  │        tool: "agent_logic"                                         │ │
│  │        action: "reconcile"                                         │ │
│  │        inputs: ["internal_trades", "custodian_confirmations"]     │ │
│  │        output: "reconciliation_results"                            │ │
│  │                                                                     │ │
│  │      - id: "handle_breaks"                                         │ │
│  │        tool: "api"                                                 │ │
│  │        action: "create_breaks"                                     │ │
│  │        condition: "{{reconciliation_results.breaks.count > 0}}"   │ │
│  │        params:                                                     │ │
│  │          breaks: "{{reconciliation_results.breaks}}"              │ │
│  │                                                                     │ │
│  │      - id: "send_alerts"                                           │ │
│  │        tool: "middleware"                                          │ │
│  │        action: "send_message"                                      │ │
│  │        condition: "{{reconciliation_results.breaks.count > 0}}"   │ │
│  │        params:                                                     │ │
│  │          queue: "OPERATIONS.ALERTS"                                │ │
│  │          message: "{{format_alert(reconciliation_results)}}"      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 6: BUSINESS RULES ENCODING                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  business_rules:                                                   │ │
│  │    - name: "auto_approve_small_mismatches"                         │ │
│  │      condition: "abs(trade.amount - confirmation.amount) < 100"   │ │
│  │      action: "approve_and_log"                                     │ │
│  │                                                                     │ │
│  │    - name: "escalate_large_breaks"                                 │ │
│  │      condition: "break.amount > 1000000"                           │ │
│  │      action: "escalate_to_manager"                                 │ │
│  │                                                                     │ │
│  │    - name: "match_tolerance"                                       │ │
│  │      params:                                                       │ │
│  │        trade_id_match: "exact"                                     │ │
│  │        amount_tolerance: 0.01                                      │ │
│  │        date_tolerance: 0                                           │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 7: TESTING & VALIDATION                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Test Scenarios:                                                   │ │
│  │  ✓ Happy path: All trades match                                   │ │
│  │  ✓ Partial match: Some breaks identified                          │ │
│  │  ✓ API failure: Fallback to browser tool                          │ │
│  │  ✓ Large break: Escalation triggered                              │ │
│  │  ✓ Small mismatch: Auto-approved                                  │ │
│  │                                                                     │ │
│  │  Validation:                                                       │ │
│  │  ✓ All required tools configured correctly                        │ │
│  │  ✓ Workflow steps execute in correct order                        │ │
│  │  ✓ Business rules applied correctly                               │ │
│  │  ✓ Error handling works as expected                               │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  Step 8: DEPLOYMENT                                                      │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Materialized Agent Created:                                       │ │
│  │  Name: "settlement_reconciliation_agent"                           │ │
│  │  Status: ACTIVE                                                    │ │
│  │  Schedule: Daily at 9:00 AM                                        │ │
│  │  Monitoring: Enabled                                               │ │
│  │  Alerts: Configured                                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tool Implementation Details

### 2.1 API Tool - Deep Dive

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            API TOOL                                      │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  API REGISTRY (Metadata Store)                                     │ │
│  │                                                                     │ │
│  │  {                                                                 │ │
│  │    "trade_booking_api": {                                          │ │
│  │      "base_url": "https://api.tradebook.internal/v2",             │ │
│  │      "auth": {                                                     │ │
│  │        "type": "oauth2",                                           │ │
│  │        "token_url": "https://auth.internal/token",                │ │
│  │        "client_id": "{{vault:trade_api_client_id}}",              │ │
│  │        "client_secret": "{{vault:trade_api_secret}}"               │ │
│  │      },                                                            │ │
│  │      "endpoints": {                                                │ │
│  │        "book_trade": {                                             │ │
│  │          "method": "POST",                                         │ │
│  │          "path": "/trades/equity",                                 │ │
│  │          "headers": {                                              │ │
│  │            "Content-Type": "application/json",                     │ │
│  │            "X-Business-Unit": "required"                           │ │
│  │          },                                                        │ │
│  │          "request_schema": {                                       │ │
│  │            "tradeId": "string",                                    │ │
│  │            "counterparty": "string",                               │ │
│  │            "instrument": "string",                                 │ │
│  │            "quantity": "number",                                   │ │
│  │            "price": "number",                                      │ │
│  │            "tradeDate": "date"                                     │ │
│  │          },                                                        │ │
│  │          "response_schema": {                                      │ │
│  │            "bookingId": "string",                                  │ │
│  │            "status": "enum[SUCCESS,FAILED]",                       │ │
│  │            "timestamp": "datetime",                                │ │
│  │            "validationErrors": "array"                             │ │
│  │          },                                                        │ │
│  │          "rate_limit": "100/minute",                               │ │
│  │          "timeout": 30,                                            │ │
│  │          "retry_policy": {                                         │ │
│  │            "max_retries": 3,                                       │ │
│  │            "backoff": "exponential",                               │ │
│  │            "retry_on": [500, 502, 503, 504]                        │ │
│  │          }                                                         │ │
│  │        }                                                           │ │
│  │      }                                                             │ │
│  │    }                                                               │ │
│  │  }                                                                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  EXECUTION FLOW                                                    │ │
│  │                                                                     │ │
│  │  1. Agent Request                                                  │ │
│  │     ↓                                                              │ │
│  │     "Call trade_booking_api.book_trade with params {...}"         │ │
│  │                                                                     │ │
│  │  2. Registry Lookup                                                │ │
│  │     ↓                                                              │ │
│  │     Retrieve endpoint configuration from registry                  │ │
│  │                                                                     │ │
│  │  3. Authentication                                                 │ │
│  │     ↓                                                              │ │
│  │     - Check if valid token exists in cache                         │ │
│  │     - If not, obtain new token using OAuth2 flow                   │ │
│  │     - Store token with expiry                                      │ │
│  │                                                                     │ │
│  │  4. Request Building                                               │ │
│  │     ↓                                                              │ │
│  │     - Validate params against request_schema                       │ │
│  │     - Build HTTP request (method, URL, headers, body)              │ │
│  │     - Add authentication headers                                   │ │
│  │                                                                     │ │
│  │  5. Execution                                                      │ │
│  │     ↓                                                              │ │
│  │     - Send HTTP request                                            │ │
│  │     - Handle rate limiting (wait if limit reached)                 │ │
│  │     - Apply timeout                                                │ │
│  │                                                                     │ │
│  │  6. Response Handling                                              │ │
│  │     ↓                                                              │ │
│  │     - Parse response (JSON, XML, etc.)                             │ │
│  │     - Validate against response_schema                             │ │
│  │     - Check for errors                                             │ │
│  │                                                                     │ │
│  │  7. Error Handling & Retry                                         │ │
│  │     ↓                                                              │ │
│  │     - If retriable error (5xx, timeout): retry with backoff        │ │
│  │     - If non-retriable error (4xx): return error to agent          │ │
│  │     - If max retries exceeded: escalate                            │ │
│  │                                                                     │ │
│  │  8. Return Result                                                  │ │
│  │     ↓                                                              │ │
│  │     {                                                              │ │
│  │       "success": true,                                             │ │
│  │       "data": {...},                                               │ │
│  │       "metadata": {                                                │ │
│  │         "execution_time_ms": 245,                                  │ │
│  │         "retry_count": 0                                           │ │
│  │       }                                                            │ │
│  │     }                                                              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Implementation Pseudocode

```python
class APITool:
    def __init__(self, registry_path, vault_client):
        self.registry = load_registry(registry_path)
        self.vault = vault_client
        self.token_cache = {}
        self.rate_limiters = {}

    def execute(self, instruction, context):
        # Parse instruction: "call trade_booking_api.book_trade with {...}"
        api_name, endpoint_name, params = parse_instruction(instruction)

        # Get configuration
        api_config = self.registry[api_name]
        endpoint_config = api_config['endpoints'][endpoint_name]

        # Authenticate
        token = self._get_auth_token(api_config['auth'])

        # Build request
        request = self._build_request(
            base_url=api_config['base_url'],
            endpoint=endpoint_config,
            params=params,
            token=token
        )

        # Execute with retry
        response = self._execute_with_retry(
            request=request,
            retry_policy=endpoint_config['retry_policy']
        )

        # Parse and validate response
        result = self._parse_response(
            response=response,
            schema=endpoint_config['response_schema']
        )

        return result

    def _get_auth_token(self, auth_config):
        if auth_config['type'] == 'oauth2':
            # Check cache
            cache_key = auth_config['token_url']
            if cache_key in self.token_cache:
                token_data = self.token_cache[cache_key]
                if not token_data['expired']:
                    return token_data['token']

            # Get new token
            client_id = self.vault.get(auth_config['client_id'])
            client_secret = self.vault.get(auth_config['client_secret'])

            token_response = requests.post(
                auth_config['token_url'],
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret
                }
            )

            token = token_response.json()['access_token']
            expires_in = token_response.json()['expires_in']

            # Cache token
            self.token_cache[cache_key] = {
                'token': token,
                'expires_at': time.time() + expires_in,
                'expired': False
            }

            return token

    def _execute_with_retry(self, request, retry_policy):
        max_retries = retry_policy['max_retries']
        retry_on = retry_policy['retry_on']

        for attempt in range(max_retries + 1):
            try:
                response = requests.request(
                    method=request['method'],
                    url=request['url'],
                    headers=request['headers'],
                    json=request['body'],
                    timeout=request['timeout']
                )

                if response.status_code in retry_on and attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue

                return response

            except requests.Timeout:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                raise

        raise MaxRetriesExceeded()
```

---

### 2.2 Browser Tool - Deep Dive

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BROWSER TOOL                                    │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  BROWSER CONFIGURATION                                             │ │
│  │                                                                     │ │
│  │  {                                                                 │ │
│  │    "custodian_portal": {                                           │ │
│  │      "url": "https://custodian.portal.com",                        │ │
│  │      "auth": {                                                     │ │
│  │        "type": "form_login",                                       │ │
│  │        "login_url": "/login",                                      │ │
│  │        "username_field": "input[name='username']",                 │ │
│  │        "password_field": "input[name='password']",                 │ │
│  │        "submit_button": "button[type='submit']",                   │ │
│  │        "credentials": {                                            │ │
│  │          "username": "{{vault:custodian_portal_user}}",            │ │
│  │          "password": "{{vault:custodian_portal_pass}}"             │ │
│  │        }                                                           │ │
│  │      },                                                            │ │
│  │      "workflows": {                                                │ │
│  │        "extract_confirmations": {                                  │ │
│  │          "steps": [                                                │ │
│  │            {                                                       │ │
│  │              "action": "navigate",                                 │ │
│  │              "url": "/confirmations"                               │ │
│  │            },                                                      │ │
│  │            {                                                       │ │
│  │              "action": "click",                                    │ │
│  │              "selector": "button#filter-btn"                       │ │
│  │            },                                                      │ │
│  │            {                                                       │ │
│  │              "action": "fill",                                     │ │
│  │              "selector": "input[name='date']",                     │ │
│  │              "value": "{{params.date}}"                            │ │
│  │            },                                                      │ │
│  │            {                                                       │ │
│  │              "action": "click",                                    │ │
│  │              "selector": "button#apply-filter"                     │ │
│  │            },                                                      │ │
│  │            {                                                       │ │
│  │              "action": "wait",                                     │ │
│  │              "condition": "table#confirmations tbody tr"           │ │
│  │            },                                                      │ │
│  │            {                                                       │ │
│  │              "action": "extract",                                  │ │
│  │              "selector": "table#confirmations",                    │ │
│  │              "type": "table",                                      │ │
│  │              "columns": [                                          │ │
│  │                "trade_id", "amount", "counterparty", "status"     │ │
│  │              ]                                                     │ │
│  │            }                                                       │ │
│  │          ]                                                         │ │
│  │        }                                                           │ │
│  │      }                                                             │ │
│  │    }                                                               │ │
│  │  }                                                                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  EXECUTION FLOW                                                    │ │
│  │                                                                     │ │
│  │  1. Initialize Browser                                             │ │
│  │     ↓                                                              │ │
│  │     - Launch browser instance (headless or visible)                │ │
│  │     - Set viewport, user agent, etc.                               │ │
│  │     - Configure timeouts                                           │ │
│  │                                                                     │ │
│  │  2. Authentication                                                 │ │
│  │     ↓                                                              │ │
│  │     - Navigate to login page                                       │ │
│  │     - Fill username and password from vault                        │ │
│  │     - Click submit button                                          │ │
│  │     - Wait for successful login (check for dashboard element)      │ │
│  │                                                                     │ │
│  │  3. Execute Workflow Steps                                         │ │
│  │     ↓                                                              │ │
│  │     For each step in workflow:                                     │ │
│  │       - Navigate: Go to URL                                        │ │
│  │       - Click: Find element and click                              │ │
│  │       - Fill: Find input and enter text                            │ │
│  │       - Wait: Wait for element or condition                        │ │
│  │       - Extract: Get data from page                                │ │
│  │       - Capture screenshot (for audit)                             │ │
│  │                                                                     │ │
│  │  4. Data Extraction                                                │ │
│  │     ↓                                                              │ │
│  │     - Locate target elements (table, list, form)                   │ │
│  │     - Parse HTML structure                                         │ │
│  │     - Extract text, attributes, or structured data                 │ │
│  │     - Transform to desired format (JSON, CSV)                      │ │
│  │                                                                     │ │
│  │  5. Error Handling                                                 │ │
│  │     ↓                                                              │ │
│  │     - Element not found: Retry with alternative selectors          │ │
│  │     - Timeout: Increase wait time or fail gracefully               │ │
│  │     - Unexpected popup: Detect and handle                          │ │
│  │     - Session expired: Re-authenticate                             │ │
│  │                                                                     │ │
│  │  6. Cleanup                                                        │ │
│  │     ↓                                                              │ │
│  │     - Logout (if required)                                         │ │
│  │     - Close browser                                                │ │
│  │     - Save screenshots and logs                                    │ │
│  │                                                                     │ │
│  │  7. Return Result                                                  │ │
│  │     ↓                                                              │ │
│  │     {                                                              │ │
│  │       "success": true,                                             │ │
│  │       "data": [...extracted data...],                              │ │
│  │       "screenshots": ["step1.png", "step2.png"],                   │ │
│  │       "execution_time_ms": 12500                                   │ │
│  │     }                                                              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Smart Element Location Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ELEMENT LOCATION STRATEGY                             │
│                                                                           │
│  Problem: Web UIs change frequently, breaking brittle selectors          │
│                                                                           │
│  Solution: Multi-level fallback strategy                                 │
│                                                                           │
│  Level 1: Semantic Selectors (Most Robust)                               │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  - Use ARIA labels: button[aria-label="Submit"]                    │ │
│  │  - Use data attributes: div[data-testid="confirmation-table"]      │ │
│  │  - Use semantic HTML: <button>, <nav>, <main>                      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓ (if not found)                            │
│  Level 2: Text-Based Selectors                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  - Find by text content: button:contains("Submit")                 │ │
│  │  - Find by placeholder: input[placeholder="Enter date"]            │ │
│  │  - Find by label: label:contains("Trade Date") + input             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓ (if not found)                            │
│  Level 3: Structural Selectors                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  - Use class names: button.submit-btn                              │ │
│  │  - Use IDs: #submit-button                                         │ │
│  │  - Use position: form > div:nth-child(3) > button                  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓ (if not found)                            │
│  Level 4: AI-Powered Visual Detection                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  - Take screenshot                                                 │ │
│  │  - Use vision model to identify element                            │ │
│  │  - "Find the submit button in this screenshot"                     │ │
│  │  - Get coordinates and click                                       │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  Self-Healing: When element is found via fallback, update config         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 2.3 SQL Tool - Deep Dive

#### Natural Language to SQL Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      NL-TO-SQL PIPELINE                                  │
│                                                                           │
│  Input: "Show me all equity trades from yesterday that haven't settled" │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  STEP 1: Intent Recognition                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  - Query Type: SELECT (read operation)                       │ │ │
│  │  │  - Target Entity: "trades"                                   │ │ │
│  │  │  - Filters:                                                  │ │ │
│  │  │    * asset_class = "equity"                                  │ │ │
│  │  │    * trade_date = "yesterday"                                │ │ │
│  │  │    * settlement_status != "settled"                          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  STEP 2: Schema Mapping                                            │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Business Term → Database Schema                             │ │ │
│  │  │                                                               │ │ │
│  │  │  "trades" → Table: trades                                    │ │ │
│  │  │  "equity" → Column: asset_class, Value: 'EQUITY'             │ │ │
│  │  │  "yesterday" → Column: trade_date, Value: CURRENT_DATE - 1   │ │ │
│  │  │  "haven't settled" → Column: settlement_status,              │ │ │
│  │  │                      Value: NOT IN ('SETTLED', 'CONFIRMED')  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  STEP 3: SQL Generation                                            │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  SELECT                                                       │ │ │
│  │  │    t.trade_id,                                               │ │ │
│  │  │    t.instrument,                                             │ │ │
│  │  │    t.quantity,                                               │ │ │
│  │  │    t.price,                                                  │ │ │
│  │  │    t.trade_date,                                             │ │ │
│  │  │    t.settlement_status                                       │ │ │
│  │  │  FROM trades t                                               │ │ │
│  │  │  WHERE t.asset_class = 'EQUITY'                              │ │ │
│  │  │    AND t.trade_date = CURRENT_DATE - INTERVAL '1 day'       │ │ │
│  │  │    AND t.settlement_status NOT IN ('SETTLED', 'CONFIRMED')  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  STEP 4: Query Validation                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ✓ Syntax check: Valid SQL                                   │ │ │
│  │  │  ✓ Schema check: All tables and columns exist                │ │ │
│  │  │  ✓ Permission check: User has SELECT on trades table         │ │ │
│  │  │  ✓ Safety check: No DELETE/DROP/TRUNCATE                     │ │ │
│  │  │  ✓ Performance check: Query has appropriate indexes          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  STEP 5: Execution                                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  - Execute query against database                            │ │ │
│  │  │  - Apply row limit (default: 1000)                           │ │ │
│  │  │  - Set query timeout (default: 30s)                          │ │ │
│  │  │  - Use read-only connection                                  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  STEP 6: Result Formatting                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  {                                                            │ │ │
│  │  │    "success": true,                                          │ │ │
│  │  │    "row_count": 47,                                          │ │ │
│  │  │    "data": [                                                 │ │ │
│  │  │      {                                                       │ │ │
│  │  │        "trade_id": "TRD-2024-001",                           │ │ │
│  │  │        "instrument": "AAPL",                                 │ │ │
│  │  │        "quantity": 1000,                                     │ │ │
│  │  │        "price": 175.50,                                      │ │ │
│  │  │        "trade_date": "2024-12-04",                           │ │ │
│  │  │        "settlement_status": "PENDING"                        │ │ │
│  │  │      },                                                      │ │ │
│  │  │      ...                                                     │ │ │
│  │  │    ],                                                        │ │ │
│  │  │    "query": "SELECT...",                                     │ │ │
│  │  │    "execution_time_ms": 145                                  │ │ │
│  │  │  }                                                           │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Schema Metadata Example

```json
{
  "data_sources": {
    "trade_repository": {
      "type": "postgresql",
      "connection": "jdbc:postgresql://tradedb.internal:5432/trades_prod",
      "schemas": {
        "public": {
          "tables": {
            "trades": {
              "description": "All trade transactions",
              "columns": {
                "trade_id": {
                  "type": "varchar(50)",
                  "description": "Unique trade identifier",
                  "business_terms": ["trade ID", "trade number", "transaction ID"]
                },
                "asset_class": {
                  "type": "varchar(20)",
                  "description": "Type of asset",
                  "business_terms": ["asset type", "product type"],
                  "values": ["EQUITY", "FX", "FIXED_INCOME", "DERIVATIVE"]
                },
                "trade_date": {
                  "type": "date",
                  "description": "Date trade was executed",
                  "business_terms": ["execution date", "trade date", "transaction date"]
                },
                "settlement_status": {
                  "type": "varchar(20)",
                  "description": "Current settlement status",
                  "business_terms": ["status", "settlement state"],
                  "values": ["PENDING", "SETTLED", "CONFIRMED", "FAILED"]
                }
              },
              "relationships": {
                "counterparties": {
                  "type": "many-to-one",
                  "foreign_key": "counterparty_id",
                  "references": "counterparties.counterparty_id"
                }
              },
              "indexes": ["trade_date", "settlement_status", "asset_class"]
            }
          }
        }
      }
    }
  }
}
```

---

### 2.4 Middleware Tool - Deep Dive

#### Multi-Protocol Support

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MIDDLEWARE TOOL                                   │
│                                                                           