"""Exporta o contrato gerado sem conectar ao banco."""

import argparse
import json
from pathlib import Path

from app.core.config import ROOT, Settings
from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "openapi.json")
    args = parser.parse_args()
    app = create_app(Settings(_env_file=None))
    try:
        args.output.write_text(
            json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        app.state.engine.dispose()
    print(f"Contrato exportado: {args.output.name}")


if __name__ == "__main__":
    main()
