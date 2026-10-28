"""The repository's package list starts empty and grows with each import. Tests run against the package list
the release tooling was proven with (Tests/Fixtures/inventory), as the trusted allowlist and default inventory."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common  # noqa: E402

ROOT = Path(__file__).resolve().parent / "Fixtures" / "inventory"
for function in (common.allowlist, common.url, common.inventory):
    function.__defaults__ = (ROOT,)
