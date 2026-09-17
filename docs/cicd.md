# CI/CD and developer experience

Three gates, running fastest-first: pre-commit (seconds), pre-push (tens of
seconds), CI (minutes). Anything CI enforces, a developer can also run locally
with `make lint` and `make test`.

## Gate 1 — pre-commit hooks (Husky + lint-staged)

Installed automatically by `pnpm install` via the `prepare` script.

### `.husky/pre-commit`

Runs `lint-staged`, which touches only the files actually staged:

| Pattern                         | Action                                                   |
| ------------------------------- | -------------------------------------------------------- |
| `frontend/**/*.{ts,tsx}`        | `eslint --fix --max-warnings=0`, then `prettier --write` |
| `backend/**/*.py`               | `ruff check --fix`, then `ruff format`                   |
| `*.{json,md,yml,yaml,css,html}` | `prettier --write`                                       |

Fixed files are re-staged, so the commit contains the formatted version. A
lint error that cannot be auto-fixed aborts the commit.

Scoping to staged files is what keeps this fast enough to survive: linting the
whole repository on every commit is how teams end up with `--no-verify` in their
muscle memory.

### `.husky/commit-msg`

`commitlint` enforces Conventional Commits, with an allow-list of scopes
(`auth`, `projects`, `sites`, `analytics`, `map`, `charts`, `ui`, `api`, `db`,
`ci`, `deps`, `docs`, `config`, `tests`, `release`):

```
feat(sites): add polygon drawing with area validation
fix(auth): reject refresh tokens presented as bearer credentials
```

The brief asks for a clean, logical commit history. Enforcing it at commit time
is the only way that survives a long day.

### `.husky/pre-push`

A cheap safety net before code leaves the machine: `tsc --noEmit` on the
frontend and the backend unit suite. Not the full test run — that belongs in CI,
where waiting is free.

## Gate 2 — GitHub Actions

Four workflows, each scoped by `paths` so a backend change does not run the
frontend pipeline. `concurrency` cancels superseded runs on the same branch.

### `ci-backend.yml`

| Job            | Steps                                                                          |
| -------------- | ------------------------------------------------------------------------------ |
| **quality**    | `ruff check` (with GitHub annotations), `ruff format --check`, `mypy --strict` |
| **test**       | Full `pytest` against a **PostGIS service container**, coverage gated at 80%   |
| **migrations** | `upgrade head` → `downgrade base` → `upgrade head`, then a drift check         |

Two of these deserve comment.

**The PostGIS service container** means tests run against the same extension set
as production. A PostGIS-specific bug — a `geography` cast dropped, a GIST index
missing, `ST_Extent` parsing changed — fails in CI rather than on the demo URL.
Mocking the database would test the mock.

**The migration job** proves three separate things: migrations apply from
nothing, they are reversible (a migration you cannot undo is one you cannot roll
back during an incident), and the models match the schema. The last check
autogenerates a throwaway revision and fails if it contains any operation:

```bash
alembic revision --autogenerate -m "drift-check" --rev-id drift_check
grep -qE "op\.(create|drop|add|alter)" alembic/versions/drift_check_*.py && exit 1
```

That catches the most common real mistake: editing a model and forgetting the
migration.

### `ci-frontend.yml`

| Job         | Steps                                                                              |
| ----------- | ---------------------------------------------------------------------------------- |
| **quality** | `prettier --check`, `eslint --max-warnings=0`, `tsc --noEmit`, `vitest --coverage` |
| **build**   | Production `vite build`, bundle sizes posted to the job summary                    |

`pnpm install --frozen-lockfile` fails if `package.json` and the lockfile
disagree — which catches a dependency added without committing the lockfile.

`--max-warnings=0` means warnings are errors. A tolerated warning is a warning
nobody will ever fix.

### `deploy.yml`

Triggered by `workflow_run` on **both** CI workflows completing successfully on
`main`. This is the part that makes the gate real: a plain `push` trigger would
race CI and could ship a commit whose tests were still running.

1. **deploy-api** — POSTs the Render deploy hook, then polls
   `/health/ready` for up to ten minutes. That endpoint queries
   `PostGIS_Lib_Version()`, so a green deploy means the API is up _and_ reached
   its database with PostGIS installed. Render runs
   `alembic upgrade head` as its pre-deploy command, so the schema is applied
   before the new instance takes traffic.
2. **deploy-web** — `vercel pull / build / deploy --prod`, then a smoke request
   against the deployed URL. It `needs: deploy-api`, so the frontend is never
   pointed at an API that has not finished migrating.

### `codeql.yml`

Static security analysis for TypeScript and Python on every PR and weekly, so a
newly-published advisory is caught even without a code change.

### `dependabot.yml`

Weekly npm and pip updates, monthly Actions and Docker. Minor and patch updates
are grouped into one PR per ecosystem to keep review load sane; CI still gates
each one.

## Required setup

### Repository secrets

| Secret                   | Purpose                                         |
| ------------------------ | ----------------------------------------------- |
| `RENDER_DEPLOY_HOOK_URL` | Render service → Settings → Deploy Hook         |
| `VERCEL_TOKEN`           | Vercel account → Settings → Tokens              |
| `VERCEL_ORG_ID`          | From `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID`      | Same file                                       |

### Repository variables

| Variable  | Example                            |
| --------- | ---------------------------------- |
| `API_URL` | `https://darukaa-api.onrender.com` |
| `WEB_URL` | `https://darukaa-earth.vercel.app` |

### Branch protection on `main`

Require a pull request, require **Backend CI** and **Frontend CI** to pass,
require branches to be up to date, and disallow force pushes.

## Local equivalents

```bash
make lint    # everything CI's quality jobs run
make test    # backend pytest + frontend vitest
make format  # auto-fix formatting across the repo
```

If `make lint && make test` passes, CI passes. That equivalence is deliberate:
the moment CI checks something a developer cannot reproduce locally, CI becomes
a lottery.
