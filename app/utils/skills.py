"""
Curated skill dictionary used for extraction & matching.

Maps skill aliases -> canonical name, grouped by category.
Purely rule-based and transparent; users can always see WHY something matched.
"""

SKILL_DICT = {
    # Languages
    "python": "Python", "python3": "Python",
    "javascript": "JavaScript", "js": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript",
    "java": "Java", "c++": "C++", "cpp": "C++", "c#": "C#", "csharp": "C#",
    "golang": "Go", "go": "Go", "rust": "Rust", "ruby": "Ruby",
    "php": "PHP", "kotlin": "Kotlin", "swift": "Swift",
    "sql": "SQL", "bash": "Bash", "shell": "Bash", "r language": "R", "matlab": "MATLAB",
    "scala": "Scala", "dart": "Dart", "html": "HTML", "css": "CSS",

    # Web frameworks
    "django": "Django", "django rest framework": "Django REST Framework", "drf": "Django REST Framework",
    "flask": "Flask", "fastapi": "FastAPI", "spring": "Spring", "spring boot": "Spring Boot",
    "express": "Express.js", "expressjs": "Express.js", "node": "Node.js", "node.js": "Node.js", "nodejs": "Node.js",
    "react": "React", "reactjs": "React", "react.js": "React", "next.js": "Next.js", "nextjs": "Next.js",
    "vue": "Vue.js", "vuejs": "Vue.js", "angular": "Angular", "angularjs": "Angular",
    "laravel": "Laravel", "rails": "Ruby on Rails", "ruby on rails": "Ruby on Rails",

    # APIs / protocols
    "rest": "REST APIs", "rest api": "REST APIs", "rest apis": "REST APIs", "restful": "REST APIs",
    "restful api": "REST APIs", "restful apis": "REST APIs", "restful services": "REST APIs",
    "graphql": "GraphQL", "grpc": "gRPC", "soap": "SOAP", "websocket": "WebSockets", "websockets": "WebSockets",
    "api gateway": "API Gateway", "microservices": "Microservices",

    # Databases
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL",
    "sqlite": "SQLite", "mongodb": "MongoDB", "mongo": "MongoDB", "redis": "Redis",
    "elasticsearch": "Elasticsearch", "dynamodb": "DynamoDB", "cassandra": "Cassandra",
    "mariadb": "MariaDB", "oracle db": "Oracle", "mssql": "SQL Server", "sql server": "SQL Server",

    # Cloud & DevOps
    "aws": "AWS", "amazon web services": "AWS", "gcp": "GCP", "google cloud": "GCP",
    "azure": "Azure", "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "terraform": "Terraform", "jenkins": "Jenkins", "ci/cd": "CI/CD", "cicd": "CI/CD",
    "github actions": "GitHub Actions", "gitlab ci": "GitLab CI", "ansible": "Ansible",
    "linux": "Linux", "nginx": "Nginx", "apache": "Apache", "cloudformation": "CloudFormation",
    "lambda": "AWS Lambda", "aws lambda": "AWS Lambda", "ec2": "AWS EC2", "s3": "AWS S3",

    # Data / ML
    "pandas": "Pandas", "numpy": "NumPy", "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "keras": "Keras",
    "spark": "Apache Spark", "pyspark": "PySpark", "hadoop": "Hadoop", "kafka": "Kafka",
    "airflow": "Apache Airflow", "airflow apache": "Apache Airflow", "dbt": "dbt",
    "power bi": "Power BI", "tableau": "Tableau", "snowflake": "Snowflake", "bigquery": "BigQuery",
    "etl": "ETL", "machine learning": "Machine Learning", "deep learning": "Deep Learning",
    "nlp": "NLP", "opencv": "OpenCV", "nltk": "NLTK", "spacy": "spaCy",

    # Testing
    "pytest": "PyTest", "unittest": "Unittest", "jest": "Jest", "selenium": "Selenium",
    "cypress": "Cypress", "junit": "JUnit", "postman": "Postman", "playwright": "Playwright",

    # Tools / practice
    "git": "Git", "github": "GitHub", "gitlab": "GitLab", "jira": "Jira",
    "agile": "Agile", "scrum": "Scrum", "tdd": "TDD", "celery": "Celery",
    "rabbitmq": "RabbitMQ", "rabbit mq": "RabbitMQ", "sqs": "AWS SQS", "sns": "AWS SNS",
    "oauth": "OAuth", "jwt": "JWT", "firebase": "Firebase", "supabase": "Supabase",
    "heroku": "Heroku", "vercel": "Vercel", "prisma": "Prisma", "sqlalchemy": "SQLAlchemy",
    "hibernate": "Hibernate", "wordpress": "WordPress", "figma": "Figma",
}

