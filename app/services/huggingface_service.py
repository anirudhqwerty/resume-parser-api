# app/services/huggingface_service.py
"""
FIXED Hugging Face API integration with multiple models and fallback + RULE-BASED ANSWERS
"""
import httpx
from app.config import settings
from app.core.logger import get_logger
from typing import Dict, Any, Optional
import json
import re
import asyncio

logger = get_logger(__name__)


class HuggingFaceService:
    """Handle Hugging Face API calls for ML inference with robust fallback"""
    
    def __init__(self):
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.api_url = "https://api-inference.huggingface.co/models"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Multiple models to try (in order of preference)
        self.extraction_models = [
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "microsoft/Phi-3-mini-4k-instruct",
            "HuggingFaceH4/zephyr-7b-beta",
        ]
        
        self.qa_models = [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "microsoft/Phi-3-mini-4k-instruct",
            "HuggingFaceH4/zephyr-7b-beta",
        ]
    
    # [Keep all existing extract_resume_info methods unchanged...]
    
    async def answer_question(self, question: str, candidate_data: Dict[str, Any]) -> str:
        """Answer questions about candidate - WITH RULE-BASED FALLBACK"""
        
        # FIRST: Try rule-based answer for simple questions
        rule_based_answer = self._try_rule_based_answer(question, candidate_data)
        if rule_based_answer:
            logger.info(f"✅ Answered with rule-based logic: {rule_based_answer[:100]}")
            return rule_based_answer
        
        # SECOND: Try LLM if rule-based failed
        context = self._prepare_context(candidate_data)
        logger.info(f"📝 Context prepared:\n{context[:300]}...")
        
        # Try each QA model
        for model in self.qa_models:
            try:
                logger.info(f"🤖 Answering with: {model}")
                
                if "mistral" in model.lower():
                    prompt = f"""<s>[INST] Answer this question about a job candidate concisely.

Candidate Information:
{context}

Question: {question}

Provide a clear, direct answer based only on the information above. Keep it brief (1-2 sentences). [/INST]"""
                elif "phi" in model.lower():
                    prompt = f"""<|system|>
You are a helpful assistant that answers questions about job candidates.<|end|>
<|user|>
Candidate Information:
{context}

Question: {question}

Answer clearly and concisely based on the information provided.<|end|>
<|assistant|>"""
                else:
                    prompt = f"""<|system|>
You are a helpful assistant answering questions about job candidates.</s>
<|user|>
Candidate Information:
{context}

Question: {question}

Answer clearly and concisely.</s>
<|assistant|>"""

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.api_url}/{model}",
                        headers=self.headers,
                        json={
                            "inputs": prompt,
                            "parameters": {
                                "max_new_tokens": 200,
                                "temperature": 0.3,
                                "top_p": 0.9,
                                "do_sample": True,
                                "return_full_text": False
                            },
                            "options": {
                                "wait_for_model": True,
                                "use_cache": False
                            }
                        }
                    )
                    
                    logger.info(f"📥 Response status: {response.status_code}")
                    
                    if response.status_code == 503:
                        logger.warning("Model loading, trying next model...")
                        continue
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if isinstance(result, list) and len(result) > 0:
                            answer = result[0].get("generated_text", "").strip()
                            if answer and len(answer) > 5:
                                logger.info(f"✅ LLM answered: {answer[:100]}")
                                return answer
                        elif isinstance(result, dict):
                            answer = result.get("generated_text", "").strip()
                            if answer and len(answer) > 5:
                                return answer
                    
                    logger.warning(f"❌ {model} failed - Status: {response.status_code}, Response: {response.text[:200]}")
                    
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout with {model}")
                continue
            except Exception as e:
                logger.error(f"❌ Error with {model}: {str(e)}")
                continue
        
        # THIRD: If LLM failed, try rule-based one more time with looser matching
        fallback_answer = self._try_rule_based_answer(question, candidate_data, strict=False)
        if fallback_answer:
            return fallback_answer
        
        return "Unable to generate answer. Please try rephrasing your question."
    
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