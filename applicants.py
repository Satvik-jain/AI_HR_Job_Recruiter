import requests
from auth.zoho_auth import get_access_token
import json
import sys
import time

BASE_URL = "https://recruit.zoho.in/recruit/v2/"
JOB_OPENINGS_ENDPOINT = "JobOpenings"
APPLICATIONS_ENDPOINT = "Applications"
CANDIDATES_ENDPOINT = "Candidates"

# Fetch Job Openings
def fetch_job_openings():
    access_token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    response = requests.get(f"{BASE_URL}{JOB_OPENINGS_ENDPOINT}", headers=headers)
    
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print(f"Failed to fetch job openings: {response.text}")
        return None

# get in-progress job
def get_in_progress_job_openings(job_openings):
    jobs = []
    for job in job_openings:
        if job["Job_Opening_Status"] == "In-progress":
            jobs.append(job)
    return jobs

# Select Job Title
def select_job_title(job_openings):
    print("Available Job Titles:")
    for idx, job in enumerate(job_openings, 1):
        print(f"{idx}. {job['Posting_Title']} (Job ID: {job['id']})")
    choice = int(input("\nEnter the number corresponding to the job title: "))
    return job_openings[choice - 1] if 1 <= choice <= len(job_openings) else None


def get_all_applications():
    access_token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    all_applications = []
    page = 1
    per_page = 200

    while True:
        params = {"page": page, "per_page": per_page}
        response = requests.get(f"{BASE_URL}{APPLICATIONS_ENDPOINT}", headers=headers, params=params)

        if response.status_code == 200:
            data = response.json().get("data", [])
            if not data:
                break
            all_applications.extend(data)
            sys.stdout.write(f"\rFetched {len(data)} applications from page {page}               ")  
            sys.stdout.flush()
            page += 1
        elif response.status_code == 204:
            print(f"\nNo applications found on page {page}")
            break
        else:
            print(f"\nFailed to fetch applications on page {page}: {response}")
            break

    print()
    return all_applications


def filter_applications_by_job(job_title):
    applications = get_all_applications()
    print(f"Total applications: {len(applications)}")
    filtered_apps = [
        app for app in applications if app.get("Posting_Title", {}) == job_title
    ]
    return filtered_apps

def reset_timer():
    print("\nAPI limit reached. Waiting for reset...")
    for i in range(60, 0, -1):
        sys.stdout.write(f"\rRetrying in {i} seconds...")
        sys.stdout.flush()
        time.sleep(1)
    print("\nRetrying now.")

# Fetch detailed candidate information
def fetch_candidate_details(candidate_id):
    access_token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    url = f"{BASE_URL}{CANDIDATES_ENDPOINT}/{candidate_id}"

    while True:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json().get("data", {})
        elif response.status_code == 429:
            reset_timer()
        else:
            print(f"Failed to fetch candidate details for ID {candidate_id}: {response.text}")
            return None


# Get more details for each candidate in the applications
def fetch_detailed_applications(applications):
    detailed_apps = []
    for idx, app in enumerate(applications, 1):
        candidate_id = app.get("$Candidate_Id")
        if not candidate_id:
            continue

        print(f"\nFetching details for Candidate {idx}/{len(applications)} - ID: {candidate_id}")
        details = fetch_candidate_details(candidate_id)
        if details:
            # Merge basic app data with detailed candidate data
            app.update(details[0])
            detailed_apps.append(app)
        else:
            print(f"Skipping candidate ID {candidate_id} due to failure.")
    
    return detailed_apps


# Main Execution
def main_applicants():
    job_openings = fetch_job_openings()
    if not job_openings:
        return
    
    in_progress_openings = get_in_progress_job_openings(job_openings)
    if not in_progress_openings:
        return

    selected_job = select_job_title(in_progress_openings)
    if not selected_job:
        return

    job_title = selected_job['Posting_Title']
    job_description = selected_job.get("Job_Description", "")
    # print(job_description)
    print(f"\nFetching candidates for: {selected_job['Posting_Title']}...")
    applications = filter_applications_by_job(job_title)
    print(f"Found {len(applications)} applications for Job: {job_title}")

    print("\nFetching detailed information for each candidate...")
    detailed_applications = fetch_detailed_applications(applications)
    print(f"\nSuccessfully fetched detailed info for {len(detailed_applications)} candidates.")

    with open("detailed_candidates.json", "w") as file:
        json.dump(detailed_applications, file, indent=4)
        print("\nSaved detailed data to 'detailed_candidates.json'.")

    return job_description, detailed_applications

if __name__ == "__main__":
    main_applicants()