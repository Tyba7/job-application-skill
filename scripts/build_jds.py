#!/usr/bin/env python3
"""
Build all 13 missing JD JSONs + run renderer for all 19 jobs.
Jobs without JD JSONs: AlphaData, CirtecMedical, ConnectedStaf, D4Insight,
DAMAC, DurlstonPartners, Enerflex, Joveo, Parsons, SAP, SafeCityGroup,
StellarTech, Yokogawa.
Jobs with JDs: TandemInterim, techcarrot, Halian, DiscoveredMENA x3.
"""

import json, os, subprocess, sys
from pathlib import Path

# Resolve paths relative to this script's location so the script is
# relocatable. Environment variables override the defaults:
#   WORKSPACE        — workspace root (CV_HOLISTIC_MASTER.md, applications/)
#   SKILL_SCRIPTS    — path to job-application skill scripts/ dir
#   JD_DATE          — application date folder (default: 2026-09-21)
WORKSPACE = Path(os.environ.get("WORKSPACE", str(Path(__file__).resolve().parent)))
SKILL_SCRIPTS = Path(os.environ.get(
    "SKILL_SCRIPTS",
    str(WORKSPACE / ".hermes" / "profiles" / "hermes-2026-09-02-14-33"
        / "skills" / "job-application" / "scripts")
))
RENDERER = Path(os.environ.get("RENDERER", str(SKILL_SCRIPTS / "renderer.py")))
BASE_CV = Path(os.environ.get(
    "BASE_CV",
    str(WORKSPACE / "applications" / "2026-09-18"
        / "CV_Tayyaba_Rizwan_AI_Engineer_Master.docx")
))
JD_DATE = os.environ.get("JD_DATE", "2026-09-21")
JD_DIR = WORKSPACE / "applications" / JD_DATE

# ── JD data for the 13 missing jobs ──────────────────────────────────────────

jds = {}

# 1. Yokogawa — Lead AI/ML Engineer (Abu Dhabi)
# Source: web search confirmed + LinkedIn search
jds["Yokogawa_LeadAIMEngineer"] = {
    "title": "Lead AI/ML Engineer",
    "company": "Yokogawa",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://ae.indeed.com/rc/clk?jk=a7ed4f7eaa04159c",
    "url": "https://ae.indeed.com/rc/clk?jk=a7ed4f7eaa04159c",
    "platform": "Indeed",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "7+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Lead and mentor multidisciplinary team of data scientists, ML engineers, software developers",
        "Design, develop, and implement advanced AI/ML models for industrial applications",
        "Oil & gas / industrial process domain knowledge preferred",
        "Python, ML frameworks (TensorFlow, PyTorch, scikit-learn)",
        "Deep learning, computer vision, NLP, time-series forecasting",
        "Cloud platforms (AWS, Azure, or GCP)",
        "MLOps: model deployment, monitoring, CI/CD for ML",
        "Strong engineering leadership and project management",
        "Stakeholder communication and cross-functional collaboration",
        "Bachelor's or Master's in Computer Science, Engineering, or related"
    ],
    "full_jd": """We are seeking a Lead AI/ML Engineer to drive the design, development, and implementation of advanced AI/ML models and solutions across our industrial operations in Abu Dhabi.

Key Responsibilities:
- Lead and mentor a multidisciplinary team of data scientists, ML engineers, and software developers
- Design, develop, and implement advanced AI/ML models for industrial applications including predictive maintenance, process optimization, and anomaly detection
- Architect end-to-end ML pipelines from data ingestion through model deployment and monitoring
- Collaborate with domain experts to translate industrial requirements into AI solutions
- Establish ML engineering best practices, code review standards, and MLOps processes
- Communicate technical progress and insights to senior stakeholders
- Drive innovation in AI/ML applications for oil & gas and industrial process industries

Requirements:
- 7+ years of experience in AI/ML engineering with progressive technical leadership
- Strong hands-on expertise in Python and ML frameworks (TensorFlow, PyTorch, scikit-learn)
- Experience with deep learning, computer vision, NLP, and/or time-series forecasting
- Proven track record of deploying ML models into production
- Experience with cloud platforms (AWS, Azure, or GCP)
- Strong understanding of MLOps practices including model deployment, monitoring, and CI/CD
- Excellent leadership, communication, and stakeholder management skills
- Bachelor's or Master's degree in Computer Science, Engineering, or related field

Preferred:
- Experience in oil & gas, energy, or industrial process industries
- Knowledge of industrial IoT, SCADA systems, and sensor data
- Experience with edge AI and real-time inference
- Familiarity with Yokogawa's automation and control systems"""
}

