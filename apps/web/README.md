# Olive Admin Dashboard

Private staging dashboard for monitoring Olive paper executions. Authentication is
handled by a same-origin server route: the admin bearer token is stored only in an
HttpOnly cookie and is never persisted in browser storage.

Run locally with `npm install && npm run dev`, then open `http://localhost:3000`.

