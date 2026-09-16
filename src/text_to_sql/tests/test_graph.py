import os
from dotenv import load_dotenv
from text_to_sql.graph.build_graph import build_graph

load_dotenv()

if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        exit(1)

    print("=== Testing LangGraph Workflow ===\n")

    # Build the graph
    graph = build_graph()
    print("✓ Graph built successfully")

    # Test case 1: Clear query
    print("\n--- Test Case 1: Clear Query ---")
    query1 = "Show me all active products"
    print(f"Query: '{query1}'")

    config = {"configurable": {"thread_id": "test-thread-1"}}
    initial_state = {"user_query": query1}

    try:
        result = graph.invoke(initial_state, config)
        print(f"✓ Final answer: {result.get('final_answer', 'No answer generated')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test case 2: Ambiguous query with clarification
    print("\n--- Test Case 2: Ambiguous Query with Clarification ---")
    query2 = "Show me sales"
    print(f"Query: '{query2}'")

    config = {"configurable": {"thread_id": "test-thread-2"}}
    initial_state = {"user_query": query2}

    try:
        result = graph.invoke(initial_state, config)
        
        # Debug output
        print(f"  Ambiguity check: {result.get('ambiguity_check')}")
        print(f"  Clarification question: {result.get('clarification_question')}")
        print(f"  SQL query: {result.get('sql_query')}")
        print(f"  SQL error: {result.get('sql_error')}")
        
        print(f"✓ Final answer: {result.get('final_answer', 'No answer generated')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n=== Graph Test Complete ===")
