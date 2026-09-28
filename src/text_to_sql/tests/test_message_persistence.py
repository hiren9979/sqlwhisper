"""Test Phase 18 - Message Persistence and Conversation Context.

This test verifies:
1. Messages are stored as plain text (not raw LLM objects)
2. Duplicate messages are prevented
3. Conversation context is loaded correctly for follow-up questions
4. Follow-up context works: Q1 → Gujarat, Q2 → Maharashtra
"""

import uuid
from text_to_sql.db.conversations import (
    add_message,
    create_conversation,
    get_recent_messages,
    extract_plain_text,
)


def test_extract_plain_text():
    """Test the extract_plain_text function handles various input formats."""
    print("Testing extract_plain_text function...")
    
    # Test 1: Plain string
    result = extract_plain_text("Show revenue for Gujarat")
    assert result == "Show revenue for Gujarat", f"Expected plain string, got: {result}"
    print("✓ Plain string handled correctly")
    
    # Test 2: Structured LLM object
    structured = [{"type": "text", "text": "Revenue was ₹20M", "extras": {"signature": "abc123"}}]
    result = extract_plain_text(structured)
    assert result == "Revenue was ₹20M", f"Expected extracted text, got: {result}"
    assert "signature" not in result, "Signature should not be in extracted text"
    print("✓ Structured LLM object handled correctly")
    
    # Test 3: Other object types
    result = extract_plain_text(12345)
    assert result == "12345", f"Expected string conversion, got: {result}"
    print("✓ Other object types handled correctly")
    
    print("✓ All extract_plain_text tests passed\n")


def test_duplicate_prevention():
    """Test that duplicate messages are not stored."""
    print("Testing duplicate message prevention...")
    
    user_id = uuid.uuid4()
    conversation_id = create_conversation(user_id, title="Duplicate Test")
    
    # Add the same message twice
    add_message(conversation_id, "user", "Show revenue for Gujarat")
    add_message(conversation_id, "user", "Show revenue for Gujarat")
    
    # Should only have one message
    messages = get_recent_messages(conversation_id)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    assert messages[0]["content"] == "Show revenue for Gujarat"
    print("✓ Duplicate messages prevented")
    
    # Add a different message
    add_message(conversation_id, "user", "What about Maharashtra?")
    messages = get_recent_messages(conversation_id)
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
    print("✓ Different messages allowed")
    
    print("✓ All duplicate prevention tests passed\n")


def test_conversation_context_flow():
    """Test the conversation context flow for follow-up questions."""
    print("Testing conversation context flow...")
    
    user_id = uuid.uuid4()
    conversation_id = create_conversation(user_id, title="Context Test")
    
    # Simulate conversation flow:
    # Q1: Show revenue for Gujarat
    # A1: Revenue was ₹20M
    # Q2: What about Maharashtra?
    # A2: Revenue was ₹15M
    
    add_message(conversation_id, "user", "Show revenue for Gujarat")
    add_message(conversation_id, "assistant", "Revenue was ₹20M")
    add_message(conversation_id, "user", "What about Maharashtra?")
    add_message(conversation_id, "assistant", "Revenue was ₹15M")
    
    # Load recent messages
    messages = get_recent_messages(conversation_id)
    
    # Verify we have 4 messages in chronological order
    assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"
    
    # Verify chronological order
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Show revenue for Gujarat"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Revenue was ₹20M"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "What about Maharashtra?"
    assert messages[3]["role"] == "assistant"
    assert messages[3]["content"] == "Revenue was ₹15M"
    
    print("✓ Conversation context loaded in correct order")
    print("✓ All messages stored as plain text")
    
    # Verify context structure for ambiguity check
    context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
    print(f"Conversation context:\n{context_str}")
    
    print("✓ All conversation context flow tests passed\n")


def test_structured_content_storage():
    """Test that structured LLM content is stored as plain text."""
    print("Testing structured content storage...")
    
    user_id = uuid.uuid4()
    conversation_id = create_conversation(user_id, title="Structured Content Test")
    
    # Store structured LLM response
    structured_response = [
        {"type": "text", "text": "Revenue was ₹20M", "extras": {"signature": "abc123"}}
    ]
    add_message(conversation_id, "assistant", structured_response)
    
    # Verify it's stored as plain text
    messages = get_recent_messages(conversation_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "Revenue was ₹20M"
    assert "signature" not in messages[0]["content"]
    assert "extras" not in messages[0]["content"]
    
    print("✓ Structured content stored as plain text")
    print("✓ Metadata/signatures not stored")
    print("✓ All structured content storage tests passed\n")


def test_clarification_exchange():
    """Test that clarification exchanges are stored as separate clean rows."""
    print("Testing clarification exchange storage...")
    
    user_id = uuid.uuid4()
    conversation_id = create_conversation(user_id, title="Clarification Test")
    
    # Simulate clarification flow:
    # Q: Show revenue
    # A: Which region?
    # Q: Gujarat
    # A: Revenue was ₹20M
    
    add_message(conversation_id, "user", "Show revenue")
    add_message(conversation_id, "assistant", "Which region?")
    add_message(conversation_id, "user", "Gujarat")
    add_message(conversation_id, "assistant", "Revenue was ₹20M")
    
    messages = get_recent_messages(conversation_id)
    
    # Verify all 4 messages are stored separately
    assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"
    
    # Verify each is a clean user/assistant row
    assert messages[0] == {"role": "user", "content": "Show revenue"}
    assert messages[1] == {"role": "assistant", "content": "Which region?"}
    assert messages[2] == {"role": "user", "content": "Gujarat"}
    assert messages[3] == {"role": "assistant", "content": "Revenue was ₹20M"}
    
    print("✓ Clarification exchange stored as separate clean rows")
    print("✓ All clarification exchange tests passed\n")


def run_all_tests():
    """Run all message persistence tests."""
    print("=" * 60)
    print("PHASE 18 - MESSAGE PERSISTENCE TESTS")
    print("=" * 60 + "\n")
    
    try:
        test_extract_plain_text()
        test_duplicate_prevention()
        test_conversation_context_flow()
        test_structured_content_storage()
        test_clarification_exchange()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())
