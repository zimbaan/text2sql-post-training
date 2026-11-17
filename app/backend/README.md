# NL2SQL Agent

A production-ready **FastAPI** application that converts natural language queries to SQL using a local **Ollama** model or hosted **OpenRouter** models. Supports PostgreSQL, MySQL/MariaDB, and SQLite databases.

## Features

- 🔌 **Multi-Database Support**: Connect to PostgreSQL, MySQL/MariaDB, or SQLite
- 🤖 **NL→SQL Conversion**: Powered by local Ollama or hosted OpenRouter (OpenAI-compatible) models
- 🔒 **Safety First**: Built-in SQL safety checks, DDL/DML blocking, and row limits
- 📊 **Schema Introspection**: Automatic discovery of databases, schemas, tables, columns, PKs, and FKs
- 📈 **Visualization**: Generate relationship graphs for table dependencies
- 📥 **CSV Export**: Stream query results as CSV files
- 📝 **Query History**: Track last 50 queries per connection
- 🚀 **Production Ready**: CORS, GZip compression, comprehensive error handling, OpenAPI docs

## Prerequisites

- **Python 3.11+**
- **Ollama** installed and running (for local inference)
  - Install from [ollama.ai](https://ollama.ai)
  - Start Ollama server: `ollama serve`
  - Pull a model: `ollama pull llama3.1` (or `llama3.2:latest`)
- **OpenRouter API key** if using hosted inference (no local model needed)

## Installation

1. **Clone the repository** (or create the project structure)

2. **Install dependencies**:

   ```bash
   pip install -e ".[finetuned]"   # includes the post-trained text-to-SQL model
   # Without the local model:
   pip install -e .
   # For development:
   pip install -e ".[finetuned,dev]"
   ```

3. **Set up environment variables**:

   Create a `.env` file based on `.env.example`:

   ```bash
   APP_HOST=0.0.0.0
   APP_PORT=8000
   ALLOWED_ORIGINS=*
   LLM_PROVIDER=ollama # or openrouter
   DEFAULT_OLLAMA_MODEL=llama3.1
   OLLAMA_BASE_URL=http://localhost:11434
   OPENROUTER_API_KEY=your_key_here
   OPENROUTER_MODEL=openrouter/llama-3.1-8b-instruct
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   EXECUTION_SAFE_MODE=true
   QUERY_ROW_LIMIT=1000
   QUERY_TIMEOUT_SECONDS=30
   CONNECTION_EXPIRY_MINUTES=60
   ```

### Using OpenRouter (hosted, no local model)

1. Set `LLM_PROVIDER=openrouter` in `.env`.
2. Add your `OPENROUTER_API_KEY` and (optionally) override `OPENROUTER_MODEL`.
3. Start the app as usual; Ollama is not required when using OpenRouter.

## Post-trained text-to-SQL model

With the `finetuned` extra installed, the backend also serves `text2sql-qwen-0.5b-dpo`: Qwen2.5-Coder-0.5B-Instruct
plus the LoRA adapter trained in this repo (SFT, then DPO on execution-verified pairs; see the root README for
results). It runs in-process on CPU or GPU, needs no Ollama or API key, and is listed first by `GET /nlq/models`.

- Select it per request with `"model": "text2sql-qwen-0.5b-dpo"` in `POST /nlq/{connection_id}` (the UI's model
  picker does this). Requests without `model` use the provider's default model.
- It is prompted exactly as in training: the `CREATE TABLE` statements of the tables in scope, then the question.
  It returns plain SQL, which goes through the same safety checks and row limit as other models.
- Settings: `FINETUNED_ENABLED`, `FINETUNED_MODEL_NAME`, `FINETUNED_BASE_MODEL`, `FINETUNED_ADAPTER_PATH`
  (defaults to `<repo>/models/text2sql-qwen-dpo`) and `FINETUNED_PRELOAD` (load at startup, default on).

## Running the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use Python directly:

```bash
python -m app.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Connection Management

#### Create Connection
```bash
curl -X POST "http://localhost:8000/connect" \
  -H "Content-Type: application/json" \
  -d '{
    "dialect": "postgresql",
    "username": "myuser",
    "password": "mypassword",
    "host": "localhost",
    "port": 5432,
    "database": "mydb"
  }'
```

Response:
```json
{
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "databases": ["mydb"],
  "default_database": "mydb",
  "capabilities": {"readOnly": true, "dialect": "postgresql"}
}
```

#### Close Connection
```bash
curl -X DELETE "http://localhost:8000/connect/{connection_id}"
```

### Schema Introspection

#### Get All Schemas and Tables
```bash
curl "http://localhost:8000/schemas/{connection_id}"
```

#### Get Specific Tables
```bash
curl "http://localhost:8000/schemas/{connection_id}/tables?tables=orders,customers&schema=public"
```

### Natural Language Queries

#### Execute NL Query
```bash
curl -X POST "http://localhost:8000/nlq/{connection_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Show me top 10 customers by revenue last quarter",
    "database": "mydb",
    "schema": "public",
    "table_scope": ["orders", "order_items", "customers"],
    "allow_modification": false,
    "return_sql_only": false
  }'
