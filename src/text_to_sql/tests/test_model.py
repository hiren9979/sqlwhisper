import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)
key = os.getenv("GOOGLE_API_KEY")
print("Key loaded:", bool(key), "| ends with:", (key or "")[-4:])

client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=15000))

available = {m.name.replace("models/", "") for m in client.models.list()}
print("Models visible to this key (gemini-3*):",
      sorted(n for n in available if n.startswith("gemini-3")))

for m in ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
          "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]:
    try:
        r = client.models.generate_content(model=m, contents="Say hi")
        print("OK  ", m, "->", r.text[:40])
    except Exception as e:
        print("FAIL", m, "->", type(e).__name__, str(e)[:160])