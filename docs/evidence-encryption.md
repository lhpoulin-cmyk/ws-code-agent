# Evidence and configuration protection

Structured configuration, manifests, indexes, prompts, and accepted metadata
use SOPS encryption with age recipients. Large accepted evidence bundles use
age-encrypted archives indexed by a SOPS-encrypted manifest.

Model blobs remain unencrypted and reconstructable, pinned by exact tag and
resolved digest; they are not authoritative evidence.

Protect indefinitely: accepted benchmark evidence, model-selection decisions,
digests, prompt and `VOICE.md` revisions, scoring, hardware/software baselines,
performance/thermal evidence, accepted configuration, amendments, and
anomalies. No automatic deletion of accepted evidence is authorized.

The exact age/SOPS identity and recovery method are unresolved pending
`auth-cp` or the approved existing secret authority. Private keys, SOPS
secrets, and decrypted evidence never enter Git.

Local-at-rest protection is a separate layer: the application volume is LUKS2
with an interactively entered passphrase shared with Foundation and an
independent recovery key protected in both approved vaults. The shared
passphrase coupling is an explicitly accepted operator tradeoff. LUKS2 does
not replace SOPS/age for portable configuration or exported evidence.
