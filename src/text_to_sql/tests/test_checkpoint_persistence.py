import os
import sys
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

from text_to_sql.config import DATABASE_URL
from text_to_sql.db.init_checkpoint import init_checkpoint_tables
from text_to_sql.graph.build_graph import build_graph

load_dotenv()

if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.sys.exit(1)

    print("=== Testing PostgreSQL Checkpoint Persistence ===\n")

    # Step 1: Initialize checkpoint tables
    print("Step 1: Initializing LangGraph checkpoint tables...")
    try:
        init_checkpoint_tables()
        print("✓ Checkpoint tables initialized successfully\n")
    except Exception as e:
        print(f"✗ Error initializing checkpoint tables: {e}")
        sys.exit(1)

    # Step 2: Build the graph with PostgreSQL checkpointer
    print("Step 2: Building graph with PostgreSQL checkpointer...")
    conn = None
    try:
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        graph = build_graph(checkpointer=checkpointer)
        print("✓ Graph built successfully with PostgreSQL checkpointer\n")

        # Step 3: Get user input for thread_id and query
        print("Step 3: Create a conversation thread")
        thread_id = input("Enter a thread ID (e.g., 'test-conversation-1'): ").strip()
        if not thread_id:
            print("ERROR: Thread ID is required")
            sys.exit(1)

        print(f"\nUsing thread_id: {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}

        # Step 4: First interaction
        print("\n" + "="*50)
        print("FIRST INTERACTION")
        print("="*50)
        print("Note: Enter a database-related query (e.g., 'how many active users')")
        query1 = input("Enter your first query: ").strip()
        if not query1:
            print("ERROR: Query is required")
            sys.exit(1)

        print(f"\nProcessing query: '{query1}'")
        try:
            initial_state = {
                "messages": [],
                "user_query": query1,
                "schema_context": "",
                "ambiguity_check": False,
                "ambiguity_type": "",
                "missing_slots": [],
                "clarification_question": "",
                "sql_query": "",
                "sql_result": [],
                "final_answer": "",
                "retry_count": 0,
                "sql_error": None,
            }
            print(f"Initial state: {initial_state}")
            result1 = graph.invoke(initial_state, config=config)
            print("\n✓ First interaction completed")
            print(f"Full result: {result1}")
            print(f"Final answer: {result1.get('final_answer', 'No answer generated')}")
            print(f"SQL query: {result1.get('sql_query', 'No SQL generated')}")
            print(f"SQL result: {result1.get('sql_result', 'No SQL result')}")
            print(f"SQL error: {result1.get('sql_error', 'No SQL error')}")
            print(f"Ambiguity check: {result1.get('ambiguity_check', 'No ambiguity check')}")
            
            # Check state was saved
            state = graph.get_state(config)
            print(f"✓ Checkpoint saved - current state has {len(state.values.get('messages', []))} messages")
        except Exception as e:
            print(f"✗ Error during first interaction: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # Step 5: Handle clarification if needed
        if result1.get("ambiguity_check"):
            print("\n" + "="*50)
            print("CLARIFICATION NEEDED")
            print("="*50)
            print(f"Clarification question: {result1.get('clarification_question')}")
            clarification_answer = input("Provide clarification answer: ").strip()
            if not clarification_answer:
                print("ERROR: Clarification answer is required")
                sys.exit(1)

            print(f"\nProcessing clarification: '{clarification_answer}'")
            try:
                from langgraph.types import Command
                result2 = graph.invoke(Command(resume=clarification_answer), config=config)
                print(f"\n✓ Clarification processed")
                print(f"Full result: {result2}")
                print(f"Final answer: {result2.get('final_answer', 'No answer generated')}")
                print(f"SQL query: {result2.get('sql_query', 'No SQL generated')}")
                print(f"SQL result: {result2.get('sql_result', 'No SQL result')}")
                print(f"SQL error: {result2.get('sql_error', 'No SQL error')}")
                
                # Check state was updated
                state = graph.get_state(config)
                print(f"✓ Checkpoint updated - current state has {len(state.values.get('messages', []))} messages")
            except Exception as e:
                print(f"✗ Error during clarification: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
            # Step 5: Second interaction (if no clarification needed)
            print("\n" + "="*50)
            print("SECOND INTERACTION (resuming from checkpoint)")
            print("="*50)
            query2 = input("Enter your second query (to test checkpoint resumption): ").strip()
            if not query2:
                print("ERROR: Query is required")
                sys.exit(1)

            print(f"\nProcessing query: '{query2}'")
            try:
                from langgraph.types import Command
                result2 = graph.invoke(Command(resume=query2), config=config)
                print(f"\n✓ Second interaction completed")
                print(f"Full result: {result2}")
                print(f"Final answer: {result2.get('final_answer', 'No answer generated')}")
                print(f"SQL query: {result2.get('sql_query', 'No SQL generated')}")
                print(f"SQL result: {result2.get('sql_result', 'No SQL result')}")
                print(f"SQL error: {result2.get('sql_error', 'No SQL error')}")
                
                # Check state was updated
                state = graph.get_state(config)
                print(f"✓ Checkpoint updated - current state has {len(state.values.get('messages', []))} messages")
            except Exception as e:
                print(f"✗ Error during second interaction: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
    finally:
        if conn:
            conn.close()
            print("✓ Database connection closed")

    # Step 6: Verify persistence
    print("\n" + "="*50)
    print("VERIFYING PERSISTENCE")
    print("="*50)
    print("The checkpoint data is now stored in PostgreSQL.")
    print("You can verify this by:")
    print("1. Stopping this application")
    print("2. Restarting and using the same thread_id")
    print("3. The conversation state should be preserved")
    
    print(f"\n✓ Test completed successfully for thread_id: {thread_id}")
    print("✓ Checkpoints are persisted in PostgreSQL database")
