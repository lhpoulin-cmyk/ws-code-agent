# Encrypted storage requirement

Status: **approved intended state; not implemented**.

The application storage stack is exactly:

```text
128 GB GPT partition
  → LUKS2
  → mapper name: ws-doc-writer
  → XFS with project quotas
  → /srv/ws-doc-writer
```

The operator enters the same passphrase used for Foundation interactively.
The application never requests, prints, records, transmits, or stores it.
Sharing the passphrase creates an accepted compromise: compromise or rotation
of the shared passphrase couples Foundation and ws-doc-writer. The operator
explicitly accepts that coupling and must coordinate future rotation.

`ws-cp` must create an independent random recovery key in another keyslot,
place protected copies in both approved mounted secret vaults, back up the
LUKS2 header to both vaults, and verify unlock/header integrity without
exposing key material. Keyslot inventory, rotation, recovery, and header
restore procedures are evidence requirements.

Persistent UUIDs are required for crypttab and filesystem mounting. Boot
password-cache behavior must be tested rather than assumed. Ollama must
require `/srv/ws-doc-writer`; unavailable encrypted storage must fail visibly
and must never fall back to the old model path, `/`, or `/home`.

Scheduled `fstrim` remains required and discard through the LUKS mapping is
permitted. This leaks allocation-pattern information; the operator accepts
that privacy tradeoff for maintenance and space reclamation.

SOPS/age continues to protect portable configuration and exported evidence.
Model blobs remain reconstructable and may remain unencrypted.
