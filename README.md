# Serverless AWS Chat App

A real-time group chat application built entirely on AWS serverless infrastructure. Messages are delivered instantly via WebSocket connections, authenticated through Cognito JWTs, and persisted in DynamoDB. No servers to manage, no idle costs.

---

## Architecture

```
Client
  │
  ├── WebSocket (wss://)  ──►  API Gateway WebSocket API
  │                                  │
  │                         ┌────────┴────────────┐
  │                    $connect              sendMessage
  │                  (+ Authorizer)               │
  │                         │                     │
  │                   Lambda (app.py)    Lambda (send_message.py)
  │                         │                     │
  │                   ConnectionsTable   ┌─────────┴──────────┐
  │                   (DynamoDB)    ConnectionsTable     MessagesTable
  │                                 (broadcast scan)    (persist msg)
  │
  └── Auth (token query param)  ──►  Lambda Authorizer (auth.py)
                                            │
                                     Cognito User Pool
                                     (JWKS / RS256)
```

**Flow:**

1. User registers/logs in via Cognito (USER_PASSWORD_AUTH)
2. Client connects to WebSocket URL with JWT as `?token=` query param
3. Lambda Authorizer validates the token against Cognito JWKS, returns Allow/Deny policy
4. On Allow, `$connect` handler stores `connectionId + userId + email` in DynamoDB with 24h TTL
5. Client sends `{ "action": "sendMessage", "message": "..." }`
6. `sendMessage` handler persists the message, then scans all active connections and broadcasts
7. Stale connections (GoneException) are cleaned up inline
8. On tab close / disconnect, `$disconnect` removes the connection record

---

## AWS Services Used

| Service | Role |
|---|---|
| API Gateway WebSocket | Persistent client connections, route by `action` key |
| Lambda (Python 3.12) | Connect, disconnect, send, authorize |
| DynamoDB | Connections table (active sessions) + Messages table (history) |
| Cognito User Pool | User identity, JWT issuance |
| IAM | Least-privilege policies per Lambda via SAM |

---

## Project Structure

```
.
├── template.yaml          # SAM/CloudFormation — all infrastructure as code
├── samconfig.toml         # SAM CLI deployment config
├── Taskfile.yaml          # Task runner (build, deploy, delete)
└── src/
    ├── app.py             # $connect handler — stores connection in DynamoDB
    ├── auth.py            # Lambda Authorizer — validates Cognito JWT (RS256)
    ├── disconnect.py      # $disconnect handler — removes connection record
    ├── send_message.py    # sendMessage handler — persists + broadcasts
    └── requirements.txt   # python-jose[cryptography]
```

---

## Key Design Decisions

**Lambda Authorizer on `$connect` only**
The JWT is validated once at connection time. API Gateway caches the authorizer result and passes `userId` + `email` through context to all subsequent route handlers — avoiding per-message token verification overhead.

**TTL on ConnectionsTable**
Connections are written with a 24-hour TTL. If a client disconnects without triggering `$disconnect` (network drop, crash), DynamoDB automatically expires the record rather than leaving ghost entries.

**GoneException cleanup in `sendMessage`**
When broadcasting, any connection that returns `GoneException` is collected and deleted in the same invocation. This keeps the connections table clean without a separate cleanup job.

**GSI on MessagesTable (`userId-timestamp-index`)**
Messages are keyed by UUID but indexed by `userId + timestamp`, allowing efficient per-user message history queries without a table scan.

**IAM least privilege**
Each Lambda has only the DynamoDB permissions it needs. `SendMessageFunction` additionally holds `execute-api:ManageConnections` to post back to connected clients via the management API.

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI (`pip install aws-sam-cli`)
- Python 3.12
- [Task](https://taskfile.dev) (optional, for Taskfile commands)

---

## Deploy

```bash
# Build and deploy (guided first-time setup)
sam build
sam deploy --guided

# Or using Taskfile
task deploy
```

SAM will output:

```
WebSocketURL = wss://<api-id>.execute-api.<region>.amazonaws.com/Prod
UserPoolId   = <pool-id>
ClientId     = <client-id>
```

---

## Connect & Test

**1. Register a user**

```bash
aws cognito-idp sign-up \
  --client-id <ClientId> \
  --username you@example.com \
  --password "YourPassword1!"
```

**2. Confirm the user (skip email verification in dev)**

```bash
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id <UserPoolId> \
  --username you@example.com
```

**3. Get a JWT**

```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <ClientId> \
  --auth-parameters USERNAME=you@example.com,PASSWORD="YourPassword1!"
```

Copy the `IdToken` from the response.

**4. Connect via WebSocket**

```bash
# Install wscat if needed: npm install -g wscat
wscat -c "wss://<api-id>.execute-api.<region>.amazonaws.com/Prod?token=<IdToken>"
```

**5. Send a message**

```json
{"action": "sendMessage", "message": "hello world"}
```

All connected clients will receive:

```json
{"sender": "you@example.com", "message": "hello world", "timestamp": 1710000000}
```

---

## Teardown

```bash
sam delete
# or
task delete
```

---

## Known Limitations / Roadmap

- [ ] No REST endpoint for message history — clients only see messages sent after they connect
- [ ] `sendMessage` uses `scan` for broadcasting — fine for small groups, needs pagination for scale
- [ ] JWKS fetched on every cold start — module-level caching would reduce latency
- [ ] No frontend client — test via `wscat` or build your own
- [ ] No rate limiting on `sendMessage` route

---

## Tech Stack

`Python 3.12` · `AWS SAM` · `API Gateway WebSocket` · `Lambda` · `DynamoDB` · `Cognito` · `python-jose`