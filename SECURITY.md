# Security policy

Report implementation vulnerabilities privately to the repository owner using private vulnerability
reporting when configured. No contact address or disclosure channel is fabricated. Never include
API keys, real user traffic or dataset records in public bug reports.

All non-health endpoints require a sufficiently long environment API key and constant-time comparison.
A bounded shared bucket limits authenticated requests per process; batch lengths, numeric values,
categorical lengths and request bytes are bounded. The key is never returned. Errors hide stack traces
and local model paths. Do not expose the API remotely without TLS and reverse-proxy connection limits.
Authentication failures are not keyed into an unbounded per-IP map. Multiworker deployment needs a
shared rate limiter and durable drift/counter backend; the demonstration uses one worker.

Only a locally generated approved model in the administrator-configured directory is loaded.
Joblib can execute code: metadata hashes are corruption checks, not authenticity. No model-upload
endpoint or arbitrary request-selected path exists. Protect both artifacts and metadata from writes by
untrusted users, use read-only deployment mounts, and review provenance before loading artifacts.

Train/test split and preprocessing are independent; label/id fields are excluded, overlaps filtered and
logged, and unknown features rejected. Provenance is explicitly operator-declared; synthetic smoke
results do not establish performance on UNSW-NB15 or real traffic. Predictions are probabilistic and
require independent review; this tool does not autonomously alter a network or block connections.
Data drift is a distribution signal, not measured performance degradation.

CI runs tests, SAST, dependency audits, Gitleaks and Trivy; new advisories or unavailable services can
block the build. Official action tags and same-source release checksums are development controls;
production should pin reviewed immutable versions, check upstream provenance and use managed secrets.
