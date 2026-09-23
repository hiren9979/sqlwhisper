import os
import sys
import uuid

import psycopg
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from text_to_sql.config import DATABASE_URL
from text_to_sql.db.conversations import create_conversation, get_conversation
from text_to_sql.graph.build_graph import build_graph

load_dotenv()


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result):
    """Print formatted result information."""
    print("\n📊 Results:")
    print(f"   Final Answer: {result.get('final_answer', 'No answer generated')}")
    print(f"   SQL Query: {result.get('sql_query', 'No SQL generated')}")
    print(f"   SQL Result: {result.get('sql_result', 'No SQL result')}")
    print(f"   SQL Error: {result.get('sql_error', 'No SQL error')}")
    print(
        f"   Ambiguity Check: "
        f"{result.get('ambiguity_check', 'No ambiguity check')}"
    )


def stream_graph(graph, input_data, config):
    """Stream graph execution and print AI output in real time."""
    final_result = {}

    for chunk in graph.stream(
        input_data,
        config=config,
        stream_mode="updates",
    ):
        if not isinstance(chunk, dict):
            continue

        for node_name, node_output in chunk.items():
            if not isinstance(node_output, dict):
                continue

            final_result.update(node_output)

            # Stream final answer as soon as the summarizer produces it.
            final_answer = node_output.get("final_answer")
            if final_answer:
                print("\n🤖 AI: ", end="", flush=True)
                print(final_answer, flush=True)

            # Show clarification immediately.
            clarification = node_output.get("clarification_question")
            if (
                clarification
                and node_output.get("ambiguity_check")
            ):
                print("\n❓ Clarification: ", end="", flush=True)
                print(clarification, flush=True)

    return final_result


def initialize_graph():
    """Initialize the graph with PostgreSQL checkpointer."""
    print_section("Initializing Graph with PostgreSQL Checkpointer")

    conn = None

    try:
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()

        graph = build_graph(checkpointer=checkpointer)

        print("✓ Graph initialized successfully with PostgreSQL checkpointer")
        return graph, checkpointer

    except (ValueError, RuntimeError, ConnectionError) as e:
        if conn:
            conn.close()

        print(f"✗ Error initializing graph: {e}")
        sys.exit(1)


def create_or_resume_conversation():
    """Create a new conversation or resume an existing one."""
    print_section("Conversation Setup")

    user_id = input(
        "Enter your user ID (or press Enter for default): "
    ).strip()

    if not user_id:
        user_id = str(uuid.uuid4())
        print(f"Generated new user ID: {user_id}")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        print("✗ Invalid user ID format (must be UUID)")
        return None, None

    thread_id = input(
        "Enter thread ID to resume "
        "(or press Enter for new conversation): "
    ).strip()

    if thread_id:
        try:
            conversation_id = uuid.UUID(thread_id)
            conversation = get_conversation(conversation_id)

            if conversation:
                print(
                    f"✓ Resuming existing conversation: "
                    f"{thread_id}"
                )
                return user_uuid, conversation_id

            print("✗ Conversation not found, creating new one")

            conversation_id = uuid.uuid4()
            create_conversation(
                user_uuid,
                title="Interactive Test",
                conversation_id=conversation_id,
            )

            print(f"✓ Created new conversation: {conversation_id}")
            return user_uuid, conversation_id

        except ValueError:
            print("✗ Invalid thread ID format (must be UUID)")
            return None, None

    conversation_id = uuid.uuid4()

    create_conversation(
        user_uuid,
        title="Interactive Test",
        conversation_id=conversation_id,
    )

    print(f"✓ Created new conversation: {conversation_id}")
    return user_uuid, conversation_id


def get_initial_state(user_query):
    """Get the initial state for the graph."""
    return {
        "messages": [],
        "user_query": user_query,
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


def run_interactive_session():
    """Run an interactive streaming conversation session."""
    print_section("Interactive Text-to-SQL Conversation Test")
    print("This test allows you to interact with the system in real-time")
    print("You can ask database queries and respond to clarification questions")
    print("The conversation state is persisted in PostgreSQL")

    graph, checkpointer = initialize_graph()

    user_uuid, conversation_id = create_or_resume_conversation()

    if not user_uuid or not conversation_id:
        print("✗ Failed to setup conversation")
        checkpointer.conn.close()
        sys.exit(1)

    config = {
        "configurable": {
            "thread_id": str(conversation_id)
        }
    }

    print_section("Starting Conversation")
    print("Type 'exit' to quit the conversation")
    print("Type 'clear' to start a new conversation")

    try:
        while True:
            user_input = input("\n💬 You: ").strip()

            if user_input.lower() == "exit":
                print_section("Ending Conversation")
                print("✓ Conversation ended successfully")
                print(f"Thread ID: {conversation_id}")
                print(
                    "You can resume this conversation by using "
                    "the same thread ID"
                )
                break

            if user_input.lower() == "clear":
                print_section("Starting New Conversation")

                user_uuid, conversation_id = create_or_resume_conversation()

                if not user_uuid or not conversation_id:
                    print("✗ Failed to setup new conversation")
                    continue

                config = {
                    "configurable": {
                        "thread_id": str(conversation_id)
                    }
                }

                print("✓ New conversation started")
                continue

            if not user_input:
                print("⚠️  Please enter a message")
                continue

            try:
                # Check the latest PostgreSQL checkpoint.
                state = graph.get_state(config)

                if state.next:
                    print("🔄 Resuming from previous state...")

                    result = stream_graph(
                        graph,
                        Command(resume=user_input),
                        config,
                    )
                else:
                    print("🚀 Processing your query...")

                    initial_state = get_initial_state(user_input)

                    result = stream_graph(
                        graph,
                        initial_state,
                        config,
                    )

                # If clarification is required, wait for the
                # user's next input and resume the same checkpoint.
                if result.get("ambiguity_check"):
                    print(
                        "\nPlease provide the missing information "
                        "to continue."
                    )
                    continue

                # Print non-streamed result details.
                print_result(result)

                # Verify that the latest checkpoint was persisted.
                current_state = graph.get_state(config)

                message_count = len(
                    current_state.values.get("messages", [])
                )

                print(
                    f"\n💾 Checkpoint saved - "
                    f"State has {message_count} messages"
                )

            except (ValueError, KeyError, RuntimeError) as e:
                print(f"✗ Error processing request: {e}")

                import traceback

                traceback.print_exc()
                continue

    finally:
        if checkpointer:
            checkpointer.conn.close()
            print("✓ Checkpointer connection closed")


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print(
            "ERROR: DATABASE_URL environment variable is not set"
        )
        sys.exit(1)

    try:
        run_interactive_session()

    except KeyboardInterrupt:
        print_section("Session Interrupted")
        print("✓ Session ended by user")

    except (ValueError, RuntimeError, ConnectionError) as e:
        print_section("Unexpected Error")
        print(f"✗ An unexpected error occurred: {e}")

        import traceback

        traceback.print_exc()
        sys.exit(1)