import pytest

from ml.synthetic import generate
from ml.train import train


@pytest.fixture(scope="session")
def artifacts(tmp_path_factory):
    root = tmp_path_factory.mktemp("trained")
    data = generate(600)
    csv = root / "synthetic.csv"
    data.to_csv(csv, index=False)
    metadata, folder = train(
        csv, root / "models", root / "reports", provenance="synthetic", trees=20, min_f1=0, min_recall=0
    )
    return root, data, metadata, folder


@pytest.fixture
def example(artifacts):
    _, data, metadata, _ = artifacts
    return data[list(metadata["feature_schema"])].iloc[0].to_dict()
