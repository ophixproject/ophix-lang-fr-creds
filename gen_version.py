"""Write src/ophix_lang_fr_creds/_version.py from pyproject.toml."""
import tomllib
from pathlib import Path

root = Path(__file__).parent
with open(root / "pyproject.toml", "rb") as f:
    version = tomllib.load(f)["project"]["version"]

target = root / "src" / "ophix_lang_fr_creds" / "_version.py"
target.write_text(f'__version__ = "{version}"\n')
print(f"Wrote {target} -> {version}")
