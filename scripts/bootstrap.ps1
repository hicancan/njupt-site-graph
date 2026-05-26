$ErrorActionPreference = "Stop"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e D:\code\github\hicancan\static-site-graph[dev]
python -m pip install -e .[dev]
python -m sitegraph.cli validate-config configs/sites/jwc/site.yaml
