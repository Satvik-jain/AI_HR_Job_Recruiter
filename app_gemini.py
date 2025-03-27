import os
import json
import time
import traceback
from applicants import main_applicants
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from system_prompt_frontend import system_prompt

def initialize_llm():
    return ChatGoogleGenerativeAI(
        temperature=0.1,
        model="gemini-2.0-flash",
        google_api_key=os.getenv('GOOGLE_API_KEY')
    )

def create_candidate_evaluation_prompt():
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", """
        Job Description:
        {job_description}

        Candidate Profile:
        {candidate_profile}

        Provide a comprehensive evaluation in strict JSON format.
        """)
    ])

def evaluate_candidates(job_description, detailed_applications):
    # Try to load previous progress
    try:
        with open(r'json\evaluation_progress.json', 'r') as f:
            progress = json.load(f)
        selected_candidates = progress.get('selected_candidates', [])
        rejected_candidates = progress.get('rejected_candidates', [])
        start_index = progress.get('last_processed_index', 0)
    except FileNotFoundError:
        selected_candidates = []
        rejected_candidates = []
        start_index = 0

    # Prepare LLM and chain
    llm = initialize_llm()
    prompt = create_candidate_evaluation_prompt()
    output_parser = JsonOutputParser()
    chain = prompt | llm | output_parser

    # Slice the detailed_applications to start from last processed index
    candidates_to_process = detailed_applications[start_index:]

    # Retry strategy parameters
    max_retries = 3
    base_delay = 5  # Base delay in seconds

    for index, candidate in enumerate(candidates_to_process, start=start_index):
        print(f"Evaluating Candidate {index+1}/{len(detailed_applications)}")

        # Convert candidate dict to a more readable profile string
        candidate_profile = f"""
        Name: {candidate.get('Full_Name', 'N/A')}
        Current Role: {candidate.get('Current_Job_Title', 'N/A')}
        Experience: {candidate.get('Experience_in_Years', 0)} years
        Skills: {candidate.get('Skill_Set', 'N/A')}
        Work Experience:
        {json.dumps(candidate.get('Experience_Details', []), indent=2)}
        Education: {json.dumps(candidate.get('Educational_Details', []), indent=2)}
        """

        # Retry mechanism
        for attempt in range(max_retries):
            try:
                # Invoke the chain
                evaluation = chain.invoke({
                    "job_description": job_description,
                    "candidate_profile": candidate_profile
                })

                # Prepare candidate result
                candidate_result = {
                    "phone": candidate.get('Phone', 'N/A'),
                    "email": candidate.get('Email', 'N/A'),
                    "full_name": candidate.get('Full_Name', 'N/A'),
                    "first_name": candidate.get('First_Name', 'N/A'),
                    "last_name": candidate.get('Last_Name', 'N/A'),
                    "score": evaluation.get('score', 0),
                    "recommendation": evaluation.get('recommendation', 'Reject'),
                    "reasoning": evaluation.get('reasoning', 'No detailed reasoning'),
                    "strong_points": evaluation.get('strong_points', []),
                    "areas_of_concern": evaluation.get('areas_of_concern', [])
                }
                print(f"Result: \n{candidate_result}")
                # Categorize candidates
                if evaluation.get('recommendation') == 'Shortlist':
                    selected_candidates.append(candidate_result)
                else:
                    rejected_candidates.append(candidate_result)

                # Save progress after each successful evaluation
                progress = {
                    'selected_candidates': selected_candidates,
                    'rejected_candidates': rejected_candidates,
                    'last_processed_index': index + 1
                }
                with open(r'json\evaluation_progress.json', 'w') as f:
                    json.dump(progress, f, indent=4)

                # Break retry loop if successful
                break

            except Exception as e:
                print(f"Error processing candidate {candidate.get('Full_Name')}: {e}")
                print(traceback.format_exc())

                # Exponential backoff for retries
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"Failed to process {candidate.get('Full_Name')} after {max_retries} attempts.")
                    # Optionally, log failed candidates to a separate file
                    with open(r'json\failed_candidates.json', 'a') as f:
                        json.dump({
                            'full_name': candidate.get('Full_Name'),
                            'error': str(e)
                        }, f)
                        f.write('\n')

    # Save final results
    with open(r'json\selected_candidates.json', 'w') as f:
        json.dump(selected_candidates, f, indent=4)
    
    with open(r'json\rejected_candidates.json', 'w') as f:
        json.dump(rejected_candidates, f, indent=4)

    return selected_candidates, rejected_candidates

def main():

    ## IF YOU WANT REALTIME APPLICANTS, UNCOMMENT THE BELOW LINE
    job_description, detailed_applications = main_applicants()

    # job_description = """Company: Tarini Consulting  Location: Remote (India)  Experience Level: 6-8 Years  Salary Range: ₹14-15 LPA(in hand) ​  Are you a talented Laravel Developer with a diverse experience in crafting elegant and efficient web solutions? Tarini Consulting, a leading IT company, is on the lookout for Remote Laravel Developers to join our dynamic team.   Key Responsibilities: Lead the development team to design and implement and improve Laravel-based web applications. Develop, test, and maintain robust and scalable code following best practices. Troubleshoot, debug, and upgrade existing systems for optimal performance. Work closely with front-end developers to integrate user-facing elements with server-side logic. Stay updated on Laravel framework updates and industry best practices. Contribute to the planning and execution of software projects.   Requirements Bachelor’s degree in Computer Science, IT, or a related field. 6-8 Years experience in PHP Laravel Framework Familiarity with front-end technologies such as HTML, CSS, and JavaScript. Knowledge of database design and management using MySQL. Strong problem-solving and analytical skills. Ability to work independently and collaboratively in a remote team environment.   Benefits Competitive salary Opportunity to work remotely and enjoy a flexible work environment. Engage with cutting-edge technologies in a collaborative work culture. Contribute to innovative projects and be a part of a forward-thinking IT company. If you have a passion for web development and want to be part of a thriving IT community, we invite you to apply.  Tarini Consulting is an equal opportunity employer and encourages applicants from diverse backgrounds.   *Note: This is a remote position, and applicants must be based in India."""
    # Load candidates from JSON file
    # with open(r'json\detailed_candidates.json'r, 'r') as file:
    #     detailed_applications = json.load(file)
    
    # Evaluate candidates
    selected, rejected = evaluate_candidates(job_description, detailed_applications)

    print(f"Selected Candidates: {len(selected)}")
    print(f"Rejected Candidates: {len(rejected)}")
    os.remove(r'json\evaluation_progress.json')

if __name__ == "__main__":
    main()