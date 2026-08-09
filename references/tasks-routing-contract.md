# Tasks routing contract

Use this handoff only when `$tlc-spec-driven` and `$tlc-loop` are named
together while authoring Tasks. `tlc-spec-driven` still owns the Tasks phase:
task granularity, dependencies, tests, gates, review, and approval. `tlc-loop`
contributes this output contract; it does not start Execute.

Recommended short request:

```text
$tlc-spec-driven create the tasks for feature <name> for execution by
$tlc-loop, with phases separated by stage.
```

When suggesting common domains, be explicit without making them mandatory:

```text
$tlc-spec-driven create the tasks for feature <name> for execution by
$tlc-loop. Separate phases by stage, prioritizing foundation, backend,
frontend, and docs as configured in .specs/loop.config.toml.
```

Those four names are examples. The available implementation stages are the
tables under `[stages.<name>]` in `.specs/loop.config.toml`. A project may use
names such as `mobile`, `infra`, or `data` instead.

## Required phase shape

Put `Stage` on the first non-empty line after the phase heading:

```markdown
### Phase 2: Checkout API

**Stage:** backend
```

The value must:

- use lowercase kebab-case: `[a-z][a-z0-9-]*`;
- match a configured `[stages.<value>]` exactly;
- occur zero or one time in a phase;
- never be inferred from the phase title.

Phase numbers are positive integers and unique. `Phase 2A`, duplicate
`Phase 2` headings, a missing title, a duplicate `Stage`, or a `Stage` placed
after other phase content is invalid.

## How to divide phases

Dependencies and cohesion come first. Then apply stage homogeneity:

1. Preserve dependency order.
2. Give each phase exactly one effective implementation stage.
3. Do not put tasks requiring different stages in the same phase.
4. A stage may reappear in later, non-consecutive phases.
5. Keep the normal target of about seven tasks per phase and approximate
   ceiling of ten.
6. Do not split a cohesive, testable task merely to obtain a prettier domain
   boundary.

An indivisible cross-domain task uses the stage capable of the whole task,
usually `implement`. If its parts can ship and be tested independently, split
the task first.

## Fallback, strict mode, and reserved names

`[execute] strict_routing = false` is the default. In that compatibility mode,
a phase with no `Stage` uses `implement`. An explicit unknown or malformed
stage is still an error; typos never fall back silently.

With strict routing, every phase must declare a stage:

```toml
[execute]
strict_routing = true
```

`verify`, `fix`, and `continue.respawn` are reserved runtime roles and cannot
route implementation phases in either mode.

## Valid example

```markdown
### Phase 1: Shared setup

**Stage:** foundation

### Phase 2: API

**Stage:** backend

### Phase 3: UI

**Stage:** frontend

### Phase 4: API integration

**Stage:** backend

### Phase 5: Guides

**Stage:** docs
```

The repeated `backend` stage is valid because document order and dependencies
are preserved.

## Invalid examples

```markdown
### Phase 1: API
Some explanation first.
**Stage:** backend
```

`Stage` is misplaced. These values are also invalid: `Backend` (not
lowercase), `backend_api` (not kebab-case), `backned` (unless explicitly
configured), and `verify` or `fix` (reserved).

## Gates before approval

Run both read-only validators before presenting `tasks.md` for approval:

```bash
python3 <tlc-spec-driven-dir>/scripts/validate_tasks.py <feature> --root <root>
python3 <tlc-loop-dir>/scripts/validate_routing.py <feature> --root <root>
```

Both must exit 0. `validate_routing.py` prints the effective phase-to-stage map
and aggregates all routing errors in one run. Neither command approves Tasks
or begins execution.
