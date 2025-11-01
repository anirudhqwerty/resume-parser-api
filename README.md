# Resume Parser API

A FastAPI-based resume parsing system that extracts structured information from resumes (PDF/DOCX) and provides intelligent Q&A capabilities using AI.

## Features

- **Resume Upload & Parsing**: Upload PDF/DOCX resumes and automatically extract structured data
- **Intelligent Q&A**: Ask natural language questions about candidates using LLM-powered responses
- **Dual Storage**: Supabase for file storage, MongoDB for structured candidate data
- **Background Processing**: Asynchronous resume processing for better performance
- **RESTful API**: Clean, well-documented endpoints with proper error handling

## Tech Stack

- **Framework**: FastAPI
- **Storage**: Supabase (file storage + metadata), MongoDB (candidate data)
- **AI/ML**: HuggingFace API (Mistral, Phi-3, Zephyr models)
- **Text Extraction**: PyMuPDF (PDF), python-docx (DOCX)
- **Language**: Python 3.8+

## Project Structure

```
resume-parser-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration settings
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── logger.py              # Centralized logging
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic models
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py              # Resume upload endpoint
│   │   ├── candidates.py          # Candidate listing/detail endpoints
│   │   └── qa.py                  # Q&A endpoint
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_service.py        # File handling & validation
│   │   ├── resume_parser.py       # Resume parsing logic
│   │   ├── supabase_service.py    # Supabase integration
│   │   ├── mongodb_service.py     # MongoDB operations
│   │   └── huggingface_service.py # LLM integration
│   │
│   └── utils/
│       ├── __init__.py
│       └── text_extractor.py      # PDF/DOCX text extraction
│
├── tests/
│   └── __init__.py
│
├── .env.example                   # Environment variables template
├── .gitignore
├── requirements.txt
├── README.md
└── run.py                         # Application runner
```

## Setup

### Prerequisites

- Python 3.8 or higher
- MongoDB instance (local or cloud)
- Supabase account
- HuggingFace API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd resume-parser-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   
5. **Set up Supabase**
   
   Create a table in your Supabase project:
   ```sql
   CREATE TABLE resumes_metadata (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     filename TEXT NOT NULL,
     storage_path TEXT NOT NULL,
     upload_time TIMESTAMP NOT NULL,
     file_size INTEGER,
     content_type TEXT,
     created_at TIMESTAMP DEFAULT NOW()
   );
   ```

   Create a storage bucket named `resumes` (or your chosen name).

6. **Set up MongoDB**
   
   The `candidates` collection will be created automatically on first use.

## Running the Application

### Development Mode

```bash
python run.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

Interactive API documentation: `http://localhost:8000/docs`

## API Endpoints

### 1. Upload Resume

**POST** `/upload`

Upload a resume file (PDF or DOCX) for parsing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (PDF or DOCX file)

**Response:**
```json
{
  "message": "File uploaded successfully and processing started",
  "file_id": "resumes/uuid.pdf",
  "candidate_id": "uuid",
  "filename": "resume.pdf",
  "upload_time": "2025-11-02T10:30:00"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -F "file=@resume.pdf"
```

### 2. List Candidates

**GET** `/candidates`

Get a summary list of all candidates.

**Response:**
```json
[
  {
    "id": "mongodb_id",
    "candidate_id": "uuid",
    "name": "John Doe",
    "skills": ["Python", "FastAPI", "MongoDB"],
    "experience_years": "5 years",
    "created_at": "2025-11-02T10:30:00"
  }
]
```

**Example:**
```bash
curl "http://localhost:8000/candidates"
```

### 3. Get Candidate Details

**GET** `/candidate/{candidate_id}`

Get complete information for a specific candidate.

**Response:**
```json
{
  "id": "mongodb_id",
  "candidate_id": "uuid",
  "education": {
    "degree": "B.Tech in Computer Science",
    "institution": "XYZ University",
    "year": "2020"
  },
  "experience": {
    "total_years": "5 years",
    "companies": "ABC Corp, XYZ Inc",
    "positions": "Senior Software Engineer"
  },
  "skills": ["Python", "FastAPI", "MongoDB", "React"],
  "hobbies": ["Reading", "Gaming", "Travel"],
  "certifications": ["AWS Certified Developer"],
  "projects": ["E-commerce Platform", "ML Pipeline"],
  "introduction": "John Doe | Email: john@example.com | Phone: +1234567890",
  "created_at": "2025-11-02T10:30:00"
}
```

**Example:**
```bash
curl "http://localhost:8000/candidate/uuid-here"
```

### 4. Ask Question about Candidate

**POST** `/ask/{candidate_id}`

Ask a natural language question about a candidate using AI.

**Request:**
```json
{
  "question": "What are the candidate's Python skills?"
}
```

**Response:**
```json
{
  "question": "What are the candidate's Python skills?",
  "answer": "The candidate has strong Python skills including FastAPI, Django, and data science libraries like Pandas and NumPy.",
  "candidate_id": "uuid"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/ask/uuid-here" \
  -H "Content-Type: application/json" \
  -d '{"question": "What programming languages does the candidate know?"}'
```
# resume-parser-api
