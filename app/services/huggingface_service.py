# app/services/huggingface_service.py
"""
Complete Groq AI integration for resume extraction AND Q&A
"""
import os
from huggingface_hub import InferenceClient
from app.config import settings
from app.core.logger import get_logger
from typing import Dict, Any, Optional
import asyncio
import json
import re

logger = get_logger(__name__)


class HuggingFaceService:
    """Handle all AI tasks using FREE Groq provider"""
    
    def __init__(self):
        # Set up the Hugging Face token
        os.environ["HF_TOKEN"] = settings.HUGGINGFACE_API_KEY
        
        # Initialize InferenceClient with Groq provider (FREE!)
        self.client = InferenceClient(
            provider="groq",
            api_key=os.environ["HF_TOKEN"]
        )
        
        # Free model available through Groq
        self.model = "openai/gpt-oss-safeguard-20b"
    
    async def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract structured information from resume using Groq AI
        
        Args:
            resume_text: Raw text extracted from resume file
            
        Returns:
            Dictionary with extracted candidate information
        """
        try:
            logger.info(f"🤖 Extracting resume info with Groq AI (text length: {len(resume_text)})")
            
            # Truncate if too long (to fit in context)
            if len(resume_text) > 4000:
                logger.warning(f"⚠️ Resume text too long ({len(resume_text)} chars), truncating to 4000")
                resume_text = resume_text[:4000]
            
            prompt = f"""Extract structured information from this resume and return ONLY valid JSON.

Resume Text:
{resume_text}

Return a JSON object with these fields (use empty string/array if not found):
{{
    "introduction": "Full Name | Email: email@example.com | Phone: +1234567890",
    "education": {{
        "degree": "Bachelor of Technology in Computer Science",
        "institution": "University Name",
        "field": "Computer Science",
        "year": "2023"
    }},
    "experience": {{
        "total_years": "3 years",
        "companies": "Company A, Company B",
        "positions": "Software Engineer, Developer"
    }},
    "skills": ["Python", "JavaScript", "React", "Node.js"],
    "projects": ["E-commerce Platform", "Chat Application"],
    "hobbies": ["Reading", "Gaming", "Photography"],
    "certifications": ["AWS Certified Developer", "Google Cloud Associate"]
}}