```

Response:
```json
{
  "sql": "SELECT c.customer_id, c.name, SUM(oi.quantity * oi.price) as revenue ... LIMIT 10",
  "columns": ["customer_id", "name", "revenue"],
  "rows": [[1, "Alice", 12345.67], ...],
  "row_count": 10,
  "confidence": 0.9,
  "warnings": [],
  "elapsed_ms": 125.5
}
```

#### Explain SQL (Without Execution)
```bash
curl -X POST "http://localhost:8000/nlq/explain/{connection_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Count orders by status",
    "database": "mydb"
  }'
```

#### List Available Models
```bash
curl "http://localhost:8000/nlq/models"
```

#### Get Query History
```bash
curl "http://localhost:8000/nlq/history/{connection_id}"
```

### Visualization

#### Generate Relationship Graph
```bash
curl -X POST "http://localhost:8000/visualize/{connection_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "tables": ["orders", "customers", "order_items"],
    "schema": "public"
  }'
```

Response:
```json
{
  "nodes": [
    {"id": "orders", "label": "orders"},
    {"id": "customers", "label": "customers"}
  ],
  "edges": [
    {"source": "orders", "target": "customers", "label": "orders.customer_id → customers.id"}
  ]
}
```

### CSV Export

#### Export Query Results
```bash
curl -X POST "http://localhost:8000/export/csv/{connection_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM customers LIMIT 100",
    "filename": "customers.csv"
  }' \
  --output customers.csv
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Server host |
| `APP_PORT` | `8000` | Server port |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `LLM_PROVIDER` | `ollama` | `ollama` (local) or `openrouter` / `openai` (hosted) |
| `DEFAULT_OLLAMA_MODEL` | `llama3.1` | Default Ollama model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENROUTER_API_KEY` | _none_ | API key for OpenRouter (required when `LLM_PROVIDER=openrouter`) |
| `OPENROUTER_MODEL` | `openrouter/llama-3.1-8b-instruct` | Default OpenRouter model |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter base URL |
| `EXECUTION_SAFE_MODE` | `true` | Block DDL/DML operations |
| `QUERY_ROW_LIMIT` | `1000` | Maximum rows per query |
| `QUERY_TIMEOUT_SECONDS` | `30` | Query execution timeout |
| `CONNECTION_EXPIRY_MINUTES` | `60` | Connection cache expiry time |

### Database Connection

Database credentials are provided via the `/connect` endpoint and stored in memory with 60-minute expiry. Connections are automatically cleaned up when expired.

**Supported Dialects:**
- `postgresql` / `postgres` - PostgreSQL database
- `mysql` / `mariadb` - MySQL/MariaDB database
- `sqlite` - SQLite database (file path or `:memory:`)

## Safety Features

1. **SQL Validation**: All queries are validated before execution
2. **DDL/DML Blocking**: When `EXECUTION_SAFE_MODE=true`, CREATE/ALTER/DROP/INSERT/UPDATE/DELETE are blocked
3. **Row Limits**: Automatic `LIMIT` enforcement for SELECT queries
4. **Wildcard Detection**: Warnings for `SELECT *` on large tables
5. **Parameterization**: Query parameters are properly handled

## Testing

Run tests with pytest:

```bash
pytest tests/
```

With coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Project Structure

```
app/
  main.py                 # FastAPI application entry point
  core/
    config.py            # Configuration management
    llm.py               # LLM clients (Ollama/OpenRouter)
    sql_safe.py          # SQL safety checks
  db/
    manager.py           # Connection management
    introspect.py        # Schema introspection
  services/
    nl2sql.py            # NL→SQL service
    visualize.py         # Visualization service
  routers/
    connection.py        # Connection endpoints
    schemas.py           # Schema endpoints
    nlq.py               # NLQ endpoints
    visual.py            # Visualization endpoints
    export.py            # Export endpoints
  models/
    dtos.py              # Pydantic models
  utils/
    csv.py               # CSV utilities
tests/
  test_sql_safe.py       # SQL safety tests
  test_csv.py            # CSV tests
  test_llm.py            # LLM client tests
README.md
pyproject.toml
.env.example
```

## Limitations

- Connections are stored **in memory only** (no persistence)
- Query history is **ephemeral** (last 50 queries per connection)
- SQL parsing is heuristic-based (not a full SQL parser)
- Large result sets are limited by `QUERY_ROW_LIMIT`

## Troubleshooting

### Ollama Connection Error

Ensure Ollama is running:
```bash
ollama serve
```

Check available models:
```bash
ollama list
```

### OpenRouter Connection Error

- Verify `OPENROUTER_API_KEY` is set and valid.
- Ensure `OPENROUTER_BASE_URL` is reachable (`https://openrouter.ai/api/v1` by default).
- Confirm the chosen `OPENROUTER_MODEL` is available to your account.

### Database Connection Failed

- Verify database credentials
- Check network connectivity
- Ensure database server is running
- For PostgreSQL, check `pg_hba.conf` settings

### SQL Generation Issues

- Ensure schema introspection succeeded
- Check that table names in `table_scope` exist
- Review LLM reasoning in response for hints

## License

This project is provided as-is for educational and development purposes.

## Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- Type hints are included
- Docstrings are provided for public functions