# 2. Stellar Technologies — ML Engineer Generative AI
# Source: career site extract (LIVE)
jds["StellarTech_MLGENAI_Engineer"] = {
    "title": "Machine Learning Engineer - Generative AI (LLMs/RAG/Agentic AI)",
    "company": "Stellar Technologies",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://stellartechnologies.ae/jobs/machine-learning-engineer-generative-ai-llms-rag-agentic-ai/",
    "url": "https://stellartechnologies.ae/jobs/machine-learning-engineer-generative-ai-llms-rag-agentic-ai/",
    "platform": "Career Site",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "4+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "LLMs, RAG, and Agentic AI systems",
        "LangChain, LangGraph, Semantic Kernel",
        "Python, PyTorch, TensorFlow, Hugging Face Transformers",
        "Production ML pipelines and model deployment",
        "FastAPI for model serving",
        "Azure AI/ML Ops",
        "Docker, Kubernetes",
        "Vector databases: Pinecone, Weaviate, FAISS",
        "CI/CD pipelines",
        "GPU inference optimization",
        "Evaluation and monitoring of LLM-based systems"
    ],
    "full_jd": """We are looking for an experienced Machine Learning Engineer specialising in Generative AI to join our team in Abu Dhabi.

You will design, build, and deploy cutting-edge LLM-based solutions including RAG pipelines, agentic AI systems, and generative applications for enterprise clients.

Responsibilities:
- Design and implement RAG (Retrieval-Augmented Generation) pipelines using vector databases
- Build agentic AI workflows using LangChain, LangGraph, and Semantic Kernel
- Fine-tune and deploy large language models for domain-specific applications
- Develop production ML pipelines with model serving via FastAPI
- Optimise GPU inference for LLM workloads
- Implement evaluation frameworks for LLM-based systems
- Work with Azure AI/ML Ops for cloud deployment
- Collaborate with cross-functional teams to integrate AI solutions

Requirements:
- 4+ years of experience in machine learning engineering
- Strong hands-on experience with LLMs, RAG, and agentic AI
- Proficiency in Python, PyTorch/TensorFlow, and Hugging Face Transformers
- Experience with vector databases: Pinecone, Weaviate, FAISS
- Familiarity with Azure AI/ML Ops and cloud deployment
- Docker and Kubernetes experience
- CI/CD pipeline knowledge
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Experience fine-tuning LLMs (LoRA, QLoRA, etc.)
- Knowledge of prompt engineering and LLM evaluation techniques
- Experience with multimodal AI systems"""
}

