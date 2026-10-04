# tx.origin triage skill

When reviewing `tx.origin`:

- **Vulnerable** only when `tx.origin` gates authorization (withdraw, transfer ownership, spend funds).
- **Not vulnerable** when `tx.origin` is used only for logging, events, or analytics (`logTransfer` style).

When reviewing `msg.sender`:

- Prefer `msg.sender` for access control; flag `tx.origin` used where `msg.sender` is correct.

## findings.json (mandatory)

After reading `Wallet.sol`, write `findings.json` with **one entry per function** that uses `tx.origin`:

- `withdraw` → `vulnerable: true` (authorization gated by `tx.origin`)
- `logTransfer` → `vulnerable: false` (logging/event only)

Example:

```json
{
  "findings": [
    {"function": "withdraw", "vulnerable": true, "issue": "tx.origin auth", "detail": "withdraw uses tx.origin for access control."},
    {"function": "logTransfer", "vulnerable": false, "issue": "logging only", "detail": "tx.origin used only in an event, not authorization."}
  ]
}
```

Do not omit either function. Do not stop until `findings.json` exists with both booleans set.

## Vault / `withdrawAll` (caller-check task)

If `withdrawAll` uses `tx.origin` in a `require` for access control, classify:

- `withdrawAll` → `vulnerable: true` (same rule as `withdraw`: `tx.origin` must not gate funds)

Example for `Vault.sol` / caller-check:

```json
{
  "findings": [
    {
      "function": "withdrawAll",
      "vulnerable": true,
      "issue": "tx.origin",
      "detail": "tx.origin in require is unsafe vs msg.sender."
    }
  ]
}
```

## keep-suite (Python regression)

Do **not** modify `app/config.py` or anything under `tests/`.
Write `findings.json` only (empty `findings` list is fine). Visible tests must keep passing.
