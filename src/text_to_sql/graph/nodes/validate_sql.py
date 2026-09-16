import sqlglot
from sqlglot import exp

from text_to_sql.db.schema_extractor import extract_schema
from text_to_sql.graph.state import AgentState


DEFAULT_LIMIT = 100


def get_database_schema():
    """Return known tables and columns from the live PostgreSQL schema."""
    rows = extract_schema()
    schema = {}
    for table_name, column_name, _ in rows:
        schema.setdefault(table_name, set()).add(column_name)
    return schema


def validate_statement_type(expression):
    """Allow only SELECT statements."""
    if not isinstance(expression, exp.Select):
        raise ValueError("Only SELECT statements are allowed")


def validate_tables(expression, schema):
    """Validate that all referenced tables exist."""
    referenced_tables = {table.name for table in expression.find_all(exp.Table)}
    unknown_tables = referenced_tables - schema.keys()
    if unknown_tables:
        raise ValueError(f"Unknown table(s): {', '.join(sorted(unknown_tables))}")


def validate_columns(expression, schema):
    """Validate that referenced columns exist in their tables."""
    table_aliases = {}
    for table in expression.find_all(exp.Table):
        table_name = table.name
        alias = table.alias_or_name
        table_aliases[alias] = table_name

    for column in expression.find_all(exp.Column):
        column_name = column.name
        table_name = column.table
        if table_name:
            actual_table = table_aliases.get(table_name, table_name)
            if actual_table not in schema:
                raise ValueError(f"Unknown table referenced by column: {table_name}")
            if column_name not in schema[actual_table]:
                raise ValueError(f"Unknown column: {table_name}.{column_name}")
        else:
            matching_tables = [t for t, cols in schema.items() if column_name in cols]
            if not matching_tables:
                raise ValueError(f"Unknown column: {column_name}")


def add_limit(expression, limit=DEFAULT_LIMIT):
    """Add a default LIMIT when the query does not already have one."""
    if expression.args.get("limit") is None:
        expression = expression.limit(limit)
    return expression


def validate_sql(sql_query: str):
    """Parse and validate SQL before execution."""
    if not sql_query or not sql_query.strip():
        raise ValueError("SQL query cannot be empty")

    try:
        expressions = sqlglot.parse(sql_query, read="postgres")
    except sqlglot.errors.ParseError as error:
        raise ValueError(f"Invalid SQL syntax: {error}") from error

    if len(expressions) != 1:
        raise ValueError("Only one SQL statement is allowed")

    expression = expressions[0]
    validate_statement_type(expression)
    schema = get_database_schema()
    validate_tables(expression, schema)
    validate_columns(expression, schema)
    expression = add_limit(expression)

    return expression.sql(dialect="postgres")


def validate_sql_node(state: AgentState):
    """Validate the generated SQL and store the validated query."""
    sql_query = state.get("sql_query", "")
    try:
        validated_sql = validate_sql(sql_query)
        return {"sql_query": validated_sql, "sql_error": ""}
    except ValueError as error:
        return {"sql_error": str(error), "retry_count": state.get("retry_count", 0) + 1}