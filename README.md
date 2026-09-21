# SmartChatBot

## Agentic PDF chat with LangGraph and Resend MCP

After PDF upload, `POST /chat` runs a LangGraph workflow. A structured-output
LLM router sends each request to a question-answering, summary, analysis, or
comparison agent. Email requests pause for human approval before the approved
content is sent through the official Resend MCP server's `send-email` tool.

Example chat commands:

```text
Summarize this document.
Extract the important dates and action items.
Compare the uploaded documents.
Email the previous answer.
Create a summary and email it.
```

For email requests, the agent emails a draft to the configured approver and
pauses. Reply `APPROVE` or `REJECT` to that email. Resend Inbound delivers the
reply to a verified webhook, which resumes the saved LangGraph workflow.

### 1. Configure environment variables

Add the Resend MCP variables shown below to your existing `.env`. Use a newly
rotated Resend API key with sending-only access and a verified sender domain.
Do not expose this key in the frontend.

```env
RESEND_API_KEY=re_your_new_key
RESEND_RECEIVING_API_KEY=re_your_full_access_receiving_key
RESEND_MCP_URL=http://127.0.0.1:3000/mcp
SUMMARY_RECIPIENT_EMAIL=kingvsj@gmail.com
SUMMARY_SENDER_EMAIL="PDF Assistant <noreply@your-verified-domain.com>"
SUMMARY_REPLY_TO_EMAIL=you@your-verified-domain.com
APPROVAL_EMAIL=approver@example.com
RESEND_RECEIVING_ADDRESS=approval@your-id.resend.app
RESEND_WEBHOOK_SECRET=whsec_your_webhook_signing_secret
APPROVAL_TOKEN_TTL_SECONDS=3600
PUBLIC_BASE_URL=https://your-public-backend.example.com
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the official Resend MCP server

Install Node.js 20+ if it is not available, then run this in a separate terminal:

```bash
npx -y resend-mcp --http --port 3000
```

The FastAPI app authenticates each MCP request with the sending-only
`RESEND_API_KEY`; it is not sent to the browser. Retrieving the body of inbound
approval replies requires a separate full-access `RESEND_RECEIVING_API_KEY`.
The default MCP endpoint is `http://127.0.0.1:3000/mcp`.

### 4. Configure Resend Inbound

Enable Receiving for a Resend-managed `*.resend.app` address or your own
receiving subdomain. In the Resend dashboard, create an `email.received` webhook
pointing to:

```text
https://your-public-backend.example.com/webhooks/resend/inbound
```

Copy that webhook's signing secret into `RESEND_WEBHOOK_SECRET`. For local
development, expose FastAPI using a secure tunnel so Resend can reach the
webhook. The webhook verifies the raw request signature, checks the configured
approver, enforces single-use expiring tokens, and ignores duplicate events.

### 5. Start this app

```bash
cd backend
uvicorn main:app --reload
```

Upload one or more PDFs and use the chat box for both questions and actions.
Email is sent only to `SUMMARY_RECIPIENT_EMAIL`, which keeps the demo recipient
server-controlled. The legacy `POST /email-summary` endpoint remains available,
but the browser UI uses the human-approved LangGraph flow.
