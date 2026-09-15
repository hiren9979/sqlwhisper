from pathlib import Path

import yaml

from text_to_sql.schema.glossary_loader import load_glossary
from text_to_sql.schema.metadata_loader import load_merged_schema

EXAMPLES_FILE = Path(__file__).with_name("few_shot_example.yaml")

def load_few_shot_examples():
    with EXAMPLES_FILE.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return data.get("examples", [])


def build_schema_documents():
    schema = load_merged_schema()
    documents = []
    for table_name, table_info in schema.items():
        lines = [
            f"Table: {table_name}",
            f"Description: {table_info['description'] or 'No description provided.'}",
            "",
            "Columns:",
        ]
        for column in table_info["columns"]:
            description = column["description"] or "No description provided."
            lines.append(
                f"- {column['name']} "
                f"(Type: {column['type']}): {description}"
            )
        documents.append(
            {
                "document_key": f"schema:{table_name}",
                "document_type": "schema",
                "content": "\n".join(lines),
                "metadata": {
                    "table_name": table_name,
                },
            }
        )
    return documents


def build_glossary_documents():
    glossary = load_glossary()
    documents = []
    for term, term_info in glossary.items():
        content = (
            f"Business term: {term}\n"
            f"Meaning: {term_info['description']}\n"
            f"SQL expression: {term_info['expression']}"
        )
        documents.append(
            {
                "document_key": f"glossary:{term}",
                "document_type": "glossary",
                "content": content,
                "metadata": {
                    "term": term,
                },
            }
        )
    return documents


def build_few_shot_documents():
    examples = load_few_shot_examples()
    documents = []
    for example in examples:
        content = (
            f"Question: {example['question']}\n"
            f"SQL:\n{example['sql']}"
        )
        documents.append(
            {
                "document_key": f"few_shot:{example['id']}",
                "document_type": "few_shot",
                "content": content,
                "metadata": {
                    "example_id": example["id"],
                },
            }
        )
    return documents


def build_all_documents():
    return build_schema_documents() + build_glossary_documents() + build_few_shot_documents()