CRITICAL: Return ONLY the JSON object, no markdown, no explanation, no extra text."""

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_sync,
                prompt
            )
            
            if result:
                logger.info(f"✅ Successfully extracted resume info with Groq")
                logger.info(f"📊 Extracted: {len(result.get('skills', []))} skills, {len(result.get('projects', []))} projects")
                return result
            else:
                logger.warning("⚠️ Groq extraction returned empty, using fallback")
                return self._get_default_structure()
                
        except Exception as e:
            logger.error(f"❌ Error extracting resume with Groq: {str(e)}")
            return self._get_default_structure()
    
    def _extract_sync(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Synchronous call to Groq for extraction"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a resume parser that extracts structured data. Always return valid JSON only, no markdown formatting."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1500
            )
            
            response_text = completion.choices[0].message.content.strip()
            logger.info(f"📥 Groq extraction response: {response_text[:200]}...")
            
            # Clean the response
            response_text = self._clean_json_response(response_text)
            
            # Parse JSON
            parsed = json.loads(response_text)
            
            # Validate structure
            return self._validate_and_fix_structure(parsed)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {str(e)}")
            logger.error(f"Raw response: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"❌ Groq extraction error: {str(e)}")
            return None
    
    def _clean_json_response(self, text: str) -> str:
        """Clean JSON response from potential markdown or extra text"""
        # Remove markdown code blocks
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        
        # Find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text
    
    def _validate_and_fix_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix extracted data structure"""
        fixed = {
            "introduction": str(data.get("introduction", "")),
            "education": data.get("education", {}) if isinstance(data.get("education"), dict) else {},
            "experience": data.get("experience", {}) if isinstance(data.get("experience"), dict) else {},
            "skills": data.get("skills", []) if isinstance(data.get("skills"), list) else [],
            "projects": data.get("projects", []) if isinstance(data.get("projects"), list) else [],
            "hobbies": data.get("hobbies", []) if isinstance(data.get("hobbies"), list) else [],
            "certifications": data.get("certifications", []) if isinstance(data.get("certifications"), list) else []
        }
        
        # Ensure education has proper structure
        if fixed["education"]:
            fixed["education"] = {
                "degree": str(fixed["education"].get("degree", "")),
                "institution": str(fixed["education"].get("institution", "")),
                "field": str(fixed["education"].get("field", "")),
                "year": str(fixed["education"].get("year", ""))
            }
        
        # Ensure experience has proper structure
        if fixed["experience"]:
            fixed["experience"] = {
                "total_years": str(fixed["experience"].get("total_years", "")),
                "companies": str(fixed["experience"].get("companies", "")),
                "positions": str(fixed["experience"].get("positions", ""))
            }
        
        return fixed
    
    async def answer_question(self, question: str, candidate_data: Dict[str, Any]) -> str:
        """Answer questions about candidate - WITH RULE-BASED FALLBACK"""
        
        # FIRST: Try rule-based answer for simple questions
        rule_based_answer = self._try_rule_based_answer(question, candidate_data)
        if rule_based_answer:
            logger.info(f"✅ Answered with rule-based logic: {rule_based_answer[:100]}")
            return rule_based_answer
        
        # SECOND: Try Groq LLM if rule-based failed
        try:
            context = self._prepare_context(candidate_data)
            logger.info(f"🔍 Context prepared, asking Groq...")
            
            prompt = f"""Answer this question about a job candidate concisely.

Candidate Information:
{context}

Question: {question}

Provide a clear, direct answer based only on the information above. Keep it brief (1-2 sentences)."""

            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None,
                self._ask_groq_sync,
                prompt
            )
            
            if answer and len(answer) > 5:
                logger.info(f"✅ Groq answered: {answer[:100]}")
                return answer
                
        except Exception as e:
            logger.error(f"❌ Error with Groq QA: {str(e)}")
        
        # THIRD: If LLM failed, try rule-based one more time with looser matching
        fallback_answer = self._try_rule_based_answer(question, candidate_data, strict=False)
        if fallback_answer:
            return fallback_answer
        
        return "Unable to generate answer. Please try rephrasing your question."
    
    def _ask_groq_sync(self, prompt: str) -> Optional[str]:
        """Synchronous question answering via Groq"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant answering questions about job candidates. Be concise and direct."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Groq QA error: {str(e)}")
            return None
    
    def _try_rule_based_answer(self, question: str, candidate_data: Dict[str, Any], strict: bool = True) -> Optional[str]:
        """
        Try to answer simple questions with rule-based logic
        
        Args:
            question: The user's question
            candidate_data: Candidate information
            strict: If True, only match exact patterns. If False, be more lenient.
        
        Returns:
            Answer string or None if can't answer with rules
        """
        q_lower = question.lower().strip()
        
        # NAME questions
        name_keywords = ['name', 'called', 'who is', 'candidate name', 'their name']
        if strict:
            is_name_question = any(keyword in q_lower for keyword in name_keywords) and len(q_lower) < 30
        else:
            is_name_question = any(keyword in q_lower for keyword in name_keywords)
        
        if is_name_question:
            intro = candidate_data.get("introduction", "")
            if intro:
                # Extract name from "Anirudh Sharma | Email: ..."
                name = intro.split("|")[0].strip() if "|" in intro else intro.split("Email:")[0].strip()
                if name and len(name) < 50:
                    return f"The candidate's name is {name}."
        
        # SKILLS questions
        skills_keywords = ['skills', 'skill', 'technologies', 'tech stack', 'knows', 'proficient']
        if any(keyword in q_lower for keyword in skills_keywords):
            skills = candidate_data.get("skills", [])
            if skills and isinstance(skills, list):
                if len(skills) <= 5:
                    return f"The candidate's skills include: {', '.join(skills)}."
                else:
                    return f"The candidate has skills in: {', '.join(skills[:10])}. Plus {len(skills) - 10} more skills."
        
        # HOBBIES questions
        hobbies_keywords = ['hobbies', 'hobby', 'interests', 'interest', 'free time', 'likes to do']
        if any(keyword in q_lower for keyword in hobbies_keywords):
            hobbies = candidate_data.get("hobbies", [])
            if hobbies and isinstance(hobbies, list):
                return f"The candidate's hobbies and interests include: {', '.join(hobbies)}."
        
        # EDUCATION questions
        education_keywords = ['education', 'degree', 'university', 'college', 'studied', 'graduated']
        if any(keyword in q_lower for keyword in education_keywords):
            edu = candidate_data.get("education", {})
            if edu and isinstance(edu, dict):
                parts = []
                if edu.get("degree"):
                    parts.append(edu["degree"])
                if edu.get("institution"):
                    parts.append(f"from {edu['institution']}")
                if edu.get("year"):
                    parts.append(f"in {edu['year']}")
                
                if parts:
                    return f"The candidate's education: {' '.join(parts)}."
        
        # EXPERIENCE questions
        experience_keywords = ['experience', 'worked', 'work', 'job', 'career', 'years of experience']
        if any(keyword in q_lower for keyword in experience_keywords):
            exp = candidate_data.get("experience", {})
            if exp and isinstance(exp, dict):
                parts = []
                if exp.get("total_years"):
                    parts.append(f"{exp['total_years']} of experience")
                if exp.get("companies"):
                    parts.append(f"at companies including {exp['companies']}")
                if exp.get("positions"):
                    parts.append(f"in roles such as {exp['positions']}")
                
                if parts:
                    return f"The candidate has {', '.join(parts)}."
        
        # PROJECTS questions
        projects_keywords = ['projects', 'project', 'built', 'developed', 'created']
        if any(keyword in q_lower for keyword in projects_keywords):
            projects = candidate_data.get("projects", [])
            if projects and isinstance(projects, list):
                if len(projects) <= 3:
                    return f"The candidate has worked on projects including: {', '.join(projects)}."
                else:
                    return f"The candidate has worked on {len(projects)} projects including: {', '.join(projects[:5])}."
        
        # CERTIFICATIONS questions
        cert_keywords = ['certification', 'certified', 'certificate']
        if any(keyword in q_lower for keyword in cert_keywords):
            certs = candidate_data.get("certifications", [])
            if certs and isinstance(certs, list) and certs:
                return f"The candidate has certifications in: {', '.join(certs)}."
            else:
                return "The candidate has no certifications listed."
        
        # EMAIL/CONTACT questions
        contact_keywords = ['email', 'contact', 'phone', 'reach']
        if any(keyword in q_lower for keyword in contact_keywords):
            intro = candidate_data.get("introduction", "")
            if intro:
                return f"Contact information: {intro}"
        
        return None
    
    def _prepare_context(self, candidate_data: Dict[str, Any]) -> str:
        """Format candidate data for context"""
        parts = []
        
        # Extract NAME from introduction
        if candidate_data.get("introduction"):
            intro = candidate_data["introduction"]
            name = intro.split("|")[0].strip() if "|" in intro else intro.split("Email:")[0].strip()
            parts.append(f"Name: {name}")
            parts.append(f"Contact: {intro}")
        
        # Education
        if candidate_data.get("education"):
            edu = candidate_data["education"]
            if isinstance(edu, dict):
                edu_parts = []
                if edu.get("degree"):
                    edu_parts.append(edu["degree"])
                if edu.get("institution"):
                    edu_parts.append(f"from {edu['institution']}")
                if edu.get("field"):
                    edu_parts.append(f"in {edu['field']}")
                if edu.get("year"):
                    edu_parts.append(f"({edu['year']})")
                
                if edu_parts:
                    parts.append(f"Education: {' '.join(edu_parts)}")
            else:
                parts.append(f"Education: {edu}")
        
        # Experience
        if candidate_data.get("experience"):
            exp = candidate_data["experience"]
            if isinstance(exp, dict):
                exp_parts = []
                for key, value in exp.items():
                    if value:
                        exp_parts.append(f"{key}: {value}")
                if exp_parts:
                    parts.append(f"Experience: {', '.join(exp_parts)}")
            else:
                parts.append(f"Experience: {exp}")
        
        # Skills
        if candidate_data.get("skills"):
            skills = candidate_data["skills"]
            if isinstance(skills, list):
                parts.append(f"Skills: {', '.join(skills[:20])}")
            else:
                parts.append(f"Skills: {skills}")
        
        # Projects
        if candidate_data.get("projects"):
            projects = candidate_data["projects"]
            if isinstance(projects, list):
                parts.append(f"Projects: {', '.join(str(p) for p in projects[:8])}")
            else:
                parts.append(f"Projects: {projects}")
        
        # Hobbies
        if candidate_data.get("hobbies"):
            hobbies = candidate_data["hobbies"]
            if isinstance(hobbies, list):
                parts.append(f"Hobbies: {', '.join(hobbies[:15])}")
            else:
                parts.append(f"Hobbies: {hobbies}")
        
        # Certifications
        if candidate_data.get("certifications"):
            certs = candidate_data["certifications"]
            if isinstance(certs, list) and certs:
                parts.append(f"Certifications: {', '.join(certs[:10])}")
        
        return "\n".join(parts)
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """Return default empty structure if extraction fails"""
        return {
            "introduction": "",
            "education": {
                "degree": "",
                "institution": "",
                "field": "",
                "year": ""
            },
            "experience": {
                "total_years": "",
                "companies": "",
                "positions": ""
            },
            "skills": [],
            "projects": [],
            "hobbies": [],
            "certifications": []
        }