# tx.origin triage skill

When reviewing `tx.origin`:

- **Vulnerable** only when `tx.origin` gates authorization (withdraw, transfer ownership, spend funds).
- **Not a finding** when `tx.origin` is used only for logging, events, or analytics.

When reviewing `msg.sender`:

- Prefer `msg.sender` for access control; flag `tx.origin` used where `msg.sender` is correct.

Always write `findings.json` with one entry per function you classify.
