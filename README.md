# SmartChatBot

## Email PDF summaries through MCP

The **Email summary** button calls `POST /email-summary`. The FastAPI backend
generates a summary with the existing PDF summarizer, then calls the official
Resend MCP server's `send-email` tool using Streamable HTTP.

### 1. Configure environment variables

Add the Resend MCP variables shown below to your existing `.env`. Use a newly
rotated Resend API key with sending-only access and a verified sender domain.
Do not expose this key in the frontend.

```env
RESEND_API_KEY=re_your_new_key
RESEND_MCP_URL=http://127.0.0.1:3000/mcp
SUMMARY_RECIPIENT_EMAIL=kingvsj@gmail.com
SUMMARY_SENDER_EMAIL="PDF Assistant <noreply@your-verified-domain.com>"
SUMMARY_REPLY_TO_EMAIL=you@your-verified-domain.com
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

The FastAPI app authenticates each MCP request with `RESEND_API_KEY`; it is not
sent to the browser. The default MCP endpoint is `http://127.0.0.1:3000/mcp`.

### 4. Start this app

```bash
cd backend
uvicorn main:app --reload
```

Upload a PDF, then choose **Email summary**. The email is sent only to
`SUMMARY_RECIPIENT_EMAIL`, which makes the demo recipient server-controlled.
