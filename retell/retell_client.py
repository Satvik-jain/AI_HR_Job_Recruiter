import csv
import os
import time
from retell import AsyncRetell
import json
from dotenv import load_dotenv
import asyncio

load_dotenv()

# r = AsyncRetell(api_key=os.getenv('RETELL_API_KEY'))
# re = r.call.retrieve


def initialize_retell():
    return AsyncRetell(api_key=os.getenv('RETELL_API_KEY'))

async def call_candidate(retell_client, phone_number, first_name):
    RETELL_RECRUIT_PHONE = os.getenv("RETELL_RECRUIT_PHONE")
    try:
        response = await retell_client.call.create_phone_call(
            to_number=phone_number,
            from_number=RETELL_RECRUIT_PHONE,
            retell_llm_dynamic_variables={"first_name": first_name}
        )
        return response
    except Exception as e:
        print(f"Error calling {phone_number}: {e}")
        return {"error": str(e)}

async def wait_for_call_completion(retell_client, call_id, max_retries=20, delay=10):
    """Polls the API until the call is completed or failed."""
    for _ in range(max_retries):
        try:
            status_response = await retell_client.call.retrieve(call_id)
            status = status_response.call_status
            # print(status_response)
            print(f"Call Status: {status}")

            if status in ["ended", "error"]:
                print("Call ended, waiting for 10 seconds before checking analysis...")
                await asyncio.sleep(10)
                return status_response
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"Error polling call status: {e}")
            return None
    print("Max retries reached. Call did not complete.")
    return None

async def extract_post_call_analysis(response):
    try:
        # Debug the full response structure
        # print(response.model_dump())  # Pydantic 2.0 compliant
        response = response.model_dump()
        print(response)
        # Extract necessary fields if available
        return {
            "Has Laptop": response.get('call_analysis').get("custom_analysis_data").get('has_laptop', 'N/A'),
            "Expected Salary": response.get('call_analysis').get("custom_analysis_data").get('expected_salary', 'N/A'),
            "Notice Period": response.get('call_analysis').get("custom_analysis_data").get('notice_period', 'N/A'),
            "Working Hours": response.get('call_analysis').get("custom_analysis_data").get('working_hours', 'N/A'),
            "Recording Link" : response.get('recording_url', 'N/A')
        }
    except Exception as e:
        print(f"Error extracting post-call data: {e}")
        return {
            "Has Laptop": "Error",
            "Expected Salary": "Error",
            "Notice Period": "Error",
            "Working Hours": "Error",
            "Recording Link" : response.get('recording_url', 'Error')
        }

def save_to_csv(file_path, data):
    headers = [
        "Full Name", "Phone Number", "Email", "Position Applied","Response", 
        "Has Laptop", "Expected Salary", "Notice Period", "Working Hours", "Recording Link"
    ]
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Check if file exists
    file_exists = os.path.isfile(file_path)
    
    # Open in append mode
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        
        # Write header only if file is new
        if not file_exists:
            writer.writeheader()
        
        # Write data
        writer.writerows(data)


async def main():
    with open(r'json/demo_candidates.json', 'r') as file:
        selected_candidates = json.load(file)

    retell_client = initialize_retell()
    responses = []

    for candidate in selected_candidates:
        phone_number = candidate.get('phone', 'N/A')
        full_name = candidate.get('full_name', 'N/A')
        first_name = candidate.get('first_name', 'N/A')
        email = candidate.get('email', 'N/A')
        position_applied = candidate.get('position_applied', 'N/A')

        print(f"Initiating call to {full_name} at {phone_number}...")
        response = await call_candidate(retell_client, phone_number, first_name)

        if isinstance(response, dict) and "error" in response:
            post_call_data = {
                "Has Laptop": "Error",
                "Expected Salary": "Error",
                "Notice Period": "Error",
                "Working Hours": "Error",
                "Recording Link": "Error"
            }
            response_text = response["error"]
        else:
            # Wait for call to complete
            completed_response = await wait_for_call_completion(retell_client, response.call_id)
            if completed_response:
                post_call_data = await extract_post_call_analysis(completed_response)
                response_text = completed_response.model_dump().get("transcript") or "No transcript available"
            else:
                post_call_data = {
                    "Has Laptop": "Error",
                    "Expected Salary": "Error",
                    "Notice Period": "Error",
                    "Working Hours": "Error",
                    "Recording Link": "Error"
                }
                response_text = "Call did not complete"

        # Save response
        responses.append({
            "Full Name": full_name,
            "Phone Number": f"'{phone_number}",
            "Email": email,
            "Position Applied":position_applied, 
            "Response": response_text,
            **post_call_data
        })

    # Save to CSV
    csv_file_path = rf'csv/candidate_responses.csv'
    save_to_csv(csv_file_path, responses)
    print(f"Responses saved to {csv_file_path}")

if __name__ == "__main__":
    asyncio.run(main())
