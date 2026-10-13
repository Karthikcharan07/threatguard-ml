# Local model artifacts

Run `python -m ml.train` using a validated CSV. It creates an independent random hex version folder
containing `model.joblib` and `metadata.json`. Metadata records dataset SHA-256, provenance declaration,
column schema, seed, distributions, preprocessing, held-out metrics, training-only drift bins, quality
thresholds and installed library versions. Random version IDs identify separate runs; dataset hashes
and seeds support reproducibility of predictions/metrics. Version IDs themselves are not deterministic.

Only successful candidates atomically update `CURRENT`. Failed candidates remain reviewable and
exit 1; they never replace an approved model. API health is 503 until an approved artifact is readable.
The API loads the current version once at startup; restart after promoting a new model.

The ZIP intentionally excludes model binaries and generated datasets. Regenerate them with the
README smoke command or your downloaded official data. Inference requires the exact scikit-learn
version used for training; retain all recorded versions for reliable reproducibility.

Trust boundary: joblib is executable deserialization, not a safe interchange format. The operator
must own and protect the entire artifact directory. No request or endpoint accepts a model path or
uploads a model. The SHA-256 detects accidental corruption; it is not a signature. Malicious writers
who can replace a model and its metadata can replace the hash too. Never load external untrusted models.
For production consider signed artifact provenance and a reviewed safer serialization format.
