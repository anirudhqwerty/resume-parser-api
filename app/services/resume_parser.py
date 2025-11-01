# app/services/resume_parser.py
"""
Robust resume parsing with proper regex extraction
"""
from app.core.logger import get_logger
import re
from typing import Dict, Any, List

logger = get_logger(__name__)


class ResumeParser:
    """Parse resume text with reliable rule-based extraction"""
    
    def __init__(self):
        pass
    
    async def parse_resume(self, text: str) -> Dict[str, Any]:
        """Parse resume - no BS, just results"""
        try:
            logger.info("📄 Starting resume parsing")
            
            result = {
                "introduction": self._extract_contact_info(text),
                "education": self._extract_education(text),
                "experience": self._extract_experience(text),
                "skills": self._extract_skills(text),
                "certifications": self._extract_certifications(text),
                "projects": self._extract_projects(text),
                "hobbies": self._extract_hobbies(text)
            }
            
            logger.info(f"✅ Extracted: {len(result['skills'])} skills, {len(result['projects'])} projects, {len(result['certifications'])} certs, {len(result['hobbies'])} hobbies")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            return self._empty_structure()
    
    def _extract_contact_info(self, text: str) -> str:
        """Extract name, email, phone - WITH EMAIL FIXING"""
        parts = []
        
        # Name (first 3 lines, find the one that looks like a name)
        lines = [l.strip() for l in text.split('\n')[:5] if l.strip()]
        for line in lines:
            if len(line.split()) <= 4 and len(line) < 50 and not '@' in line and not any(char.isdigit() for char in line):
                parts.append(line)
                break
        
        # Email - WITH CORRUPTION FIXES
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            email = email_match.group()
            
            # FIX CORRUPTED EMAILS
            # Fix 1: "petherealX" -> "therealX"
            email = re.sub(r'^p(thereal)', r'\1', email, flags=re.IGNORECASE)
            
            # Fix 2: Other common prefixes before "thereal"
            email = re.sub(r'^[a-z]{1,3}(thereal)', r'\1', email, flags=re.IGNORECASE)
            
            # Fix 3: "Xp@" -> "X@"
            email = email.replace('p@', '@')
            
            parts.append(f"Email: {email}")
        
        # Phone
        phone = re.search(r'[\+\(]?[1-9][0-9 \-\(\)]{8,}[0-9]', text)
        if phone:
            parts.append(f"Phone: {phone.group().strip()}")
        
        result = " | ".join(parts) if parts else "No contact info"
        logger.info(f"📧 Extracted contact: {result}")
        return result
    
    def _extract_education(self, text: str) -> Dict[str, str]:
        """Extract education details"""
        edu = {}
        
        # Find education section
        edu_section = self._find_section(text, ['education', 'academic', 'qualification'])
        search_text = edu_section if edu_section else text[:2000]  # Focus on top part
        
        # Degree - get more context
        degree_patterns = [
            r'(Bachelor[^\n]{5,80})',
            r'(Master[^\n]{5,80})',
            r'(B\.?Tech[^\n]{5,80})',
            r'(M\.?Tech[^\n]{5,80})',
            r'(MBA[^\n]{5,80})',
            r'(PhD[^\n]{5,80})',
            r'(B\.?E\.?[^\n]{5,80})',
            r'(M\.?E\.?[^\n]{5,80})',
        ]
        for pattern in degree_patterns:
            matches = re.findall(pattern, search_text, re.IGNORECASE)
            if matches:
                edu['degree'] = matches[0].strip()
                break
        
        # Institution
        institutions = re.findall(r'\b([A-Z][A-Za-z\s&]+(?:University|Institute|College|School)[A-Za-z\s&]*)', search_text)
        if institutions:
            edu['institution'] = institutions[0].strip()
        
        # Year - all 4 digit years
        years = re.findall(r'\b(19|20)\d{2}\b', search_text)
        if years:
            # If multiple years, assume last is graduation
            edu['year'] = years[-1]
            if len(years) > 1:
                edu['duration'] = f"{years[0]} - {years[-1]}"
        
        # Field - more specific
        fields = ['Computer Engineering', 'Computer Science', 'Software Engineering', 'Information Technology', 
                 'Electronics', 'Mechanical', 'Civil', 'Business', 'Data Science', 'Engineering']
        for field in fields:
            if field.lower() in search_text.lower():
                edu['field'] = field
                break
        
        return edu
    
    def _extract_experience(self, text: str) -> Dict[str, str]:
        """Extract work experience"""
        exp = {}
        
        exp_section = self._find_section(text, ['experience', 'employment', 'work'])
        search_text = exp_section if exp_section else text
        
        # Years of experience
        years = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', search_text, re.IGNORECASE)
        if years:
            exp['total_years'] = f"{years[0]} years"
        
        # Companies
        companies = re.findall(r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&.,]+?)(?:\s*[\n,|]|\s+as\s+)', search_text)
        if companies:
            exp['companies'] = ", ".join(set([c.strip() for c in companies[:3]]))
        
        # Positions
        positions = re.findall(r'\b(Senior|Junior|Lead|Principal)?\s*(Software|Full[- ]?Stack|Backend|Frontend|Data|ML|AI|Cloud|DevOps)?\s*(Engineer|Developer|Architect|Analyst|Scientist|Manager|Consultant)\b', search_text, re.IGNORECASE)
        if positions:
            titles = [" ".join([p for p in pos if p]).strip() for pos in positions[:3]]
            exp['positions'] = ", ".join(set(titles))
        
        return exp
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills"""
        skills = set()
        
        # Programming languages
        langs = ['Python', 'Java', 'JavaScript', 'TypeScript', 'C\\+\\+', 'C#', 'Go', 'Rust', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala', 'R', 'C']
        for lang in langs:
            if re.search(rf'\b{lang}\b', text, re.IGNORECASE):
                skills.add(lang.replace('\\', ''))
        
        # Frameworks
        frameworks = ['React', 'Angular', 'Vue', 'Next\\.js', 'Node\\.js', 'Django', 'Flask', 'FastAPI', 'Spring', 'Express', 'Laravel', 'Rails', 'Streamlit']
        for fw in frameworks:
            if re.search(rf'\b{fw}\b', text, re.IGNORECASE):
                skills.add(fw.replace('\\', ''))
        
        # Databases
        dbs = ['MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch', 'Cassandra', 'DynamoDB', 'Oracle', 'SQL', 'SQLite', 'MariaDB']
        for db in dbs:
            if re.search(rf'\b{db}\b', text, re.IGNORECASE):
                skills.add(db)
        
        # Cloud & Tools
        tools = ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'Git', 'GitHub', 'GitLab', 'CI/CD', 'Terraform', 'Ansible', 'Linux', 'Nginx', 'Apache']
        for tool in tools:
            if re.search(rf'\b{tool}\b', text, re.IGNORECASE):
                skills.add(tool)
        
        # AI/ML
        ml = ['Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP', 'Computer Vision', 'Data Science', 'Scikit-learn', 'Keras', 'OpenCV', 'Pandas', 'NumPy']
        for m in ml:
            if m.lower() in text.lower():
                skills.add(m)
        
        # Other tech
        other = ['REST API', 'GraphQL', 'Microservices', 'Agile', 'Scrum', 'DevOps', 'MLOps', 'DataOps']
        for tech in other:
            if tech.lower() in text.lower():
                skills.add(tech)
        
        return sorted(list(skills))
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications - SUPER AGGRESSIVE"""
        certs = set()
        
        # Find certification section
        cert_section = self._find_section(text, ['certification', 'certificate', 'license', 'credential'])
        
        if cert_section:
            # Extract lines from cert section
            lines = [l.strip() for l in cert_section.split('\n') if l.strip()]
            for line in lines:
                # Skip section headers
                if len(line) < 150 and not any(line.lower().startswith(h) for h in ['certification', 'certificate', 'license']):
                    # Remove bullets and numbering
                    line = re.sub(r'^[•\-\*\d\.\)]+\s*', '', line)
                    if len(line) > 8:
                        certs.add(line)
        
        # Look for certification patterns anywhere
        cert_patterns = [
            r'(AWS Certified[A-Za-z\s\-]*?)(?:\n|,|\||$)',
            r'(Azure[A-Za-z\s\-]*?Certified[A-Za-z\s\-]*?)(?:\n|,|\||$)',
            r'(Google Cloud[A-Za-z\s\-]*?)(?:\n|,|\||$)',
            r'(Certified[A-Za-z\s\-]*?)(?:\n|,|\||$)',
            r'([A-Z][A-Za-z\s]*Certificate[A-Za-z\s]*?)(?:\n|,|\||$)',
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean = match.strip()
                if 8 < len(clean) < 100:
                    certs.add(clean)
        
        # Common certifications - if found, extract context
        cert_keywords = ['AWS', 'Azure', 'Google Cloud', 'GCP', 'PMP', 'CISSP', 'CompTIA', 
                        'Kubernetes', 'Oracle', 'Salesforce', 'Cisco', 'ITIL', 'Scrum']
        
        for keyword in cert_keywords:
            # Look for "Certified X" or "X Certified"
            pattern = rf'(?:Certified\s+{keyword}|{keyword}\s+Certified)[A-Za-z\s\-]*'
            matches = re.findall(pattern, text, re.IGNORECASE)
            certs.update([m.strip() for m in matches if len(m.strip()) > 5])
        
        return sorted(list(certs))[:15]
    
    def _extract_projects(self, text: str) -> List[str]:
        """Extract projects - group them properly"""
        projects = []
        
        # Find projects section
        proj_section = self._find_section(text, ['project', 'portfolio'])
        
        if proj_section:
            # Look for project titles (usually have GitHub link or bold formatting)
            # Pattern: Project Name | Technologies
            project_titles = re.findall(r'([^\n•\-]{10,}?)(?:\||GitHub)', proj_section, re.IGNORECASE)
            
            if project_titles:
                # Get unique project titles
                for title in project_titles:
                    clean_title = title.strip()
                    if len(clean_title) > 10 and clean_title not in projects:
                        projects.append(clean_title)
            else:
                # Fallback: split by double newline or bullets
                chunks = re.split(r'\n\s*\n|^[•\-\*]\s*', proj_section, flags=re.MULTILINE)
                for chunk in chunks:
                    # Get first line as project name
                    first_line = chunk.split('\n')[0].strip()
                    if 10 < len(first_line) < 150 and not first_line.lower().startswith('project'):
                        projects.append(first_line)
        
        # If still no projects, look for "Built/Developed" patterns
        if not projects:
            patterns = [
                r'(?:Built|Developed|Created|Implemented)\s+([^.]{20,100}?)(?:\.|using|with)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                projects.extend([m.strip() for m in matches[:5]])
        
        return projects[:10]
    
    def _extract_hobbies(self, text: str) -> List[str]:
        """Extract hobbies and interests - SUPER AGGRESSIVE"""
        hobbies = set()
        
        # Find hobbies section
        hobby_section = self._find_section(text, ['hobbies', 'interests', 'personal', 'activities'])
        
        if hobby_section:
            # Split by common separators
            items = re.split(r'[,•\-\n|]', hobby_section)
            for item in items:
                item = re.sub(r'^[\d\.\s]+', '', item).strip()  # Remove numbering
                # Hobbies are short phrases
                if 3 < len(item) < 60 and not any(keyword in item.lower() for keyword in ['hobbies', 'interests', 'activities', 'personal']):
                    hobbies.add(item)
        
        # If no hobbies found, check common hobbies anywhere in text
        if not hobbies:
            common_hobbies = [
                'Reading', 'Writing', 'Gaming', 'Music', 'Sports', 'Travel', 'Traveling', 'Photography', 
                'Cooking', 'Fitness', 'Yoga', 'Meditation', 'Art', 'Drawing', 'Painting',
                'Blogging', 'Volunteering', 'Dancing', 'Singing', 'Guitar', 'Piano',
                'Running', 'Cycling', 'Swimming', 'Hiking', 'Chess', 'Cricket', 'Football',
                'Basketball', 'Tennis', 'Badminton', 'Movies', 'Films', 'TV Shows',
                'Anime', 'Manga', 'Video Games', 'Board Games', 'Gardening', 'Baking',
                'AI/ML Research', 'Automation', 'Backend Development', 'Open Source'
            ]
            
            for hobby in common_hobbies:
                # Only add if it appears in a personal/hobby context
                if re.search(rf'\b{hobby}\b', text, re.IGNORECASE):
                    # Check it's not in a professional context
                    context = re.search(rf'.{{0,50}}{hobby}.{{0,50}}', text, re.IGNORECASE)
                    if context and not any(word in context.group().lower() for word in ['project', 'developed', 'built', 'worked']):
                        hobbies.add(hobby)
        
        return sorted(list(hobbies))[:15]
    
    def _find_section(self, text: str, keywords: List[str]) -> str:
        """Find a section in text by keywords"""
        text_lower = text.lower()
        
        for keyword in keywords:
            # Look for section header
            pattern = rf'\b{keyword}s?\b[\s:]*\n(.+?)(?:\n\n|\n[A-Z]{{3,}}|\Z)'
            match = re.search(pattern, text_lower, re.DOTALL)
            if match:
                # Get original text with proper casing
                start = match.start(1)
                end = match.end(1)
                return text[start:end]
        
        return ""
    
    def _empty_structure(self) -> Dict[str, Any]:
        """Empty structure"""
        return {
            "introduction": "",
            "education": {},
            "experience": {},
            "skills": [],
            "certifications": [],
            "projects": [],
            "hobbies": []
        }