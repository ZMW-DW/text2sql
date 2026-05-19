# text2sql

Convert natural language queries to SQL statements using AI with LangGraph agent workflow.

## Overview

**text2sql** is a FastAPI-based tool that leverages language models and LangGraph to automatically generate, validate, and refine SQL queries from natural language text. It provides an intelligent SQL generation pipeline with iterative query refinement, result visualization, and detailed SQL analysis.

## Features

- 🤖 AI-powered natural language to SQL conversion using LLM
- 🔄 Iterative SQL query refinement with validation feedback loop
- 📊 Support for multiple SQL dialects (MySQL, PostgreSQL, SQLite, Oracle, DM)
- 🔍 Vector-based table retrieval using Milvus for relevant schema selection
- 📈 Automatic SQL result visualization with Mermaid diagrams
- 📝 SQL query reasoning and analysis
- ⚡ Batch inference support for multiple queries
- 🌊 Streaming response for real-time query generation updates
- 🔐 Redis-based session management and result caching
- 🛡️ Input validation and verification

## Architecture

### Core Components

- **SQLAgent**: LangGraph-based agent implementing agentic SQL generation workflow
  - `start`: Receives user question and initializes agent state
  - `retrieve`: Retrieves relevant tables using vector retrieval
  - `write`: Generates initial SQL query
  - `execute`: Executes query against database
  - `determine`: Validates query correctness
  - `rewrite`: Refines query based on feedback
  - `finish`: Generates visualizations and SQL analysis

- **FastAPI Server**: RESTful API for query generation and batch processing
  - `/stream_get_sql`: Streaming endpoint for interactive SQL generation
  - `/excel_task`: Batch inference for multiple queries
  - `/get_table`: Retrieve cached results from Redis

- **Database Abstraction**: 
  - `SQL_client`: Database connection and execution
  - `LocalDBInformation`: Schema management and examples
  - Support for multiple database dialects

- **Vector Retrieval**: 
  - `MilvusRetriever`: Vector store for table/schema retrieval
  - Support for local embeddings (HuggingFace) or web embeddings (OpenAI)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Redis server (for session management)
- Milvus vector database (for table retrieval)
- LLM API access (OpenAI or compatible)

### Setup

```bash
git clone https://github.com/ZMW-DW/text2sql.git
cd text2sql
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_MODEL_NAME=your_model_name
LLM_MODEL_PROVIDER=openai
LLM_MODEL_BASE_URL=https://api.openai.com/v1
LLM_MODEL_KEY=your_api_key

# Embedding Configuration
EMBEDDING_MODEL_LOCAL=BAAI/bge-large-en-v1.5
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_MODEL_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL_API_KEY=your_api_key

# Database Configuration (in config.yaml)
# See config.yaml for DB_config settings

# Redis Configuration
REDIS_URL=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Storage Configuration
STORE_DIR=./store
TEMP_DIR=./temp
```

## Usage

### Quick Start - Running the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### 1. Stream SQL Generation

```bash
curl -X POST "http://localhost:8000/stream_get_sql" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "session_id": "session456",
    "task_id": "task789",
    "question": "How many different series and contents are listed in the TV Channel table?"
  }'
```

Response streams events with intermediate steps:
```
data: {"title": "用户输入", "type": "text", "content": "..."}
data: {"title": "检索相关内容", "type": "text", "content": "..."}
data: {"title": "SQL语句书写", "type": "sql", "content": "SELECT ..."}
data: {"title": "SQL执行结果", "type": "text", "content": "..."}
data: {"title": "SQL查询语句判断", "type": "text", "content": "..."}
data: {"title": "结果可视化", "type": "images", "content": {...}}
```

#### 2. Batch Excel Query

```bash
curl -X POST "http://localhost:8000/excel_task" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Excel Report",
    "head": ["total records", "average value", "category count"]
  }'
```

#### 3. Get Cached Results

```bash
curl -X GET "http://localhost:8000/get_table?user_id=user123&session_id=session456&task_id=task789"
```

### Python Usage

