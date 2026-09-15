from pathlib import Path

import yaml

from text_to_sql.db.schema_extractor import extract_schema

METADATA_FILE = Path(__file__).with_name("metadata_config.yaml")

def load_metadata_config():
    with METADATA_FILE.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    return data.get("tables", {})

def load_merged_schema():
    live_schema = extract_schema()
    metadata = load_metadata_config()

    tables = {}

    for table_name, column_name, data_type in live_schema:
        table_config = metadata.get(table_name, {})

        if table_name not in tables:
            tables[table_name] = {
                "description": table_config.get("description", ""),
                "columns": [],
            }

        column_config = table_config.get("columns", {}).get(column_name, {})

        tables[table_name]["columns"].append(
            {
                "name": column_name,
                "type": data_type,
                "description": column_config.get("description", ""),
            }
        )

    return tables