# Evaluator-private calibration material

Evaluator-only C01 oracle and calibration answer-review material lives at
`~/.local/share/ws-code-agent/alpha-private/`, outside this repository and the
future model-visible executor root. The current store is local calibration
infrastructure, not durable private-holdout architecture.

| Artifact | Digest | Role |
|---|---|---|
| `C01-oracle.py` | `a5d82c5b073bb35f6ee03554cb3610889999e742d1df2b4477395bbe2f7d75b9` | C01 evaluator oracle |
| `CALIBRATION_REVIEW.md` | `4a4a4ab94741461670c7796ebdb8926273ea4e4513090b07ed15d4a0def3383a` | evaluator answer/review notes |

These artifacts and their prior committed forms were historically exposed. They
are not cryptographic or historical secret holdouts and must not support strong
public comparative claims. Future genuine private holdouts must never be
committed. A first disposition experiment must give the model no access to this
repository, Git history, this private store, hidden oracle, or web retrieval.
