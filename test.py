from supabase import create_client
from dotenv import load_dotenv
import os


load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

response = supabase.table("profiles").insert({
    "id": "6b65d074-477f-4f0a-84e8-b17bd9a36159",
    "full_name": "Yuval",
    "email": "yuval@ai.com",
    "preferences": {}
}).execute()

print(response)
