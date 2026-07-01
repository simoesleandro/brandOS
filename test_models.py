import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
try:
    client = genai.Client(api_key=os.environ.get("BRANDOS_API_KEY"))
    
    # In the new SDK, it's typically client.models.list()
    # But let's check what's there
    for m in client.models.list():
        print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
