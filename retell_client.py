from retell import Retell 
from dotenv import load_dotenv

load_dotenv()

import os
RETELL_API_KEY = os.getenv("RETELL_API_KEY")

retell_client = Retell(
  api_key = RETELL_API_KEY
)

try:
  response = retell_client.call.create_phone_call(
    from_number="+16018007298",
    to_number="+919058319045"
  )
  print(f"Call initiated: {response}")
except Exception as e:
  print(f"Error making call: {e}")