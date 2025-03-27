import os
import json
import traceback
from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

def initialize_llm():
    """
    Initialize the Ollama LLM with Llama 3.2:3b model
    """
    return OllamaLLM(
        model="llama3.2:3b", 
        temperature=0.2
    )

def create_candidate_evaluation_prompt():
    """
    Create a detailed prompt template for candidate evaluation
    """
    return ChatPromptTemplate.from_messages([
        ("system", """
        You are an expert HR recruiter analyzing a candidate's profile against a specific job description.
        Evaluate the candidate systematically and provide a detailed, structured JSON response.
        
        Please evaluate this candidate systematically:

        1. Skill Match Assessment:
        - Carefully compare the candidate's skills with job requirements
        - Note any direct matches or close alignments
        - Identify any skill gaps

        2. Experience Relevance:
        - Review work history and roles
        - Assess how closely their experience matches the job needs

        3. Scoring Criteria:
        - Technical Skills (out of 4 points)
        - Relevant Experience (out of 6 points)
        
        The JSON must include these exact keys:
        - score: total score out of 10
        - recommendation: "Shortlist" or "Reject"
        - reasoning: detailed explanation
        - strong_points: list of strengths
        - areas_of_concern: list of concerns
        """),
        ("human", """
        Job Description:
        {job_description}

        Candidate Profile:
        {candidate_profile}

        Provide a comprehensive evaluation in strict JSON format.
        """)
    ])

def evaluate_candidates(job_description, detailed_applications):
    """
    Evaluate candidates using Ollama LLM and categorize them
    """
    llm = initialize_llm()
    prompt = create_candidate_evaluation_prompt()
    output_parser = JsonOutputParser()
    
    # Create a chain
    chain = prompt | llm | output_parser

    selected_candidates = []
    rejected_candidates = []
    print("Evaluation Started...")
    for idx, candidate in enumerate(detailed_applications, 1):
        print(f"Evaluating Candidate {idx}/{len(candidate)}")
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
        print(f"candidate profile:\n{candidate_profile}\n")
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
            print(f"Results:\n{candidate_result}\n")
            # Categorize candidates
            if evaluation.get('recommendation') == 'Shortlist':
                selected_candidates.append(candidate_result)
            else:
                rejected_candidates.append(candidate_result)

        except Exception as e:
            print(f"Error processing candidate {candidate.get('Full_Name')}: {e}")
            print(traceback.format_exc())

    # Save results
    with open('selected_candidates.json', 'w') as f:
        json.dump(selected_candidates, f, indent=4)
    
    with open('rejected_candidates.json', 'w') as f:
        json.dump(rejected_candidates, f, indent=4)

    return selected_candidates, rejected_candidates

def main():
    # Get job description and detailed applications
    job_description = """Location: Remote(India Based Only) Salary: 10-14 LPA Job Description We're seeking an experienced Senior Frontend Developer to join our team and take a lead role in enhancing our exciting projects. You'll collaborate with cross-functional teams to design, develop, and deliver high-quality frontend solutions that meet client expectations. This role offers the opportunity to showcase your technical expertise, mentor junior developers, and drive the success of our development initiatives. Responsibilities Design, develop, and maintain the frontend of our projects using HTML, CSS, and JavaScript. Work closely with designers, backend developers, and project managers to ensure seamless integration of frontend and backend systems. Provide technical leadership by mentoring junior developers and promoting best practices in code quality and development processes. Conduct code reviews and contribute to improving our development workflows. Stay current with emerging frontend technologies and trends to keep our solutions cutting-edge. Requirements 5+ years of hands-on experience in frontend development. Strong proficiency in HTML, CSS, and JavaScript. Proven expertise with modern frontend frameworks such as React, Angular, or Vue.js. Solid understanding of web development principles, including accessibility, performance optimization, and security. Excellent communication, teamwork, and problem-solving skills. Familiarity with Zoho Creator and Laravel is a plus, but not mandatory. Benefits Competitive salary range of 10-14 LPA. Opportunities for career growth and skill development. A collaborative, dynamic, and supportive work environment. Remote and Flexible work timings to support work-life balance."""
    
    # Load candidates from JSON file
    with open("detailed_candidates.json", 'r') as file:
        detailed_applications = json.load(file)
    
    print(len(detailed_applications))
    # Evaluate candidates
    selected, rejected = evaluate_candidates(job_description, detailed_applications)

    print(f"Selected Candidates: {len(selected)}")
    print(f"Rejected Candidates: {len(rejected)}")

if __name__ == "__main__":
    main()