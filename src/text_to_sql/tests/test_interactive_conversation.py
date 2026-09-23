"""Interactive CLI for testing the text-to-SQL LangGraph with PostgreSQL persistence.

While a request runs, the script prints:
  * when every graph node starts and how long it took,
  * a heartbeat every few seconds for nodes that are still running,
  * a "run #N" marker when a node executes more than once (retry loops),
  * which nodes were running if you cancel with Ctrl+C.

That makes it easy to see which step is slow or stuck.
"""

import sys
import threading
import time
import traceback
import uuid
from collections import Counter
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import psycopg
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from psycopg.rows import dict_row

load_dotenv()

from text_to_sql.config import DATABASE_URL  # noqa: E402
from text_to_sql.db.conversations import (  # noqa: E402
    add_message,
    create_conversation,
    get_conversation,
    get_recent_messages,
)
from text_to_sql.graph.build_graph import build_graph  # noqa: E402

HEARTBEAT_SECONDS = 10
RECURSION_LIMIT = 25
MAX_DISPLAY_CHARS = 500


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def truncate(value: Any, limit: int = MAX_DISPLAY_CHARS) -> str:
    """Return str(value) shortened to `limit` characters."""
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... (+{len(text) - limit} chars)"


@contextmanager
def step(label: str) -> Iterator[None]:
    """Log the start, duration and outcome of a blocking step."""
    print(f"⏳ {label}...", flush=True)
    start = time.perf_counter()
    try:
        yield
    except Exception:
        print(f"✗ {label} failed ({time.perf_counter() - start:.2f}s)", flush=True)
        raise
    print(f"✓ {label} ({time.perf_counter() - start:.2f}s)", flush=True)


# ---------------------------------------------------------------------------
# Graph run monitoring
# ---------------------------------------------------------------------------
class RunMonitor:
    """Tracks running nodes and prints a heartbeat while they execute."""

    def __init__(self) -> None:
        self._running: dict[str, tuple[str, float]] = {}
        self._run_counts: Counter = Counter()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._heartbeat, daemon=True)

    def __enter__(self) -> "RunMonitor":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._stop.set()
        if exc_type is KeyboardInterrupt:
            self._print_running("⛔ Cancelled while running")
        return False

    def node_started(self, task_id: str, name: str) -> None:
        with self._lock:
            self._run_counts[name] += 1
            run_number = self._run_counts[name]
            self._running[task_id] = (name, time.perf_counter())

        suffix = f" (run #{run_number})" if run_number > 1 else ""
        print(f"\n⏳ NODE STARTED: {name}{suffix}", flush=True)

    def node_finished(self, task_id: str, name: str) -> float:
        with self._lock:
            _, started = self._running.pop(task_id, (name, time.perf_counter()))
        elapsed = time.perf_counter() - started
        print(f"✓ NODE COMPLETED: {name} ({elapsed:.2f}s)", flush=True)
        return elapsed

    def _print_running(self, prefix: str) -> None:
        with self._lock:
            snapshot = list(self._running.values())
        now = time.perf_counter()
        for name, started in snapshot:
            print(f"{prefix}: {name} ({now - started:.0f}s)", flush=True)

    def _heartbeat(self) -> None:
        while not self._stop.wait(HEARTBEAT_SECONDS):
            self._print_running("   ⏱  still running")


def to_updates(result: Any) -> dict[str, Any]:
    """Normalise a debug `task_result` payload into a dict of state updates."""
    if isinstance(result, dict):
        return result
    try:
        return dict(result or [])
    except (TypeError, ValueError):
        return {}


