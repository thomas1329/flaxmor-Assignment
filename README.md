# Open WebUI + Middleware Stack

## Project Overview
This repository contains a containerized local development environment that integrates Open WebUI, a PostgreSQL database, and a custom FastAPI middleware proxy. 

The primary function of the middleware is to sit between the frontend (Open WebUI) and OpenAI's API. It intercepts incoming chat requests, dynamically injects a system prompt designed for structured data extraction, forwards the request to OpenAI, and streams the response back to the client.

The models that i have selected from openAI is gpt-4o-mini, gpt-4o

## Architecture & Design Decisions
The FastAPI middleware is built using a layered architecture to ensure separation of concerns, making the codebase maintainable and highly testable:

**`main.py`**: The application entry point. Handles app initialization, global exception handling, and CORS configurations.
**`router.py`**: Defines the API endpoints (`/v1/chat/completions`, `/v1/models`, `/health`).
**`controller.py`**: Acts as the orchestrator. It receives the validated request from the router, calls the necessary handlers, and formats the final response (or stream) for the client.
**`handler.py`**: Contains the core business logic, specifically the `prepend_system_prompt` function that inspects the message array and injects the extraction instructions.
**`config.py`**: Manages environment variables using Pydantic settings.

**Note on AI Usage:** I utilized AI coding assistants during this project primarily for scaffolding boilerplate configurations for openAI and troubleshooting and mantine clean Docker volume/pathing issues.

## Prerequisites & Setup
1. Clone the repository to your local machine.
2. Create a `.env` file in the root directory based on the following structure:
   ```env
   OPENAI_API_KEY=sk-your-actual-api-key
   OPENAI_BASE_URL=https://api.openai.com/v1
   UPSTREAM_TIMEOUT=60.0
   LOG_LEVEL=INFO
   ```
   *Important:* A valid OpenAI API key with active billing credits is required. If the account lacks credits, OpenAI will reject the request. The middleware is designed to handle this gracefully by catching the upstream failure, logging the issue, and returning a structured 429 error to the UI.

3. Start the stack using Docker Compose:
   ```bash
   docker-compose up --build
   ```

## How to Verify it Works
1. Once the containers are running, navigate to `http://localhost:3000` in your browser.
2. Create an initial account (the first account created automatically becomes the Admin).
3. **Model Sync:** If the model list appears empty, go to your Profile (bottom left) -> **Admin Panel** -> **Settings** -> **Connections**. Under the OpenAI API section, click the refresh button to verify the connection to the local middleware (`http://middleware:8000/v1`).
4. **Test the Extraction:** Start a new chat, select a model (e.g., `gpt-4o`), and paste unstructured text (like a messy receipt or a raw email). The system will automatically return a cleanly formatted JSON block containing the extracted entities and any flagged uncertainties. 

## Testing
The middleware includes a suite of unit tests built with `pytest` to verify the core logic without needing to run the full UI/database stack. 

To run the tests inside the middleware container, execute the following command from the root directory:
```bash
docker-compose run --rm middleware bash -c "PYTHONPATH=/app pytest src/ -v"
```

**Test Coverage:**
*   **Health Check Endpoint:** Verifies the API is up and returning a 200 status code.
*   **Prompt Injection:** Ensures the system prompt is correctly inserted at the beginning of a standard user message array.
*   **Prompt Override:** Verifies that if an incoming request already contains a different system prompt, the middleware overrides/prepends the required extraction prompt to enforce the business rules.