import json
import uuid

from langchain_core.output_parsers import StrOutputParser

from text_to_sql.ai.model_config import get_llm_model
from text_to_sql.db.user_facts import get_all_user_facts, upsert_user_fact
from text_to_sql.graph.state import AgentState


DETECT_FACT_UPDATE_PROMPT = """
You are a detection system for fact update requests.

Your job is to determine if the user's query is trying to update their personal facts.

Examples of fact update requests:
- "update my name as hiren.c"
- "remember me as John"
- "change my email to john@example.com"
- "set my location to Mumbai"
- "call me by a different name"

Examples of SQL queries (NOT fact updates):
- "show me revenue"
- "what is my name?"
- "list all customers"
- "total sales last month"

Rules:

1. Return true if the user is explicitly asking to update/change/set their personal information.
2. Return false for SQL queries or questions about data.
3. Return false for questions asking about their current facts (e.g., "what is my name?").

Return your response as a JSON object with this exact key:
is_fact_update (boolean)

User query:
{user_query}

Return JSON format:
{{"is_fact_update": true}}
"""


SELECT_FACTS_PROMPT = """
You are a fact selection system for a Text-to-SQL application.

Your job is to select ONLY the user facts that are relevant to the current query.
Do not dump all facts - be selective and efficient.

Available user facts:
{user_facts}

Current user query:
{user_query}

Rules:

1. Select facts ONLY if they are directly relevant to answering the query.
2. Examples of relevant facts:
   - User asks "what is my name?" → include name fact
   - User asks "show me revenue for my location" → include location fact
   - User asks "who am I?" → include name, role facts
3. Examples of irrelevant facts:
   - User asks "show all customers" → don't include any personal facts
   - User asks "total revenue" → don't include personal facts
4. Return empty list if no facts are relevant.
5. Return selected facts as a list of objects with fact_key and fact_value.

Return your response as a JSON object with this exact key:
relevant_facts (list of objects with fact_key and fact_value)

Return JSON format:
{{
  "relevant_facts": [
    {{"fact_key": "name", "fact_value": "Hiren"}},
    {{"fact_key": "location", "fact_value": "Gujarat"}}
  ]
}}
"""


EXTRACT_FACTS_PROMPT = """
You are a selective fact extraction system for a Text-to-SQL application.

Your job is to extract ONLY important personal facts about the user from their message.
These facts should be stored for long-term memory and retrieval.

Extract facts ONLY when the user explicitly shares personal information:
- name (e.g., "My name is Hiren", "remember me as hiren.c", "call me John")
- email (e.g., "My email is john@example.com")
- phone (e.g., "My phone number is 555-1234")
- location (e.g., "I live in New York")
- company (e.g., "I work at Acme Corp")
- role/title (e.g., "I am a manager")

DO NOT extract:
- Temporary context (e.g., "show me revenue for Gujarat")
- SQL query details
- Database-related information
- Conversational fillers

Rules:

1. Only extract facts that are explicitly stated by the user.
2. Do not infer or guess facts.
3. Use simple, lowercase fact keys (e.g., "name", "email", "phone").
4. Store the exact value as provided by the user.
5. If no facts are found, return an empty list.
6. If facts are found, return them as a list of objects with fact_key and fact_value.
7. Handle variations like "remember me as X", "call me X", "my name is X" as name facts.

Return your response as a JSON object with this exact key:
facts (list of objects with fact_key and fact_value)

User message:
{user_query}

Return JSON format:
{{
  "facts": [
    {{"fact_key": "name", "fact_value": "Hiren"}},
    {{"fact_key": "email", "fact_value": "john@example.com"}}
  ]
}}
"""


def detect_fact_update(user_query: str) -> bool:
    """Detect if the user query is trying to update personal facts."""
    parser = StrOutputParser()
    model = get_llm_model() | parser
    content = model.invoke(DETECT_FACT_UPDATE_PROMPT.format(user_query=user_query))
    
    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    try:
        parsed = json.loads(content)
        return parsed.get("is_fact_update", False)
    except json.JSONDecodeError:
        return False


def select_relevant_facts(user_query: str, user_facts: dict[str, str]) -> dict[str, str]:
    """Select only the facts relevant to the current query."""
    if not user_facts:
        return {}
    
    parser = StrOutputParser()
    model = get_llm_model() | parser
    
    facts_text = "\n".join(f"{key}: {value}" for key, value in user_facts.items())
    content = model.invoke(SELECT_FACTS_PROMPT.format(
        user_facts=facts_text,
        user_query=user_query
    ))
    
    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    try:
        parsed = json.loads(content)
        relevant_facts = parsed.get("relevant_facts", [])
        return {fact["fact_key"]: fact["fact_value"] for fact in relevant_facts}
    except (json.JSONDecodeError, KeyError):
        return {}


def retrieve_user_facts(state: AgentState):
    """Retrieve all stored facts for the user."""
    user_id_str = state.get("user_id", "")
    
    if not user_id_str:
        return {"user_facts": {}}
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return {"user_facts": {}}
    
    user_facts = get_all_user_facts(user_id)
    return {"user_facts": user_facts}


def select_relevant_facts_node(state: AgentState):
    """Select only the facts relevant to the current query."""
    user_query = state.get("user_query", "")
    user_facts = state.get("user_facts", {})
    
    if not user_query or not user_facts:
        return {"relevant_facts": {}}
    
    relevant_facts = select_relevant_facts(user_query, user_facts)
    return {"relevant_facts": relevant_facts}


def extract_user_facts(state: AgentState):
    """Extract and store user facts from the user query."""
    user_query = state.get("user_query", "")
    user_id_str = state.get("user_id", "")
    
    if not user_query.strip() or not user_id_str:
        return {}
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return {}
    
    parser = StrOutputParser()
    model = get_llm_model() | parser
    content = model.invoke(EXTRACT_FACTS_PROMPT.format(user_query=user_query))
    
    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    try:
        parsed = json.loads(content)
        facts = parsed.get("facts", [])
        
        # Store each fact in the database
        for fact in facts:
            fact_key = fact.get("fact_key", "").strip().lower()
            fact_value = fact.get("fact_value", "").strip()
            
            if fact_key and fact_value:
                upsert_user_fact(user_id, fact_key, fact_value)
        
        return {"extracted_facts": facts}
    except json.JSONDecodeError:
        return {"extracted_facts": []}
