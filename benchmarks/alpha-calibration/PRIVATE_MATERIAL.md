# Evaluator-private calibration material

Evaluator-only calibration material lives at
`~/.local/share/ws-code-agent/alpha-private/`, outside this repository and the
future model-visible executor root. The current store is local calibration
infrastructure, not durable private-holdout architecture.

| Artifact | Digest | Role |
|---|---|---|
| `C01-oracle.py` | `a5d82c5b073bb35f6ee03554cb3610889999e742d1df2b4477395bbe2f7d75b9` | C01 evaluator oracle |
| `CALIBRATION_REVIEW.md` | `4a4a4ab94741461670c7796ebdb8926273ea4e4513090b07ed15d4a0def3383a` | evaluator answer/review notes |
| `C03-evaluator-notes.md` | `e4dc8ab187f96d5e0e837bc4ba7abf47002ba6efb3302661300c2e90c0164857` | C03 evaluator disposition and effect notes |
| `C04-evaluator-notes.md` | `fbdb7e5587ef0f67c9ec48b9b3d8af5c9bf51e089f7670a377edb186603a3bb0` | C04 evaluator disposition and state-transition notes |
| `C05-evaluator-notes.md` | `4f322ad132d07824715d180766dd394a22a87ffcad65d8ea47d0e53e6fa1ff60` | C05 evaluator disposition and multi-repository notes |

These C01–C05 artifacts and their prior committed forms were historically
exposed. They are not cryptographic or historical secret holdouts and must not
support strong public comparative claims. The current split is suitable only for
bounded offline calibration where the selected model cannot access this
repository, its Git history, this private store, hidden oracle, or web
retrieval. Future genuine private holdouts must originate privately and never be
committed.
