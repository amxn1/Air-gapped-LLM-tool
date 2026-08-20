# Verification Steps

This document provides steps to verify that the Offline LLM Assistant is working correctly.

## Prerequisites

- Docker and Docker Compose installed
- Ports 8000 (API), 3000 (Web), 5432 (PostgreSQL), 6333 (Qdrant) available

## Verification Steps

### 1. Start the Services

```bash
cd infrastructure/compose
docker-compose up -d
```

### 2. Wait for Services to be Ready

Wait approximately 30 seconds for all services to start up. You can check the logs:

```bash
docker-compose logs -f
```

### 3. Verify API Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "offline-llm-assistant",
  "version": "0.1.0"
}
```

### 4. Verify Database Initialization (Optional)

You can verify that the database initialized correctly by checking if the admin user exists:

```bash
# Connect to the PostgreSQL container
docker-compose exec db psql -U offline_llm -d offline_llm -c "\du"
```

You should see the admin user in the list of roles.

### 4. Verify Models Endpoint

```bash
curl http://localhost:8000/v1/models
```

Expected response (simplified):
```json
[
  {
    "id": "llama-7b-chat",
    "name": "Llama 2 7B Chat",
    "version": "2.0",
    "format": "GGUF",
    "quantization": "q4_0",
    "context_length": 4096,
    "model_profile": "chat",
    "status": "active"
  }
]
```

### 5. Test Chat Completion Endpoint

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-7b-chat",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": false
  }'
```

Expected response (simplified):
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "llama-7b-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This is a mock response from the offline LLM assistant."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

### 6. Test Summary Endpoint

```bash
curl -X POST http://localhost:8000/v1/summaries \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test document for summarization verification.",
    "summary_type": "structured"
  }'
```

Expected response (simplified):
```json
{
  "id": "generated-uuid-here",
  "summary": "This is a mock summary of the provided content.",
  "model_used": "llama-7b-chat",
  "created_at": "2026-08-14T21:45:00Z",
  "metadata": {
    "summary_type": "structured"
  }
}
```

### 7. Access the Web Interface

Open your web browser and navigate to: http://localhost:3000

You should see the Offline LLM Assistant chat interface.

### 8. Test Web Interface Functionality

1. Type a message in the input field (e.g., "Hello")
2. Click the "Send" button
3. Wait for the response to appear
4. Verify that you see both your message and the assistant's response

### 9. Run Unit Tests

#### Backend Tests
```bash
cd apps/api
pip install pytest pytest-asyncio
python -m pytest tests/
```

#### Frontend Tests
```bash
cd ../web
npm test
```

### 10. Stop Services

When finished, stop the services:
```bash
cd infrastructure/compose
docker-compose down
```

## Troubleshooting

### Services Not Starting
- Check Docker logs: `docker-compose logs`
- Verify port availability: `docker-compose ps`
- Ensure sufficient system resources (especially for llama.cpp)

### Connection Refused
- Verify services are running: `docker-compose ps`
- Check that you're using the correct ports
- Ensure Docker networking is working properly

### Test Failures
- Check that all dependencies are installed
- Verify test environment matches expectations
- Look at detailed error output for specific failures

## Next Steps After Verification

Once you've verified the basic setup works, you can proceed with:
1. Implementing actual llama.cpp integration
2. Adding authentication and RBAC
3. Building the document ingestion pipeline
4. Adding vector storage and retrieval capabilities