def run_graph(graph, graph_input: Any, config: dict) -> None:
    """Stream one graph execution, logging every node and its duration."""
    print(f"\n{'-' * 60}\n🚀 GRAPH EXECUTION STARTED\n{'-' * 60}")
    started = time.perf_counter()

    try:
        with RunMonitor() as monitor:
            for event in graph.stream(graph_input, config=config, stream_mode="debug"):
                event_type = event.get("type")
                payload = event.get("payload", {})
                task_id = payload.get("id", "")
                name = payload.get("name", "unknown")

                if event_type == "task":
                    monitor.node_started(task_id, name)
                    continue

                if event_type != "task_result":
                    continue

                monitor.node_finished(task_id, name)
                updates = to_updates(payload.get("result"))

                if payload.get("error"):
                    print(f"   ✗ error: {truncate(payload['error'])}", flush=True)
                if payload.get("interrupts"):
                    print("   ⏸  waiting for user input", flush=True)
                if updates:
                    print(f"   updated: {', '.join(updates)}", flush=True)
                if updates.get("sql_error"):
                    print(f"   ⚠ sql_error: {truncate(updates['sql_error'])}", flush=True)
    except Exception:
        print(f"\n✗ GRAPH FAILED after {time.perf_counter() - started:.2f}s", flush=True)
        raise

    print(f"\n{'-' * 60}")
    print(f"✓ GRAPH EXECUTION COMPLETED ({time.perf_counter() - started:.2f}s)")
    print("-" * 60)


# ---------------------------------------------------------------------------
# Graph / conversation setup
# ---------------------------------------------------------------------------
def initialize_graph():
    """Connect to PostgreSQL, set up the checkpointer and build the graph."""
    print_section("Initializing Graph with PostgreSQL Checkpointer")

    with step("Connecting to PostgreSQL"):
        # PostgresSaver requires autocommit=True and dict_row when given a connection.
        conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)

    try:
        with step("Initializing checkpointer"):
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()

        with step("Building LangGraph"):
            graph = build_graph(checkpointer=checkpointer)
    except Exception:
        conn.close()
        raise

    return graph, conn


def parse_uuid(raw: str, label: str) -> Optional[uuid.UUID]:
    """Parse a UUID string, printing an error and returning None if invalid."""
    try:
        return uuid.UUID(raw)
    except ValueError:
        print(f"✗ Invalid {label} format (must be UUID)")
        return None


def prompt_conversation() -> Optional[uuid.UUID]:
    """Ask for a user and thread ID, then create or resume a conversation.

    Returns the conversation ID, or None if the input was invalid.
    """
    print_section("Conversation Setup")

    raw_user_id = input("Enter your user ID (or press Enter to generate one): ").strip()
    if raw_user_id:
        user_id = parse_uuid(raw_user_id, "user ID")
        if user_id is None:
            return None
    else:
        user_id = uuid.uuid4()
        print(f"Generated new user ID: {user_id}")

    raw_thread_id = input(
        "Enter thread ID to resume (or press Enter for a new conversation): "
    ).strip()

    if raw_thread_id:
        thread_id = parse_uuid(raw_thread_id, "thread ID")
        if thread_id is None:
            return None

        with step("Looking up conversation"):
            existing = get_conversation(thread_id)

        if existing:
            print(f"✓ Resuming existing conversation: {thread_id}")
            return thread_id

        print("✗ Conversation not found, creating a new one")

    conversation_id = uuid.uuid4()
    with step("Creating conversation"):
        create_conversation(
            user_id,
            title="Interactive Test",
            conversation_id=conversation_id,
        )
    print(f"✓ Created new conversation: {conversation_id}")
    return conversation_id


def build_config(conversation_id: uuid.UUID) -> dict:
    """Build the LangGraph run config for a conversation."""
    return {
        "configurable": {"thread_id": str(conversation_id)},
        "recursion_limit": RECURSION_LIMIT,
    }