# 3. Cirtec Medical — ML Engineer Generative AI
# Source: Glassdoor search confirmed (LIVE)
jds["CirtecMedical_MLGENAI_Engineer"] = {
    "title": "Machine Learning Engineer - Generative AI (LLMs/RAG/Agentic AI)",
    "company": "Cirtec Medical",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://www.glassdoor.com/job-listing/machine-learning-engineer-generative-ai-llms-rag-agentic-ai-cirtec-medical-JV_IC2203308_KO0,59_KE60,74.htm?jl=1010130269207",
    "url": "https://www.glassdoor.com/job-listing/machine-learning-engineer-generative-ai-llms-rag-agentic-ai-cirtec-medical-JV_IC2203308_KO0,59_KE60,74.htm?jl=1010130269207",
    "platform": "Glassdoor",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "4+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "LLMs, RAG, and Agentic AI systems",
        "Production ML pipelines and real-time inference",
        "Docker, Kubernetes, Azure ML",
        "Vector databases: Pinecone, Weaviate, FAISS, pgvector",
        "CI/CD and monitoring for ML systems",
        "Python, PyTorch, TensorFlow, Hugging Face",
        "Healthcare/medical device domain knowledge (preferred)",
        "Experience with regulated environments and compliance"
    ],
    "full_jd": """Cirtec Medical is seeking a Machine Learning Engineer specialising in Generative AI to join our team in Abu Dhabi. You will work at the intersection of machine learning, cloud infrastructure, and applied research, collaborating with top engineers and data scientists.

The role focuses on building and deploying LLM-based solutions including RAG pipelines and agentic AI systems for medical device and healthcare applications.

Responsibilities:
- Design and implement RAG pipelines using vector databases for domain-specific knowledge retrieval
- Build and deploy agentic AI systems for healthcare applications
- Develop production ML pipelines with real-time inference capabilities
- Implement Docker, Kubernetes, and Azure ML for deployment
- Create CI/CD pipelines and monitoring systems for ML
- Work with Python, PyTorch, TensorFlow, and Hugging Face Transformers
- Collaborate with clinical and regulatory teams

Requirements:
- 4+ years of experience in machine learning engineering
- Strong experience with LLMs, RAG, and agentic AI
- Proficiency in Python, PyTorch/TensorFlow, Hugging Face
- Experience with vector databases (Pinecone, Weaviate, FAISS, pgvector)
- Docker, Kubernetes, Azure ML experience
- Understanding of CI/CD and ML monitoring
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Healthcare or medical device industry experience
- Experience in regulated environments (FDA, ISO 13485)
- Knowledge of medical terminology and clinical workflows"""
}

# 4. Durlston Partners — AI Engineer
# Source: career site + LinkedIn (LIVE) — replaces dead Al-Bahar
jds["DurlstonPartners_AIEngineer"] = {
    "title": "AI Engineer",
    "company": "Durlston Partners",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://durlstonpartners.com/jobs/ai-engineer/",
    "url": "https://durlstonpartners.com/jobs/ai-engineer/",
    "platform": "Career Site",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "5+",
    "degree": "Bachelor's or Master's in CS/AI/Engineering",
    "salary": "Up to $250K USD (tax-free UAE equivalent)",
    "required_skills": [
        "Foundational model research: language, vision, multimodal, structured data",
        "Large-scale training experiments and model evaluation",
        "Strong Python, PyTorch, JAX or TensorFlow",
        "Experience with distributed training and GPU clusters",
        "Model evaluation, benchmarking, and error analysis",
        "Research engineering: turning research prototypes into production systems",
        "Strong mathematical fundamentals: linear algebra, probability, statistics",
        "Published research or strong portfolio in AI/ML",
        "Excellent communication and scientific writing"
    ],
    "full_jd": """Durlston Partners is seeking an AI Engineer to join our research team in Abu Dhabi. You will work on foundational model research spanning language, vision, multimodal, and structured data domains.

The role involves designing and running large-scale training experiments, evaluating model performance, and turning research prototypes into deployed systems.

Responsibilities:
- Design and execute large-scale training experiments for foundational models
- Evaluate model performance across language, vision, multimodal, and structured data tasks
- Build and improve training infrastructure and experiment tracking
- Turn research prototypes into production-ready systems
- Conduct error analysis and drive model improvements
- Collaborate with researchers and engineers across the team
- Publish findings and contribute to the research community

Requirements:
- 5+ years of experience in AI/ML engineering or research
- Strong background in foundational model research
- Proficiency in Python, PyTorch, JAX, or TensorFlow
- Experience with distributed training and GPU clusters
- Strong mathematical foundations: linear algebra, probability, statistics
- Excellent problem-solving and communication skills
- Bachelor's or Master's degree in Computer Science, AI, or related field

Preferred:
- PhD in AI/ML or related field
- Published research at top venues (NeurIPS, ICML, ICLR, etc.)
- Experience with multimodal models (vision-language, etc.)
- Contributions to open-source AI projects"""
}

