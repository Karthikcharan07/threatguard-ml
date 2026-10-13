# GitHub repository

Suggested repository name: `threatguard-ml`

Description: Reproducible UNSW-NB15-ready intrusion classification with a secure FastAPI API, versioned models, drift monitoring and DevSecMLOps CI.

1. Extract the ZIP. Open a terminal inside the single project folder.
2. Create an empty repository on GitHub (do not add a README or license there).
3. Replace `YOUR_USERNAME` in the commands below with your GitHub username.
4. Check `git status` and `git diff --cached` before committing. Do not stage API keys, `.env`, datasets, or models.
5. Run:
```bash
git init
git branch -M main
git add .
git diff --cached --stat
git commit -m "Initial academic project"
git remote add origin https://github.com/YOUR_USERNAME/threatguard-ml.git
git push -u origin main
```
6. Open Actions on GitHub and inspect each test/security/container job. CI can fail on real
vulnerabilities or unreachable advisory services; fix the cause instead of disabling the gate.
7. For a later change, commit and push again. Nothing in this delivery uploaded a repository.

The workflows test Python 3.11 and 3.12, lint, perform SAST, audit the installed environment including
transitive dependencies, run Gitleaks on git history, scan configurations with Trivy, generate an SBOM,
and build Docker only after tests and security gates pass. ThreatGuard also trains a labelled synthetic
smoke model. Artifacts store reports, not credentials or datasets. There is no automatic production
deployment: hosting, TLS, secret configuration, and real-data model approval remain operator steps.
Actions use official major-version tags; production deployments should review and pin immutable SHAs.
Release archives are checksum-verified against the same official release, which protects against accidental
corruption, not compromise of the publisher. Review upstream release provenance before production use.
