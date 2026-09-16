import os
from dotenv import load_dotenv
from text_to_sql.db.connection import test_connection, get_connection
from text_to_sql.db.schema_extractor import extract_schema
from text_to_sql.schema.metadata_loader import load_merged_schema
from text_to_sql.schema.glossary_loader import load_glossary
from text_to_sql.schema.embedding_documents import (
    build_schema_documents,
    build_glossary_documents,
    build_few_shot_documents,
    build_all_documents,
)
from text_to_sql.schema.embed_and_store import ingest_documents
from text_to_sql.schema.retriever import retrieve_documents
from text_to_sql.graph.state import AgentState
from text_to_sql.graph.nodes.check_ambiguity import check_ambiguity
from text_to_sql.graph.nodes.generate_sql import generate_sql
from text_to_sql.graph.nodes.validate_sql import validate_sql_node
from text_to_sql.graph.nodes.execute_sql import execute_sql
from text_to_sql.graph.nodes.summarize_answer import summarize_answer

# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        print("Please set it before running this test")
        exit(1)
    
    print(f"Testing database connection...")
    print(f"DATABASE_URL: {database_url[:20]}..." if len(database_url) > 20 else f"DATABASE_URL: {database_url}")
    
    try:
        # Test basic connection
        result = test_connection()
        print(f"✓ Connection successful! Query result: {result}")
        
        # Test connection object
        conn = get_connection()
        print(f"✓ Connection object created successfully")
        conn.close()
        
        # Test schema extractor
        print("\nTesting schema extraction...")
        schema = extract_schema()
        print(f"✓ Schema extracted successfully! Found {len(schema)} columns")
        if schema:
            print("Sample columns:")
            for row in schema[:5]:
                print(f"  - Table: {row[0]}, Column: {row[1]}, Type: {row[2]}")
        
        # Phase 4: Test metadata loader
        print("\n=== Phase 4: Testing metadata loader ===")
        merged_schema = load_merged_schema()
        print(f"✓ Merged schema loaded successfully! Found {len(merged_schema)} tables")
        
        for table_name, table_info in merged_schema.items():
            print(f"\n  Table: {table_name}")
            print(f"    Description: {table_info['description']}")
            print(f"    Columns: {len(table_info['columns'])}")
            for col in table_info['columns'][:3]:  # Show first 3 columns
                print(f"      - {col['name']} ({col['type']}): {col['description']}")
            if len(table_info['columns']) > 3:
                print(f"      ... and {len(table_info['columns']) - 3} more columns")
        
        # Phase 5: Test glossary loader
        print("\n=== Phase 5: Testing glossary loader ===")
        glossary = load_glossary()
        print(f"✓ Glossary loaded successfully! Found {len(glossary)} terms")
        
        for term, term_info in glossary.items():
            print(f"\n  Term: {term}")
            print(f"    Expression: {term_info['expression']}")
            print(f"    Description: {term_info['description']}")
        
        # Phase 6: Test embedding documents
        print("\n=== Phase 6: Testing embedding documents ===")
        
        schema_docs = build_schema_documents()
        print(f"✓ Schema documents built: {len(schema_docs)} documents")
        
        glossary_docs = build_glossary_documents()
        print(f"✓ Glossary documents built: {len(glossary_docs)} documents")
        
        few_shot_docs = build_few_shot_documents()
        print(f"✓ Few-shot documents built: {len(few_shot_docs)} documents")
        
        all_docs = build_all_documents()
        print(f"✓ All documents built: {len(all_docs)} total documents")
        
        # Show sample document
        if all_docs:
            print("\n  Sample document:")
            sample = all_docs[0]
            print(f"    Key: {sample['document_key']}")
            print(f"    Type: {sample['document_type']}")
            print(f"    Content preview: {sample['content'][:100]}...")
        
        # Phase 7: Test document ingestion with embeddings
        print("\n=== Phase 7: Testing document ingestion with embeddings ===")
        count = ingest_documents()
        print(f"✓ Successfully ingested {count} documents with embeddings into database")
        
        # Phase 8: Test document retrieval
        print("\n=== Phase 8: Testing document retrieval ===")
        test_question = "Show me all active products"
        print(f"Test question: '{test_question}'")
        
        retrieved_docs = retrieve_documents(test_question, top_k=3)
        print(f"✓ Retrieved {len(retrieved_docs)} relevant documents")
        
        for i, doc in enumerate(retrieved_docs, 1):
            print(f"\n  Document {i}:")
            print(f"    Key: {doc['document_key']}")
            print(f"    Type: {doc['document_type']}")
            print(f"    Distance: {doc['distance']:.4f}")
            print(f"    Content preview: {doc['content'][:150]}...")
        
        # Phase 9: Test graph state import
        print("\n=== Phase 9: Testing graph state import ===")
        print(f"✓ AgentState imported successfully")
        print(f"  State fields: {list(AgentState.__annotations__.keys())}")
        
        # Phase 10: Test ambiguity check with clarification loop
        print("\n=== Phase 10: Testing ambiguity check with clarification loop ===")
        
        # Simulate clarification loop
        current_query = "Show me sales"
        max_iterations = 3
        
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")
            print(f"Current query: '{current_query}'")
            
            state = {"user_query": current_query}
            result = check_ambiguity(state)
            
            print(f"  Is ambiguous: {result['ambiguity_check']}")
            
            if not result['ambiguity_check']:
                print(f"  ✓ Query is clear, no clarification needed")
                break
            
            print(f"  Ambiguity type: {result['ambiguity_type']}")
            print(f"  Missing slots: {result['missing_slots']}")
            print(f"  Clarification question: {result['clarification_question']}")
            
            # Get user input for clarification
            user_answer = input("  Your answer: ")
            current_query = f"{current_query}\nUser clarification: {user_answer}"
            
            if iteration == max_iterations - 1:
                print(f"  ⚠ Max iterations reached, proceeding with current query")
        
        print(f"\nFinal query: '{current_query}'")
        
        # Phase 11: Test SQL generation
        print("\n=== Phase 11: Testing SQL generation ===")
        
        # Retrieve schema context for the final query
        schema_context = retrieve_documents(current_query, top_k=5)
        print(f"✓ Retrieved {len(schema_context)} schema documents for SQL generation")
        
        # Generate SQL
        sql_state = {"user_query": current_query, "schema_context": schema_context}
        sql_result = generate_sql(sql_state)
        
        print(f"✓ Generated SQL query:")
        print(f"  {sql_result['sql_query']}")
        
        # Phase 12: Test SQL validation
        print("\n=== Phase 12: Testing SQL validation ===")
        
        # Validate the generated SQL
        validate_state = {"sql_query": sql_result['sql_query']}
        validated_result = validate_sql_node(validate_state)
        
        print(f"✓ SQL validated successfully:")
        print(f"  {validated_result['sql_query']}")
        
        # Phase 13: Test SQL execution with retry logic
        print("\n=== Phase 13: Testing SQL execution with retry logic ===")
        
        # Test 1: Execute correct SQL
        print("\nTest 1: Executing correct SQL")
        execute_state = {"sql_query": validated_result['sql_query'], "retry_count": 0}
        execution_result = execute_sql(execute_state)
        
        if execution_result['sql_error']:
            print(f"✗ Execution failed: {execution_result['sql_error']}")
            print(f"  Retry count: {execution_result.get('retry_count', 0)}")
        else:
            print(f"✓ Execution successful")
            print(f"  Rows returned: {len(execution_result['sql_result'])}")
            if execution_result['sql_result']:
                print(f"  Sample row: {execution_result['sql_result'][0]}")
        
        # Test 2: Execute wrong SQL to test retry
        print("\nTest 2: Executing wrong SQL (to test retry)")
        wrong_sql = "SELECT * FROM nonexistent_table"
        wrong_state = {"sql_query": wrong_sql, "retry_count": 0}
        wrong_result = execute_sql(wrong_state)
        
        if wrong_result['sql_error']:
            print(f"✗ Execution failed as expected: {wrong_result['sql_error']}")
            print(f"  Retry count: {wrong_result.get('retry_count', 0)}")
        else:
            print(f"✓ Unexpected success")
        
        # Phase 14: Test answer summarization
        print("\n=== Phase 14: Testing answer summarization ===")
        
        if execution_result['sql_result']:
            summarize_state = {
                "user_query": current_query,
                "sql_result": execution_result['sql_result']
            }
            answer_result = summarize_answer(summarize_state)
            
            print(f"✓ Final answer generated:")
            print(f"  {answer_result['final_answer']}")
        else:
            print(f"⚠ Skipping summarization - no SQL results available")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        exit(1)