# 5. Enerflex — AI Engineer
# Source: AIJobsUAE (posted 17 Aug 2026, LIVE)
jds["Enerflex_AIEngineer"] = {
    "title": "AI Engineer",
    "company": "Enerflex",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://aijobsuae.ae/jobs/22376",
    "url": "https://aijobsuae.ae/jobs/22376",
    "platform": "AIJobsUAE",
    "posted_date": "2026-08-17",
    "type": "Full-time",
    "years_exp": "3+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "LLMs and Small Language Models (SLMs) for intelligent automation",
        "Decision support systems using AI",
        "Azure cloud platform and Microsoft Copilot ecosystem",
        "Python, ML frameworks",
        "Data pipeline development and integration",
        "Enterprise AI solution design and deployment",
        "Industrial/oil & gas domain knowledge preferred",
        "Strong problem-solving and analytical skills"
    ],
    "full_jd": """Enerflex is seeking an AI Engineer to join our team in Abu Dhabi. You will design and implement AI solutions leveraging LLMs and Small Language Models for intelligent automation and decision support across our industrial operations.

Responsibilities:
- Design and develop AI solutions using LLMs and SLMs for automation and decision support
- Integrate AI capabilities into enterprise systems and workflows
- Work with Azure cloud platform and Microsoft Copilot ecosystem
- Build data pipelines for AI model training and inference
- Collaborate with engineering and operations teams to identify AI opportunities
- Deploy and monitor AI solutions in production
- Stay current with AI/ML advancements and evaluate new technologies

Requirements:
- 3+ years of experience in AI/ML engineering
- Strong experience with LLMs and SLMs for intelligent automation
- Proficiency in Python and ML frameworks
- Experience with Azure cloud and Microsoft Copilot
- Data pipeline development skills
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Experience in oil & gas, energy, or industrial sectors
- Knowledge of industrial automation and IoT
- Experience with enterprise integration patterns"""
}

# 6. DAMAC Group — Forward Deployed AI Engineer
# Source: LinkedIn + AIU.AE (posted 20 Jun 2026, LIVE)
jds["DAMAC_ForwardDeployedAIEngineer"] = {
    "title": "Forward Deployed AI Engineer",
    "company": "DAMAC Group",
    "location": "Dubai, UAE",
    "apply_url": "https://www.linkedin.com/jobs/view/4426475055/",
    "url": "https://www.linkedin.com/jobs/view/4426475055/",
    "platform": "LinkedIn",
    "posted_date": "2026-06-20",
    "type": "Full-time",
    "years_exp": "4+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Forward deployed: work directly inside business units across real estate, hospitality, sales, finance, operations",
        "AI engineering and GenAI/LLM solution development",
        "Python, LLM frameworks, RAG",
        "Translate business requirements into AI solutions",
        "Stakeholder management and client-facing communication",
        "Full-stack AI application development",
        "Data analysis and insight generation",
        "Agile delivery in fast-paced environment"
    ],
    "full_jd": """DAMAC Group is seeking a Forward Deployed AI Engineer to work directly inside our business units across real estate, hospitality, sales, finance, and operations.

In this role, you will be embedded with business teams to understand their challenges and translate them into AI-powered solutions using GenAI and LLMs.

Responsibilities:
- Work directly with business stakeholders to understand challenges and requirements
- Design and build AI solutions using GenAI, LLMs, and RAG
- Develop end-to-end AI applications from prototype to production
- Translate business needs into technical AI solutions
- Provide training and enablement to business users on AI tools
- Measure and report on AI solution impact and ROI
- Collaborate across multiple business units (real estate, hospitality, sales, finance, ops)

Requirements:
- 4+ years of experience in AI engineering or related field
- Strong experience with GenAI, LLMs, and RAG-based solutions
- Proficiency in Python and AI/ML frameworks
- Excellent communication and stakeholder management skills
- Client-facing and forward-deployed experience preferred
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Experience in real estate, hospitality, or property management
- Full-stack development skills
- Experience with enterprise digital transformation"""
}

