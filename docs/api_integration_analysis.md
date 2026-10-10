# WorkBuddy API Integration Feasibility Analysis

**Date:** 2026-10-10  
**Project:** GenBuddy_Hackathon (DORMATHON 2026 Track 2)  
**Question:** Can Flask directly trigger WorkBuddy's AI agent when a user submits a question?

---

## Executive Summary

**Direct Flask-to-WorkBuddy integration is NOT available with your current account and installation.** After investigating all documented WorkBuddy API capabilities — Enterprise API, Open Platform, Assistant Remote Control, Automation, and local installation internals — none provide a clean HTTP endpoint that Flask can call to trigger agent execution with local file access.

**Recommendation: Keep the current manual workflow.** It is already working, demonstrates genuine agent reasoning, and satisfies the Track 2 requirement (proof of WorkBuddy usage, not embedded integration).

---

## 1. Integration Pathways Investigated

### Path A: WorkBuddy Enterprise API (Managed Agents)

**What it is:** A REST API hosted on Tencent Cloud that manages cloud-hosted AI agents. Developers can create agents, versions, sessions, and query message events programmatically.

**Documentation:** <https://cloud.tencent.com/document/product/1831/138590>

**API endpoints available (9 categories, 25+ endpoints):**

- Agent management: CreateAgent, DeleteAgent, DescribeAgent, DescribeAgentList, ModifyAgent
- Version management: CreateAgentVersion, DescribeAgentVersion, DescribeAgentVersionList
- Session management: CreateAgentSession, DescribeAgentSession, DescribeAgentSessionList
- Message events: DescribeMessageEventList (replay conversation + tool calls)
- External agents: BindExternalAgent, UnbindExternalAgent (A2A protocol)
- Resource browsing: DescribeSkillList, DescribeExpertList, DescribeConnectorList, DescribeBuiltinModelList
- Access: DescribeUserAccessToken

**Quick-start flow documented by Tencent:**

1. CreateAgent → get AgentId
2. CreateAgentVersion (with Manifest JSON) → get VersionId
3. CreateAgentSession → get SessionId + Endpoint URL
4. DescribeMessageEventList → retrieve conversation/tool-call results

**Verdict: NOT AVAILABLE with current account**

| Requirement           | Status                                                                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Enterprise account    | NOT AVAILABLE — `enterprise-registry.json` shows `"enterpriseId": ""`, `"entries": []`                                                                             |
| CAM authentication    | NOT CONFIGURED — requires Tencent Cloud sub-account with CAM signing                                                                                               |
| Whitelist beta        | NOT APPROVED — docs state "白名单内测" (whitelist internal testing)                                                                                                     |
| Local file access     | NOT POSSIBLE — agent runs in Tencent Cloud sandbox, not on user's machine                                                                                          |
| Existing tool access  | NOT POSSIBLE — `validate_data.py`, `fault_investigation.py`, and CSV files are local; cloud agent cannot access them without repackaging as Skills in the Manifest |
| Agent development     | REQUIRED — would need to define system prompt, skills, model in Manifest JSON                                                                                      |
| Hackathon feasibility | NO — enterprise approval, CAM setup, agent development, and skill packaging cannot be completed before deadline                                                    |

**Key limitation:** Even if enterprise access were granted, the cloud-hosted agent CANNOT access your local `<project_root>/` project files. The agent runs in a Tencent Cloud sandbox with its own filesystem. You would need to package `validate_data.py`, `fault_investigation.py`, and the CSV datasets into the agent's Manifest as Skills — essentially rebuilding the investigation toolchain for the cloud.

---

### Path B: WorkBuddy Open Platform

**What it is:** A developer marketplace platform (open.workbuddy.cn) for publishing Buddy apps, skills, experts, connectors, and hardware integrations.

**Documentation:** <https://open.workbuddy.cn/>

**Capabilities:** Publish your own Buddy apps and skills to the WorkBuddy ecosystem. Other users can discover and install them.

**The `connect_open_platform` tool** (available in this WorkBuddy session) obtains a short-lived Open Platform token (`op_xxx`) for skill backends to call back into the Open Platform API for identity verification. It is NOT an agent-triggering API — it's for skill-to-platform callbacks.

**Verdict: NOT APPLICABLE**

The Open Platform is for publishing skills/apps TO the WorkBuddy marketplace, not for triggering WorkBuddy agent execution FROM an external application. It does not provide an HTTP endpoint that Flask can call to start an investigation.

---

