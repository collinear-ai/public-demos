"""Build dashboard HTML from scenario data. Reads YAML/MD/PY files, produces JSON, injects into template."""
import json
import os
import sys

try:
    import yaml
except ImportError:
    os.system(f"{sys.executable} -m pip install pyyaml")
    import yaml

BASE = os.path.dirname(os.path.abspath(__file__))


def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def main():
    output = {}
    scenarios = [
        ("cerulean_qbr", "scenario_1_cerulean_qbr"),
        ("pinnacle_migration", "scenario_2_pinnacle_migration"),
    ]

    for key, dirname in scenarios:
        d = os.path.join(BASE, dirname)

        personas_data = yaml.safe_load(read_file(os.path.join(d, "personas.yaml"))) or {}
        rubrics_data = yaml.safe_load(read_file(os.path.join(d, "rubrics.yaml"))) or {}

        output[key] = {
            "organization": personas_data.get("organization", {}),
            "personas": personas_data.get("personas", []),
            "rubrics": rubrics_data,
            "project_dag": read_file(os.path.join(d, "project_dag.md")),
            "verifiers_code": read_file(os.path.join(d, "verifiers.py")),
        }

    # Read template and inject data
    template = read_file(os.path.join(BASE, "dashboard_template.html"))
    data_json = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    html = template.replace("__DATA__", data_json)

    out_path = os.path.join(BASE, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Written {out_path} ({size_kb:.0f} KB)")

    for key, dirname in scenarios:
        env = output[key]
        print(f"  {key}: {len(env['personas'])} personas, {len([k for k in env['rubrics'] if k != 'scoring_scale'])} rubric tasks, {len(env['verifiers_code'])} bytes verifier code")


if __name__ == "__main__":
    main()