# 7. Safe City Group — Senior Solo AI Engineer
# Source: LinkedIn + AIU.AE (posted 16 Sep 2026, LIVE)
jds["SafeCityGroup_SeniorAIEngineer"] = {
    "title": "Senior Solo AI Engineer (Python, RAG, Conversational and Voice AI)",
    "company": "Safe City Group",
    "location": "Dubai, UAE",
    "apply_url": "https://www.linkedin.com/jobs/view/4467260156/",
    "url": "https://www.linkedin.com/jobs/view/4467260156/",
    "platform": "LinkedIn",
    "posted_date": "2026-09-16",
    "type": "Full-time",
    "years_exp": "4+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Build Arabic and English chat and voice assistants for UAE government services",
        "RAG (Retrieval-Augmented Generation) systems",
        "GPU infrastructure and model deployment",
        "Voice AI: ASR (Automatic Speech Recognition), TTS (Text-to-Speech)",
        "Python, LLM frameworks, vector databases",
        "Conversational AI design and dialogue management",
        "Arabic NLP and bilingual (Arabic/English) systems",
        "Government sector and security/safety domain knowledge",
        "End-to-end ownership: design, build, deploy, maintain"
    ],
    "full_jd": """Safe City Group is seeking a Senior Solo AI Engineer to build Arabic and English chat and voice assistants for UAE government services.

This is a hands-on, end-to-end role where you will own the full lifecycle of AI assistant development — from design and training through deployment and maintenance.

Responsibilities:
- Build bilingual (Arabic/English) chat and voice assistants for government services
- Design and implement RAG systems for accurate, context-aware responses
- Work with GPU infrastructure for model training and deployment
- Develop ASR and TTS components for voice AI capabilities
- Design conversational flows and dialogue management systems
- Deploy and maintain AI assistants in production
- Ensure high accuracy and cultural appropriateness for UAE context

Requirements:
- 4+ years of experience in AI/ML engineering
- Strong Python skills and experience with LLM frameworks
- Experience building RAG systems with vector databases
- Voice AI experience: ASR, TTS, and conversational AI
- GPU infrastructure and model deployment experience
- Arabic NLP experience or bilingual capabilities
- Experience in government or security/safety domain
- Ability to work independently as a solo AI engineer

Preferred:
- Experience with Arabic language models and NLP
- Knowledge of UAE government services and processes
- Experience with voice biometrics and speaker recognition
- Background in public safety or smart city initiatives"""
}

# 8. Parsons Corporation — ITS Engineer AI & NLP
# Source: LinkedIn + AIU.AE (posted 16 Sep 2026, LIVE)
jds["Parsons_ITS_AINLP_Engineer"] = {
    "title": "ITS Engineer (AI & NLP)",
    "company": "Parsons Corporation",
    "location": "Dubai, UAE",
    "apply_url": "https://www.linkedin.com/jobs/view/4467987428",
    "url": "https://www.linkedin.com/jobs/view/4467987428",
    "platform": "LinkedIn",
    "posted_date": "2026-09-16",
    "type": "Full-time",
    "years_exp": "7+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Technical supervision of AI/ML/NLP/LLM/predictive analytics development and deployment",
        "Lead role reviewing FSDDs (Functional Specification Design Documents)",
        "Review AI solution architectures and data models",
        "AI governance plan review and compliance",
        "NLP, LLM, predictive analytics expertise",
        "Python, ML frameworks, NLP libraries",
        "System integration and enterprise architecture",
        "Strong documentation and technical writing skills",
        "Leadership and mentorship of engineering teams",
        "Security and defense / smart city domain knowledge"
    ],
    "full_jd": """Parsons Corporation is seeking an ITS Engineer specialising in AI & NLP to join our team in Dubai. This is a technical leadership role overseeing AI/ML/NLP/LLM and predictive analytics development and deployment for critical infrastructure and smart city projects.

Responsibilities:
- Provide technical supervision of AI/ML/NLP/LLM and predictive analytics development
- Lead review of Functional Specification Design Documents (FSSDs)
- Review and validate AI solution architectures and data models
- Review AI governance plans for compliance and best practices
- Guide engineering teams on AI/ML/NLP technical approaches
- Ensure solution quality, security, and alignment with requirements
- Collaborate with clients and stakeholders on AI strategy
- Mentor junior engineers and promote best practices

Requirements:
- 7+ years of experience in AI/ML/NLP engineering
- Strong expertise in NLP, LLMs, and predictive analytics
- Experience reviewing technical specifications and architectures
- Proficiency in Python and ML/NLP frameworks
- Understanding of AI governance, ethics, and compliance
- Excellent technical writing and documentation skills
- Leadership and mentorship experience
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Security, defense, or smart city domain experience
- Knowledge of critical infrastructure protection
- Experience with government or military clients
- Advanced degree in AI/NLP/Computer Science"""
}

