"""One-time migration from configs/<profile>.yaml to the shared config.yaml."""
import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="configs")
    parser.add_argument("--template", default="config/config.example.yaml")
    parser.add_argument("--output", default="config/config.yaml")
    args = parser.parse_args()

    template_path = Path(args.template)
    output_path = Path(args.output)
    if output_path.exists():
        raise SystemExit(f"{output_path} already exists; refusing to overwrite it")

    with template_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    config["profiles"] = []

    for path in sorted(Path(args.source_dir).glob("*.yaml")):
        if path.name.endswith(".example.yaml"):
            continue
        with path.open(encoding="utf-8") as f:
            profile = yaml.safe_load(f) or {}
        if not isinstance(profile, dict) or not profile.get("name"):
            raise SystemExit(f"{path}: expected a profile with a name")
        config["profiles"].append(profile)

    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
    print(f"Migrated {len(config['profiles'])} profiles to {output_path}")


if __name__ == "__main__":
    main()
