# CLAUDE.md — Security assessment context

This file tells Claude Code how to security-assess **this repository** using three
tools. Everything here is scoped to code and apps **I own or am explicitly
authorized to test**. Do not point the offensive tooling at third-party systems.

---

## Scope & rules of engagement

- **Targets:** only this repo and the local/dev instances of the app it builds.
- **Authorization:** assessing my own project = authorized testing. Do not run
  network attacks, scanning, or exploitation against any host I do not own.
- **No live exploitation by default.** Find, explain, and fix. Only demonstrate a
  vulnerability (build a PoC, run an exploit path) if I say so in the prompt, and
  only against local/dev.
- **Secrets:** if you find a real credential, treat it as compromised — tell me,
  don't paste it into reports or commits, and recommend rotation.
- **Reports over commits.** Propose diffs; let me approve before you change code.

---

## The three tools

### 1. AXguard — defensive pre-ship scanner (primary)

Repo: `https://github.com/Awarexone/AXguard` · MIT · Python 3.10+
Deterministic CLI scanner + a pack of security "skills" for the agent. This is the
default tool for "is this safe to ship?"

**Install (once):**
```bash
git clone https://github.com/Awarexone/AXguard.git
cd AXguard
chmod +x install.sh
./install.sh --agent claude        # or: all  (cursor / opencode / codex too)
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

**Core commands (run from this repo's root):**
```bash
axguard scan .                       # fast pass
axguard audit .                      # full audit
axguard audit . --fail-on high       # gate: non-zero exit on high+ findings
axguard scan . --format json -o out.json
```
Reports land in `.findings/axguard/axguard-report.{html,md,json}`.

**Diagnostics (understand, don't just match rules):**
```bash
axguard surface .    # map stack, routes, sinks, controls, trust boundaries
axguard flow .       # data/control flow
axguard verify .     # confirm a finding is real
axguard adversary .  # think like an attacker against the surface
axguard evidence .   # evidence for a finding
axguard paths .      # attack graph + vuln chaining (alias: attack-paths)
```

**MCP flow (if the AXguard MCP server is wired in):**
`axguard_security_review` → investigate → `axguard_verify_fix`
(`axguard_verify_fix` reports RESOLVED / STILL_PRESENT / REGRESSED by fingerprint —
never call something fixed on a path rename alone).

Specialist coverage: secrets, auth, injection (SQL/SSTI/path), SSRF, XSS, cloud,
crypto, supply chain, GraphQL, file upload, debug endpoints, and AI-agent risks.

### 2. claude-red — offensive methodology skills (adversarial review)

Repo: `https://github.com/SnailSploit/Claude-Red` · MIT
A library of `SKILL.md` files that give you expert attacker methodology per surface
(web, AD, container/k8s, CI/CD, crypto/TLS, exploit-dev, IoT, privesc, etc.).
Skills load on demand from conversational triggers — mention "SQL injection" and the
`offensive-sqli` skill primes in.

**Install:**
```bash
git clone https://github.com/SnailSploit/claude-red ~/.claude/skills/claude-red
# or, selectively:
cd claude-red && ./install.sh --category web
```

**Use here for:** adversarial thinking about *my* app — "how would an attacker reach
this sink," business-logic abuse, auth/session weaknesses, chaining. Use it to
*reason*, not to launch attacks at anything external.

### 3. Burp + Claude Code (MCP) — web / client-side JS analysis

A workflow, not a repo. When I'm testing a running local instance of this app with
Burp Suite, the Burp MCP server lets you read proxy history and captured JS so you
can analyze client-side code, find secrets/endpoints in bundles, and trace
dangerous sinks in the browser.

**Setup:** run Burp Suite with its MCP server enabled, register that MCP endpoint
with Claude Code, then ask me to route proxy/JS history through it. Only ever
against `localhost`/dev targets I own.

---

## How to assess this project

When I say "assess this," work this loop and stop for my review before editing code:

1. **Map** — `axguard surface .` (and read the app structure) so you know the stack,
   entry points, sinks, and trust boundaries before hunting.
2. **Scan** — `axguard audit .`. Read the report; don't just relay it.
3. **Adversarial pass** — pull the relevant claude-red skill(s) for the surfaces the
   map exposed and reason about what the scanner might miss (logic flaws, auth,
   chaining). If a running instance + Burp is in play, analyze the client-side JS.
4. **Triage** — for each finding: what it is, why it's exploitable *here*, severity,
   and the concrete impact. Drop false positives with a one-line reason.
5. **Fix** — propose minimal diffs. Wait for my approval.
6. **Re-verify** — re-run `axguard audit .` (or `axguard_verify_fix`) and confirm
   RESOLVED by fingerprint, not by the code merely looking different.
7. **Report** — short summary: what was found, what was fixed, what's left, and any
   residual risk I should accept or defer.

## Output style

- Lead with the highest-severity, actually-exploitable issues.
- Every finding: file:line, the vulnerable flow, and the fix.
- No fear-mongering, no padding the list to look thorough. Real issues only.
- If nothing serious is found, say so plainly.
