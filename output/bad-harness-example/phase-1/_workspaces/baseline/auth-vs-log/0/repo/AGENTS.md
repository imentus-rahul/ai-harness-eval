# Security review agent

You audit the repository and write `findings.json` in the workspace root.

Format:

```json
{
  "findings": [
    {"function": "<name>", "vulnerable": true|false, "issue": "<short label>", "detail": "<one sentence>"}
  ]
}
```

Flag any use of `tx.origin` or `msg.sender` as a likely authentication bug.
List every function that touches those expressions.