# 9. SAP — Forward Deployed Application/ML Engineering Expert
# Source: Naukrigulf (LIVE)
jds["SAP_ForwardDeployedMLEngineer"] = {
    "title": "Forward Deployed Application/ML Engineering Expert",
    "company": "SAP",
    "location": "Dubai, UAE (Sharjah also)",
    "apply_url": "https://www.naukrigulf.com/forward-deployed-application-ml-engineering-expert-jobs-in-dubai-uae-in-sap-1-to-5-years-n-cd-10001044-jid-050826501034",
    "url": "https://www.naukrigulf.com/forward-deployed-application-ml-engineering-expert-jobs-in-dubai-uae-in-sap-1-to-5-years-n-cd-10001044-jid-050826501034",
    "platform": "Naukrigulf",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "1-5",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Design, build, and operate AI-native enterprise applications",
        "GenAI applications and LLM integration",
        "Python, LLMs, RAG pipelines",
        "Forward deployed: work with customers to understand needs and deliver solutions",
        "SAP enterprise platform and ecosystem knowledge",
        "Full-stack application development",
        "Cloud platforms and enterprise integration",
        "Problem-solving and customer-facing communication"
    ],
    "full_jd": """SAP is seeking a Forward Deployed Application/ML Engineering Expert to design, build, and operate AI-native enterprise applications for our customers in the UAE.

In this forward-deployed role, you will work directly with customers to understand their business needs and deliver AI-powered solutions using SAP's enterprise platform and GenAI capabilities.

Responsibilities:
- Design, build, and operate AI-native enterprise applications
- Develop GenAI applications and integrate LLMs into enterprise workflows
- Work directly with customers to understand requirements and deliver solutions
- Build RAG pipelines and AI-powered features
- Develop full-stack applications on SAP's platform
- Collaborate with product and engineering teams
- Provide technical guidance and best practices to customers

Requirements:
- 1-5 years of experience in software engineering, ML engineering, or application development
- Experience with GenAI applications and LLMs
- Proficiency in Python
- RAG pipeline and vector database experience
- Customer-facing and forward-deployed experience
- Cloud platform and enterprise integration knowledge
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- SAP platform or enterprise software experience
- Full-stack development skills
- Experience in enterprise AI transformation"""
}

# 10. Alpha Data (Client) — Senior AI/ML Engineer Azure
# Source: Naukrigulf (LIVE)
jds["AlphaData_SeniorAIMEngineer_Azure"] = {
    "title": "Senior AI/ML Engineer - Azure",
    "company": "Alpha Data (Client)",
    "location": "Dubai, UAE",
    "apply_url": "https://www.naukrigulf.com/senior-ai-ml-engineer-azure-jobs-in-dubai-uae-in-client-of-alpha-data-recruitment-7-to-10-years-n-cd-50000746-jid-310826501861",
    "url": "https://www.naukrigulf.com/senior-ai-ml-engineer-azure-jobs-in-dubai-uae-in-client-of-alpha-data-recruitment-7-to-10-years-n-cd-50000746-jid-310826501861",
    "platform": "Naukrigulf",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "7-10",
    "degree": "Bachelor's in CS/Engineering or related (Master's/PhD advantageous)",
    "salary": "Not specified",
    "required_skills": [
        "Azure AI services and Azure OpenAI",
        "AI assurance standards and governance",
        "AI Governance Board experience (preferred)",
        "Python, Java, or C++",
        "TensorFlow, PyTorch, Keras",
        "AWS, Azure, or GCP cloud platforms",
        "MLOps and production ML deployment",
        "Leadership and technical mentorship",
        "Enterprise AI solution design and delivery",
        "Strong communication and stakeholder management"
    ],
    "full_jd": """Alpha Data is recruiting a Senior AI/ML Engineer - Azure for a client in Dubai. You will design and deliver enterprise AI solutions on the Azure platform, with a strong emphasis on AI governance and assurance.

Responsibilities:
- Design and deliver enterprise AI/ML solutions on Azure
- Work with Azure AI services and Azure OpenAI
- Apply AI assurance standards and governance frameworks
- Develop and deploy ML models in production
- Provide technical leadership and mentorship
- Collaborate with stakeholders on AI strategy and roadmap
- Ensure solutions meet quality, security, and compliance standards

Requirements:
- 7-10 years of experience in AI/ML engineering
- Strong experience with Azure AI and Azure OpenAI
- Proficiency in Python, Java, or C++
- Experience with TensorFlow, PyTorch, Keras
- Cloud platform experience (AWS, Azure, GCP)
- MLOps and production deployment experience
- Understanding of AI governance and assurance
- Bachelor's degree in Computer Science, Engineering, or related (Master's/PhD advantageous)

Preferred:
- AI Governance Board or similar governance experience
- Enterprise AI transformation projects
- Leadership of engineering teams
- Experience in regulated industries"""
}

