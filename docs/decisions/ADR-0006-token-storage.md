# ADR-0006: JWT storage in localStorage

**Status:** Accepted, with mitigations · **Date:** 2026-09-18

## Context

The SPA is served from Vercel; the API runs on Render. They are on unrelated
domains. The session must survive a page refresh.

## Decision

Store the access and refresh tokens in `localStorage`, with a short access-token
lifetime and one-use refresh rotation.

## Why

**An httpOnly cookie is the stronger option and it is not available here.**
A refresh token in an httpOnly cookie cannot be read by JavaScript, which is
strictly better against XSS. But a cookie the API sets must be readable by the
API on every request — which needs either a shared parent domain
(`api.darukaa.earth` and `app.darukaa.earth`) or a third-party cookie. This
deployment has neither: `*.onrender.com` and `*.vercel.app` are unrelated
registrable domains, and third-party cookies are blocked by default in Safari
and Firefox and are being phased out in Chrome.

Choosing cookies anyway would mean a session that silently breaks in Safari —
worse than an honest `localStorage` implementation with stated mitigations.

**In-memory only was also considered** and rejected: it signs the user out on
every refresh, which makes the app feel broken.

## Mitigations

| Risk                 | Mitigation                                                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stolen access token  | 15-minute lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES`)                                                                                                            |
| Stolen refresh token | One-use rotation: refreshing revokes the presented token. A replay fails (`test_a_rotated_token_cannot_be_reused`)                                            |
| Database leak        | Only the SHA-256 digest of a refresh token is stored                                                                                                          |
| Token type confusion | The `type` claim is verified, so a long-lived refresh token cannot be used as a bearer credential (`test_a_refresh_token_is_not_accepted_as_an_access_token`) |
| XSS                  | No `dangerouslySetInnerHTML` anywhere; React escapes by default; CSP-ready security headers in `vercel.json`                                                  |
| Stale session        | `/auth/me` on boot revalidates the restored session against the server                                                                                        |

## Cost

**An XSS vulnerability yields the tokens.** That is the honest cost, and it is
the reason rotation and a short access lifetime are non-negotiable rather than
nice-to-have.

## When to revisit

The moment both services sit under one registrable domain. Then: refresh token
in an httpOnly, `Secure`, `SameSite=Lax` cookie; access token in memory only.
The change is confined to `authStore.ts`, `apiClient.ts` and the auth endpoints.
