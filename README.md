# text2sql

Convert natural language queries to SQL statements using AI.

## Overview

**text2sql** is a Python-based tool that leverages language models to automatically generate SQL queries from natural language text. This makes it easier for users without SQL expertise to query databases using plain English.

## Features

- 🤖 AI-powered natural language to SQL conversion
- 📊 Support for multiple SQL dialects
- 🔧 Configurable database schema handling
- ⚡ Fast and efficient query generation
- 🛡️ Built-in query validation

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

```bash
git clone https://github.com/ZMW-DW/text2sql.git
cd text2sql
pip install -r requirements.txt
```

## Quick Start

```python
from text2sql import QueryGenerator

# Initialize the generator
generator = QueryGenerator()

# Convert natural language to SQL
query = generator.convert("Show me all customers from New York")
print(query)
# Output: SELECT * FROM customers WHERE city = 'New York'
```

## Usage

### Basic Usage

```python
from text2sql import QueryGenerator

generator = QueryGenerator()
sql_query = generator.convert("your natural language query here")
```

### Advanced Configuration

```python
from text2sql import QueryGenerator

generator = QueryGenerator(
    model="gpt-4",
    dialect="postgresql"
)

result = generator.convert("query text", schema="your_schema")
```

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
DATABASE_URL=your_database_url
```

## Project Structure

```
text2sql/
├── text2sql/
│   ├── __init__.py
│   ├── converter.py
│   └── ...
├── tests/
├── requirements.txt
├── README.md
└── LICENSE
```

## Testing

Run tests with:

```bash
pytest
```

## Documentation

For more detailed documentation, see [docs/](./docs/) directory.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or issues, please:
- Open an [Issue](https://github.com/ZMW-DW/text2sql/issues)
- Start a [Discussion](https://github.com/ZMW-DW/text2sql/discussions)
- Check existing documentation

## Acknowledgments

- Built with [OpenAI](https://openai.com/) or similar language models
- Inspired by the need to democratize database access

---

**Last Updated:** May 2026