def get_initial_state(
    user_query: str, conversation_context: list[dict[str, str]]
) -> dict[str, Any]:
    """Return the initial graph state for a new user query."""
    return {
        "messages": [],
        "conversation_context": conversation_context,
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


# ---------------------------------------------------------------------------
# Request handling
# ---------------------------------------------------------------------------
def get_pending_interrupts(state) -> list:
    """Return interrupts the graph is currently waiting on."""
    return [i for task in state.tasks for i in task.interrupts]


def print_outcome(state) -> None:
    """Print the clarification request or the final result."""
    interrupts = get_pending_interrupts(state)
    if interrupts:
        print("\n❓ Clarification needed:")
        for interrupt in interrupts:
            print(f"   {interrupt.value}")
        print("\nPlease provide the missing information to continue.")
        return

    values = state.values
    fields = [
        ("Final Answer", "final_answer"),
        ("SQL Query", "sql_query"),
        ("SQL Result", "sql_result"),
        ("SQL Error", "sql_error"),
        ("Ambiguity Check", "ambiguity_check"),
    ]

    print("\n📊 Results:")
    for label, key in fields:
        print(f"   {label}: {truncate(values.get(key))}")
    print(f"   Messages persisted: {len(values.get('messages', []))}")


def process_message(
    graph, config: dict, conversation_id: uuid.UUID, user_input: str
) -> None:
    """Run the graph for one user message, resuming if it is awaiting an answer."""
    with step("Loading checkpoint"):
        state = graph.get_state(config)

    conversation_context = get_recent_messages(conversation_id)
    add_message(conversation_id, "user", user_input)

    if get_pending_interrupts(state):
        print("🔄 Resuming with your clarification...", flush=True)
        graph_input: Any = Command(resume=user_input)
    else:
        print("🚀 Starting new graph execution...", flush=True)
        graph_input = get_initial_state(user_input, conversation_context)

    run_graph(graph, graph_input, config)

    with step("Verifying checkpoint"):
        state = graph.get_state(config)

    pending_interrupts = get_pending_interrupts(state)
    if pending_interrupts:
        add_message(conversation_id, "assistant", str(pending_interrupts[0].value))
    else:
        answer = state.values.get("final_answer")
        if answer:
            add_message(conversation_id, "assistant", str(answer))

    print_outcome(state)


def run_interactive_session() -> int:
    """Run the interactive conversation loop. Returns a process exit code."""
    print_section("Interactive Text-to-SQL Conversation Test")
    print("Conversation state is persisted in PostgreSQL.")
    print("Commands: 'exit' to quit, 'clear' for a new conversation.")
    print("Press Ctrl+C during a request to cancel it and see which node was running.")

    graph, conn = initialize_graph()

    try:
        conversation_id = prompt_conversation()
        if conversation_id is None:
            print("✗ Failed to setup conversation")
            return 1

        config = build_config(conversation_id)
        print_section("Starting Conversation")

        while True:
            try:
                user_input = input("\n💬 You: ").strip()
            except EOFError:
                break

            command = user_input.lower()

            if command == "exit":
                break

            if command == "clear":
                new_id = prompt_conversation()
                if new_id is None:
                    print("✗ Failed to setup new conversation, keeping current one")
                    continue
                conversation_id = new_id
                config = build_config(conversation_id)
                print("✓ New conversation started")
                continue

            if not user_input:
                print("⚠️ Please enter a message")
                continue

            try:
                process_message(graph, config, conversation_id, user_input)
            except KeyboardInterrupt:
                print("\n⛔ Request cancelled. You can ask another question.")
            except Exception as exc:
                print(f"\n✗ Error processing request: {exc}", flush=True)
                traceback.print_exc()

        print_section("Ending Conversation")
        print("✓ Conversation ended successfully")
        print(f"Thread ID: {conversation_id}")
        return 0

    finally:
        conn.close()
        print("✓ PostgreSQL connection closed")


def main() -> int:
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        return 1

    try:
        return run_interactive_session()
    except KeyboardInterrupt:
        print_section("Session Interrupted")
        print("✓ Session ended by user")
        return 0
    except Exception as exc:
        print_section("Unexpected Error")
        print(f"✗ An unexpected error occurred: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
