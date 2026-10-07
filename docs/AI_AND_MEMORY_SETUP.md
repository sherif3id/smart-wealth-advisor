# AI and memory setup

## 1. Environment

Copy `.env.example` to `.env.local` and add secrets. Never expose the Gemini key through a `NEXT_PUBLIC_` variable.

```env
GEMINI_API_KEY=replace_with_a_fresh_google_ai_studio_key
DATABASE_URL=postgresql://wealth_app:change_me_in_production@localhost:5432/smart_wealth
```

## 2. PostgreSQL

With Docker installed:

```bash
docker compose up -d postgres
npm install
npm run dev
```

The advisor route creates its two memory tables on first successful request. The wider wealth schema remains in `docs/schema.sql`.

Without `DATABASE_URL`, AI conversations are retained in the browser on the current device. With PostgreSQL configured, profile and advisor messages persist server-side and can be retrieved across sessions using the same authenticated session identity.

## 3. Security notes

- Rotate any API key that has been pasted into chat, source code, screenshots, or a public location.
- Use a server-only environment variable named `GEMINI_API_KEY`.
- Production must replace the prototype browser session ID with the authenticated Clerk/Auth.js user or household ID.
- Apply per-user rate limits, usage quotas, audit logging, and abuse controls before public launch.
- Encrypt sensitive profile fields and enforce household-level row security.

## 4. AI behavior

The server route uses Gemini through `/api/advisor`. It supplies the user's profile, recent memory, financial safety policy, and conversation context. If the provider is unavailable, the UI clearly falls back to a deterministic local financial assistant rather than failing silently.