SKILL_CATEGORY = {
    "Python": "Languages", "JavaScript": "Languages", "TypeScript": "Languages",
    "Java": "Languages", "C++": "Languages", "C#": "Languages", "Go": "Languages",
    "Rust": "Languages", "Ruby": "Languages", "PHP": "Languages", "Kotlin": "Languages",
    "Swift": "Languages", "SQL": "Languages", "Bash": "Languages", "R": "Languages",
    "MATLAB": "Languages", "Scala": "Languages", "Dart": "Languages",
    "HTML": "Languages", "CSS": "Languages",

    "Django": "Frameworks", "Django REST Framework": "Frameworks", "Flask": "Frameworks",
    "FastAPI": "Frameworks", "Spring": "Frameworks", "Spring Boot": "Frameworks",
    "Express.js": "Frameworks", "Node.js": "Frameworks", "React": "Frameworks",
    "Next.js": "Frameworks", "Vue.js": "Frameworks", "Angular": "Frameworks",
    "Laravel": "Frameworks", "Ruby on Rails": "Frameworks", "Hibernate": "Frameworks",
    "SQLAlchemy": "Frameworks",

    "REST APIs": "APIs & Architecture", "GraphQL": "APIs & Architecture",
    "gRPC": "APIs & Architecture", "SOAP": "APIs & Architecture",
    "WebSockets": "APIs & Architecture", "API Gateway": "APIs & Architecture",
    "Microservices": "APIs & Architecture", "OAuth": "APIs & Architecture", "JWT": "APIs & Architecture",

    "PostgreSQL": "Databases", "MySQL": "Databases", "SQLite": "Databases",
    "MongoDB": "Databases", "Redis": "Databases", "Elasticsearch": "Databases",
    "DynamoDB": "Databases", "Cassandra": "Databases", "MariaDB": "Databases",
    "Oracle": "Databases", "SQL Server": "Databases", "Prisma": "Databases",
    "Firebase": "Databases", "Supabase": "Databases", "Snowflake": "Databases",
    "BigQuery": "Databases",

    "AWS": "Cloud & DevOps", "GCP": "Cloud & DevOps", "Azure": "Cloud & DevOps",
    "Docker": "Cloud & DevOps", "Kubernetes": "Cloud & DevOps", "Terraform": "Cloud & DevOps",
    "Jenkins": "Cloud & DevOps", "CI/CD": "Cloud & DevOps", "GitHub Actions": "Cloud & DevOps",
    "GitLab CI": "Cloud & DevOps", "Ansible": "Cloud & DevOps", "Linux": "Cloud & DevOps",
    "Nginx": "Cloud & DevOps", "Apache": "Cloud & DevOps", "CloudFormation": "Cloud & DevOps",
    "AWS Lambda": "Cloud & DevOps", "AWS EC2": "Cloud & DevOps", "AWS S3": "Cloud & DevOps",
    "AWS SQS": "Cloud & DevOps", "AWS SNS": "Cloud & DevOps", "Heroku": "Cloud & DevOps",
    "Vercel": "Cloud & DevOps", "Celery": "Cloud & DevOps", "RabbitMQ": "Cloud & DevOps",

    "Pandas": "Data & ML", "NumPy": "Data & ML", "Scikit-learn": "Data & ML",
    "TensorFlow": "Data & ML", "PyTorch": "Data & ML", "Keras": "Data & ML",
    "Apache Spark": "Data & ML", "PySpark": "Data & ML", "Hadoop": "Data & ML",
    "Kafka": "Data & ML", "Apache Airflow": "Data & ML", "dbt": "Data & ML",
    "Power BI": "Data & ML", "Tableau": "Data & ML", "ETL": "Data & ML",
    "Machine Learning": "Data & ML", "Deep Learning": "Data & ML", "NLP": "Data & ML",
    "OpenCV": "Data & ML", "NLTK": "Data & ML", "spaCy": "Data & ML",

    "PyTest": "Testing & Tools", "Unittest": "Testing & Tools", "Jest": "Testing & Tools",
    "Selenium": "Testing & Tools", "Cypress": "Testing & Tools", "JUnit": "Testing & Tools",
    "Postman": "Testing & Tools", "Playwright": "Testing & Tools", "TDD": "Testing & Tools",
    "Git": "Testing & Tools", "GitHub": "Testing & Tools", "GitLab": "Testing & Tools",
    "Jira": "Testing & Tools", "Agile": "Testing & Tools", "Scrum": "Testing & Tools",
    "WordPress": "Testing & Tools", "Figma": "Testing & Tools",
}

SOFT_SKILL_KEYWORDS = {
    "communication": "Communication", "leadership": "Leadership", "teamwork": "Teamwork",
    "team player": "Teamwork", "collaboration": "Collaboration",
    "problem solving": "Problem Solving", "problem-solving": "Problem Solving",
    "critical thinking": "Critical Thinking", "time management": "Time Management",
    "adaptability": "Adaptability", "mentoring": "Mentoring", "ownership": "Ownership",
    "attention to detail": "Attention to Detail", "presentation": "Presentation",
    "stakeholder": "Stakeholder Management", "negotiation": "Negotiation",
    "self-starter": "Self-starter", "proactive": "Proactive", "creativity": "Creativity",
}

SECTION_ALIASES = {
    "experience": ["experience", "work experience", "professional experience",
                   "employment history", "work history", "professional background"],
    "education": ["education", "academic background", "academics", "qualifications",
                  "educational background", "academic qualifications"],
    "skills": ["skills", "technical skills", "skill set", "core skills",
               "technologies", "tech stack", "competencies", "key skills"],
    "projects": ["projects", "personal projects", "academic projects", "key projects",
                 "selected projects", "project work"],
    "certifications": ["certifications", "certificates", "licenses",
                       "courses and certifications", "courses", "training"],
    "summary": ["summary", "professional summary", "objective", "career objective",
                "profile", "about me", "about", "profile summary"],
    "achievements": ["achievements", "awards", "honors", "accomplishments", "honors & awards"],
}

CONTACT_PATTERNS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}",
    "linkedin": r"(?:https?://)?(?:www\.)?linkedin\.com/[A-Za-z0-9_/%.-]+",
    "github": r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+",
    "portfolio": r"(?:https?://)?(?:www\.)?[A-Za-z0-9-]+\.(?:io|dev|me|xyz|com)[^\s,]*",
}


def canon_skill(alias):
    """Return canonical skill name for an alias, or None."""
    return SKILL_DICT.get(alias.strip().lower())


def skill_category(canonical):
    return SKILL_CATEGORY.get(canonical, "Other / General")