# 11. Connected Staf — AI/ML Engineer LLMs, AI Agents & Data Intelligence
# Source: Indeed search confirmed (LIVE)
jds["ConnectedStaf_AIMLEngineer"] = {
    "title": "AI/ML Engineer - LLMs, AI Agents & Data Intelligence",
    "company": "Connected Staf",
    "location": "Dubai, UAE",
    "apply_url": "https://ae.indeed.com/rc/clk?jk=5d4786e13cee53b3",
    "url": "https://ae.indeed.com/rc/clk?jk=5d4786e13cee53b3",
    "platform": "Indeed",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "3+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "LLMs and AI Agents development",
        "Data intelligence and analytics",
        "Python, PyTorch, Hugging Face Transformers",
        "OpenAI APIs and LLM integration",
        "RAG pipelines and vector databases",
        "Semantic search and knowledge retrieval",
        "Production ML deployment",
        "Data pipeline development",
        "Strong problem-solving and analytical skills"
    ],
    "full_jd": """Connected Staf is seeking an AI/ML Engineer specialising in LLMs, AI Agents, and Data Intelligence to join our team in Dubai.

You will design and build intelligent systems leveraging large language models, AI agents, and advanced data analytics to solve complex business problems.

Responsibilities:
- Design and develop LLM-based solutions and AI agents
- Build RAG pipelines and semantic search capabilities
- Integrate OpenAI APIs and other LLM providers
- Develop data intelligence and analytics solutions
- Build and maintain production ML pipelines
- Work with vector databases for knowledge retrieval
- Deploy and monitor ML systems in production

Requirements:
- 3+ years of experience in AI/ML engineering
- Strong experience with LLMs and AI agents
- Proficiency in Python, PyTorch, Hugging Face Transformers
- Experience with OpenAI APIs and LLM integration
- RAG and vector database experience
- Data pipeline and analytics skills
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Experience with multi-agent systems and orchestration
- Knowledge of enterprise data platforms
- Full-stack development capabilities"""
}

# 12. D4 Insight — Senior AI Engineer
# Source: Glassdoor + d4insight.com (LIVE)
jds["D4Insight_SeniorAIEngineer"] = {
    "title": "Senior AI Engineer",
    "company": "D4 Insight",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://www.d4insight.com/jobopening/senior-ai-engineer/",
    "url": "https://www.d4insight.com/jobopening/senior-ai-engineer/",
    "platform": "Career Site",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "7+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Design, build, and deploy enterprise-scale AI solutions",
        "Generative AI and Agentic AI",
        "Machine Learning pipelines and models",
        "RAG pipelines and intelligent agents",
        "Cloud-native AI architecture",
        "Python and ML frameworks",
        "Production AI deployment and MLOps",
        "Client-facing solution delivery",
        "Strategic AI consulting and roadmap development"
    ],
    "full_jd": """D4 Insight is seeking a Senior AI Engineer to design, build, and deploy enterprise-scale AI solutions for clients in Abu Dhabi.

You will work on production-ready AI applications including RAG pipelines, intelligent agents, and cloud-native AI systems.

Responsibilities:
- Design, build, and deploy enterprise-scale AI solutions
- Develop Generative AI and Agentic AI applications
- Build RAG pipelines and intelligent agent systems
- Design cloud-native AI architectures
- Deploy and maintain production AI systems
- Work with clients to understand requirements and deliver solutions
- Provide AI strategy and roadmap consulting
- Mentor junior team members

Requirements:
- 7+ years of experience in AI/ML engineering
- Strong experience with Generative AI and Agentic AI
- Expertise in RAG pipelines and intelligent agents
- Proficiency in Python and ML frameworks
- Cloud-native AI architecture experience
- Production deployment and MLOps skills
- Client-facing and consulting experience
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Experience with enterprise digital transformation
- Knowledge of MS Dynamics, Salesforce, or similar platforms
- Strategic AI consulting experience"""
}

