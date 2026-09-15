from pathlib import Path
import yaml

GLOSSARY_FILE = Path(__file__).with_name("glossary.yaml")

def load_glossary():
    with GLOSSARY_FILE.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    return data.get("terms", {})