```python
from sql_agent import SQLAgent
from utils import DB_config

# Configure database
db_config = DB_config(
    dialect="mysql",
    db_name="your_db",
    user_name="user",
    db_pwd="password",
    db_host="localhost",
    port=3306
)

# Create agent
agent = SQLAgent(
    db_config=db_config,
    is_accelerate=False,
    is_sql_reasion=False
)

# Generate SQL from natural language
for item in agent(question="How many users are there?"):
    print(f"Node: {item['node']}, Update: {item['update']}")
```

## Project Structure

```
text2sql/
├── main.py                 # FastAPI application entry point
├── sql_agent.py            # LangGraph SQL agent implementation
├── config.yaml             # Database and application configuration
├── requirements.txt        # Python dependencies
├── utils/
│   ├── __init__.py
│   ├── sql_client.py       # Database connection and execution
│   ├── state.py            # LangGraph agent state definitions
│   ├── prompt.py           # LLM prompt templates
│   ├── retriever.py        # Milvus vector retriever for table selection
│   ├── match_sentence.py   # Semantic sentence matching
│   └── redis_client.py     # Redis client for caching
├── README.md
└── LICENSE
```

## Database Support

- **MySQL** with PyMySQL
- **PostgreSQL** with psycopg2
- **SQLite**
- **Oracle**
- **DM (达梦数据库)** with dmPython

## Agent Workflow

The SQL agent follows this workflow:

1. **Input Reception**: User question is received and initial state is set
2. **Table Retrieval**: Vector retriever finds relevant tables based on question
3. **SQL Writing**: LLM generates initial SQL query
4. **Query Execution**: Query is executed against the database
5. **Validation**: LLM validates query correctness and identifies issues
6. **Refinement Loop**: If validation fails, query is rewritten and loop repeats (max 3 turns)
7. **Finalization**: Once validated, visualizations and analysis are generated

## Configuration Files

### config.yaml

```yaml
DB:
  dialect: mysql
  db_name: your_database
  user_name: your_user
  db_pwd: your_password
  db_host: localhost
  port: 3306
```

## Environment Variables

Key environment variables required:

- `LLM_MODEL_NAME`: Language model name
- `LLM_MODEL_PROVIDER`: Provider (e.g., "openai")
- `LLM_MODEL_BASE_URL`: API base URL
- `LLM_MODEL_KEY`: API key
- `REDIS_URL`: Redis host
- `REDIS_PORT`: Redis port
- `REDIS_DB`: Redis database number
- `REDIS_PASSWORD`: Redis password
- `SERVER_HOST`: Server host
- `SERVER_PORT`: Server port
- `EMBEDDING_MODEL_LOCAL`: Local embedding model name
- `EMBEDDING_MODEL_PATH`: Path to embedding model
- `STORE_DIR`: Directory for storing vector databases
- `TEMP_DIR`: Temporary directory for processing

## Development

### Testing

```python
python sql_agent.py
```

This runs the main script which tests the agent with a sample question.

### Adding Custom Prompts

Modify prompts in `utils/prompt.py`:
- `WRITE_QUERY_PROMPT`: Initial SQL generation
- `CHECK_QUERY_PROMPT`: Query validation
- `REWRITE_QUERY_PROMPT`: Query refinement
- `SQL_RESULT_TO_MERMAID`: Result visualization
- `REASONS_SQL`: SQL analysis

## Performance Considerations

- **Acceleration Mode**: Enable with `is_accelerate=True` for parallel async processing
- **SQL Reasoning**: Enable with `is_sql_reasion=True` for detailed query analysis
- **Vector Retrieval**: Uses Milvus for fast table/schema matching
- **Batch Processing**: Supports concurrent inference on multiple queries

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or issues, please:
- Open an [Issue](https://github.com/ZMW-DW/text2sql/issues)
- Start a [Discussion](https://github.com/ZMW-DW/text2sql/discussions)

## Acknowledgments

- Built with [LangChain](https://python.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/)
- Powered by language models (OpenAI or compatible)
- Vector retrieval with [Milvus](https://milvus.io/)
- Session management with [Redis](https://redis.io/)

---

**Last Updated:** May 2026