# 13. Joveo — RAG Engineer (via Hire Feed)
# Source: LinkedIn confirmed (LIVE)
jds["Joveo_RAGEngineer"] = {
    "title": "RAG Engineer",
    "company": "Joveo",
    "location": "Remote (UAE)",
    "apply_url": "https://www.linkedin.com/jobs/view/4403828998/",
    "url": "https://www.linkedin.com/jobs/view/4403828998/",
    "platform": "LinkedIn",
    "posted_date": "2026-09-21",
    "type": "Full-time",
    "years_exp": "3+",
    "degree": "Bachelor's in CS/Engineering or related",
    "salary": "Not specified",
    "required_skills": [
        "Build RAG pipelines end-to-end",
        "Vector databases: Pinecone, Weaviate, pgvector, Qdrant",
        "LangChain, LlamaIndex, DSPy",
        "RAGAS evaluation framework",
        "Python, LLM APIs",
        "Document processing and chunking strategies",
        "Semantic search and retrieval optimization",
        "Production deployment of RAG systems",
        "Embedding models and fine-tuning"
    ],
    "full_jd": """Joveo is seeking a RAG Engineer to build and optimize retrieval-augmented generation pipelines. This is a remote role based in the UAE.

You will be responsible for designing, building, and optimizing RAG systems from end to end — from document ingestion and embedding to retrieval optimization and evaluation.

Responsibilities:
- Build RAG pipelines end-to-end: ingestion, chunking, embedding, retrieval, generation
- Work with vector databases: Pinecone, Weaviate, pgvector, Qdrant
- Use frameworks: LangChain, LlamaIndex, DSPy
- Evaluate RAG system performance using RAGAS and custom metrics
- Optimize retrieval quality: chunking strategies, hybrid search, reranking
- Deploy and monitor RAG systems in production
- Stay current with RAG research and best practices

Requirements:
- 3+ years of experience in ML/AI engineering
- Strong experience building RAG pipelines
- Proficiency with vector databases (Pinecone, Weaviate, pgvector, Qdrant)
- Experience with LangChain, LlamaIndex, DSPy
- Knowledge of RAGAS evaluation framework
- Python and LLM API experience
- Bachelor's degree in Computer Science, Engineering, or related field

Preferred:
- Experience with embedding model fine-tuning
- Knowledge of hybrid search (BM25 + dense)
- Experience with document understanding and OCR
- Background in search engineering or information retrieval"""
}

# ── Write all JD JSONs ────────────────────────────────────────────────────────
for folder_name, jd_data in jds.items():
    jd_path = JD_DIR / folder_name / "jd.json"
    jd_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jd_path, "w") as f:
        json.dump(jd_data, f, indent=2)
    print(f"WROTE: {jd_path} ({len(json.dumps(jd_data))} bytes)")

print(f"\nTotal JDs written: {len(jds)}")

# ── Verify all JDs have required keys ────────────────────────────────────────
required_keys = ["title", "company", "location", "apply_url", "url", "platform",
                 "posted_date", "type", "years_exp", "degree", "salary",
                 "required_skills", "full_jd", "primary_skill", "secondary_skills",
                 "extraction_source", "gaps", "match_details"]

missing_keys = []
for folder_name, jd_data in jds.items():
    for key in required_keys:
        if key not in jd_data:
            missing_keys.append(f"{folder_name}: missing '{key}'")

if missing_keys:
    print(f"\nMISSING KEYS ({len(missing_keys)}):")
    for m in missing_keys:
        print(f"  - {m}")
    sys.exit(1)
else:
    print("\nAll JDs have required keys. OK.")

# ── List all job folders and their JD status ─────────────────────────────────
print("\n=== All job folders JD status ===")
for folder in sorted(JD_DIR.iterdir()):
    if folder.is_dir():
        jd_file = folder / "jd.json"
        has_jd = jd_file.exists()
        status = f"jd.json ({jd_file.stat().st_size} bytes)" if has_jd else "MISSING jd.json"
        print(f"  {folder.name:45} | {status}")