### Path C: Assistant Remote Control (Messaging Platform Bridge)

**What it is:** WorkBuddy's "Assistant" feature lets external messaging platforms (Slack, Telegram, Discord, WeChat Work, Feishu, DingTalk, QQ, WeChat) send messages to the WorkBuddy desktop agent and receive results back.

**How it works:**

- **Slack:** Uses Slack Socket Mode (WebSocket connection from WorkBuddy to Slack's servers)
- **Telegram:** Uses Telegram Bot API (BotFather token configured in WorkBuddy settings)
- **Discord:** Uses Discord Bot API
- All platforms: WorkBuddy desktop must be running, receives messages via the platform's API, processes them, sends results back through the same platform

**Theoretical Flask integration via Telegram:**

1. Flask receives user question from dashboard
2. Flask sends message to Telegram Bot API (using bot token) — BUT this sends FROM the bot, not TO the bot
3. Actually, Flask would need to act as a Telegram USER sending a message to the bot — requires MTProto session, not just Bot API
4. WorkBuddy receives the message via Bot API polling
5. WorkBuddy processes and sends response back to the Telegram chat
6. Flask polls Telegram Bot API `getUpdates` for the response message

**Verdict: THEORETICALLY POSSIBLE but IMPRACTICAL**

| Aspect                          | Assessment                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------------- |
| Available with current account? | YES — requires only a Telegram bot token                                            |
| Local file access?              | YES — WorkBuddy runs on same machine                                                |
| Can use existing tools?         | YES — agent can run scripts, read CSVs, call Flask API                              |
| Implementation complexity       | HIGH — multi-hop message routing, token management, polling                         |
| Security risk                   | HIGH — bot API token stored in Flask app                                            |
| Reliability                     | LOW — 4 intermediate hops (Flask → Telegram API → WorkBuddy → Telegram API → Flask) |
| Multi-user support              | NO — single bot handles all requests, no user isolation                             |
| Production-ready?               | NO — fragile, hard to debug, no error recovery                                      |
| Hackathon feasibility           | MARGINAL — 2-3 days to build and debug the bridge, high risk of failure             |

**Critical flaw:** Flask cannot send a message TO the Telegram bot using only the Bot API token. The Bot API allows sending messages FROM the bot to chats, not simulating user messages TO the bot. Flask would need a full Telegram user session (MTProto), which requires phone number authentication — completely impractical.

**Slack alternative:** Slack Socket Mode is a WebSocket from WorkBuddy TO Slack. Flask cannot inject messages into this WebSocket. Flask would need to use the Slack Web API to post a message to a channel the bot monitors, then poll for the bot's response. This requires a Slack workspace with admin access and is equally fragile.

---

### Path D: WorkBuddy Automation Feature

**What it is:** An internal scheduler within WorkBuddy desktop that runs tasks on a recurring or one-time schedule.

**How it works:** User creates an automation in WorkBuddy's UI — describes a task, sets a schedule (hourly/daily/weekly/one-time), optionally specifies a workspace directory. WorkBuddy's internal scheduler triggers the task at the scheduled time.

**Verdict: NOT EXTERNALLY TRIGGERABLE**

The Automation feature is triggered by WorkBuddy's internal clock, not by external HTTP calls. There is no webhook, no API endpoint, and no CLI command to trigger an automation on demand. It cannot be invoked by Flask.

**Possible workaround (fragile):** Set up a one-time automation that fires immediately, with a prompt that includes reading from the `requests/` directory. But this requires manual setup in WorkBuddy's UI for each request and doesn't provide real-time triggering.

---

### Path E: Local HTTP API / CLI

**What it is:** A hypothetical local HTTP server or CLI command that Flask could call to create a WorkBuddy task.

**Verdict: DOES NOT EXIST**

- `netstat` shows no WorkBuddy API port listening on the machine
- `~/.workbuddy-ai/` directory contains internal state files (SQLite, logs, caches) — no HTTP server configuration
- WorkBuddy CLI documentation page (`/docs/cli/`) redirects to CodeBuddy IDE docs — no WorkBuddy CLI exists
- The `mcp.json` file at `~/.workbuddy-ai/mcp.json` configures MCP servers that WorkBuddy can CALL — it does not expose WorkBuddy as an MCP server that external apps can call

---

## 2. Summary Comparison

| Integration Path            | Available?             | Local File Access?       | Flask → Agent Direct?   | Hackathon Feasible?       |
| --------------------------- | ---------------------- | ------------------------ | ----------------------- | ------------------------- |
| A. Enterprise API           | NO (enterprise + beta) | NO (cloud sandbox)       | YES (REST API)          | NO                        |
| B. Open Platform            | YES (exists)           | N/A (not for triggering) | NO                      | NO                        |
| C. Assistant (Slack/TG)     | YES                    | YES                      | NO (via messaging API)  | MARGINAL (high risk)      |
| D. Automation               | YES                    | YES                      | NO (internal scheduler) | NO                        |
| E. Local HTTP/CLI           | NO                     | N/A                      | N/A                     | NO                        |
| **Current manual workflow** | **YES**                | **YES**                  | **NO (manual paste)**   | **YES (already working)** |

---

## 3. Why the Current Manual Workflow Is the Best Option

The current workflow already accomplishes everything the Track 2 judging criteria require:

### What it does:

1. User submits a question in the GenBuddy dashboard → JSON request created in `requests/`
2. User copies the question and pastes it into WorkBuddy
3. WorkBuddy agent detects the pending request, updates status to `investigating`
4. Agent executes real tools: `validate_data.py`, `fault_investigation.py`, raw CSV reads, Flask API queries
5. Agent performs LLM reasoning: cross-scenario comparison, root cause analysis, maintenance adequacy assessment
6. Agent updates status to `generating_reports`, writes output files to `outputs/<request_id>/`
7. Agent updates status to `completed`
8. Dashboard auto-polls (5s interval) and displays results with download links

### What it proves for Track 2:

- **Genuine agent reasoning** — not API calls, not hardcoded Python, real LLM reasoning at runtime
- **Tool execution** — agent runs scripts, reads files, calls APIs independently
- **Workflow adaptation** — agent changed strategy across 4 investigations (broad vs focused, work orders vs contractor briefing)
- **Real deliverables** — 3 output files per investigation with actionable recommendations
- **Full audit trail** — agent execution logs document every decision


### What it does NOT do (and why that's OK):

- Flask does NOT directly trigger WorkBuddy — the user manually pastes the question
- This is NOT a limitation for Track 2 — the organizer clarified: "WorkBuddy does NOT need to be directly integrated into the final application. We only need to provide proof that WorkBuddy was used."
- The dashboard tracks the full lifecycle and displays genuine execution progress and final reports

---

## 4. Required Permissions and Setup (If Enterprise API Were Available)

For completeness, here is what would be needed if you pursued the Enterprise API path in the future:

1. **Tencent Cloud Enterprise account** with WorkBuddy Managed Agents enabled
2. **CAM (Cloud Access Management) sub-account** with API keys (SecretId + SecretKey)
3. **Whitelist approval** — Enterprise API is in beta testing with whitelist access
4. **Agent definition** — CreateAgent with Manifest JSON containing:
   - System prompt (investigation instructions)
   - Skills (packaged versions of validate_data.py, fault_investigation.py)
   - Model selection (from DescribeBuiltinModelList)
5. **Agent version** — CreateAgentVersion with frozen Manifest
6. **Session management** — CreateAgentSession per user question
7. **Result polling** — DescribeMessageEventList to retrieve tool calls and responses
8. **Data transfer** — CSV files would need to be uploaded to the cloud agent's context, as it cannot access local filesystem

This is a multi-week enterprise integration project, not a hackathon-weekend task.

---

## 5. Conclusion

**Direct integration is unavailable.** The WorkBuddy Enterprise API exists and provides exactly the REST API you need, but:

- It requires enterprise account + beta whitelist approval (not available)
- It runs agents in a cloud sandbox (cannot access local GenBuddy files)
- It would require repackaging all investigation tools as cloud Skills

**The current manual workflow is the recommended path.** It already:

- Works end-to-end (proven with 4 genuine investigations)
- Tracks the full lifecycle through the dashboard
- Provides genuine agent reasoning with real tool execution
- Satisfies Track 2's requirement (proof of WorkBuddy usage)
- Requires no additional infrastructure, accounts, or APIs

**For the hackathon presentation:** Demonstrate the workflow live — submit a question in the dashboard, copy to WorkBuddy, watch the agent investigate in real-time, then show the dashboard updating with completed results. This is more impressive than an API call because it shows genuine autonomous agent behavior.

---

*Analysis performed by WorkBuddy AI agent*  
*Sources: WorkBuddy official docs (workbuddy.ai/docs), Tencent Cloud Enterprise docs (cloud.tencent.com/document/product/1831), local installation inspection (~/.workbuddy-ai/)*
