from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key: {key[:20]}..." if key else "Key: None")

try:
    supabase = create_client(url, key)
    print("✅ Connection successful!")
    
    # Test query
    response = supabase.table("stores").select("*").limit(1).execute()
    print(f"✅ Query successful! Found {len(response.data)} stores")
    
except Exception as e:
    print(f"❌ Error: {e}")
