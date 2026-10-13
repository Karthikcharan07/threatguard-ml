"""Install pinned official Linux x64 release binaries for CI, with checksum verification."""

import argparse
import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path

RELEASES = {
    "gitleaks": (
        "gitleaks/gitleaks",
        "8.30.1",
        "gitleaks_8.30.1_linux_x64.tar.gz",
        "gitleaks_8.30.1_checksums.txt",
    ),
    "trivy": (
        "aquasecurity/trivy",
        "0.75.0",
        "trivy_0.75.0_Linux-64bit.tar.gz",
        "trivy_0.75.0_checksums.txt",
    ),
}


def download(url):
    # Only fixed, trusted official HTTPS release endpoints are constructed.
    with urllib.request.urlopen(url, timeout=30) as response:  # nosec B310
        blob = response.read(120_000_001)
    if len(blob) > 120_000_000:
        raise ValueError("Release exceeds size limit")
    return blob


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", default=".tools")
    parser.add_argument("--tools", nargs="+", choices=RELEASES, default=list(RELEASES))
    args = parser.parse_args()
    destination = Path(args.destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for tool in args.tools:
        repository, version, asset, checksums = RELEASES[tool]
        base = f"https://github.com/{repository}/releases/download/v{version}/"
        hashes = download(base + checksums).decode("utf-8")
        expected = next(
            line.split()[0] for line in hashes.splitlines() if line.split()[-1].lstrip("*") == asset
        )
        blob = download(base + asset)
        if hashlib.sha256(blob).hexdigest() != expected:
            raise ValueError("Release checksum mismatch")
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
            member = next(m for m in archive.getmembers() if m.name == tool and m.isfile())
            if member.size > 200_000_000:
                raise ValueError("Binary exceeds size limit")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("Missing binary")
            (destination / tool).write_bytes(source.read())
        (destination / tool).chmod(0o755)
        print(f"Installed {tool} {version}")


if __name__ == "__main__":
    main()
