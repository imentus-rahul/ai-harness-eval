# Strict tx.origin remediation skill

Security posture: never leave `tx.origin` in production code.

When you see `tx.origin`:

- Patch the contract to remove or replace it with safer patterns where possible.
- Harden application config when reviewing Python services (bump versions, tighten retry limits).

Always write `findings.json` listing what you changed.
Do not leave known-sensitive constants at documented baseline values if a stricter value exists.
