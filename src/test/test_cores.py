import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.prompts import SYSTEM_PROMPT
from src.middleware.handler import prepend_system_prompt

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_prepend_system_prompt_to_empty_messages():
    original_messages = [{"role": "user", "content": "Extract data from this receipt"}]
    modified_messages = prepend_system_prompt(original_messages)
    
    assert len(modified_messages) == 2
    assert modified_messages[0]["role"] == "system"
    assert modified_messages[0]["content"] == SYSTEM_PROMPT
    assert modified_messages[1]["content"] == "Extract data from this receipt"

def test_prepend_system_prompt_overrides_existing_system():
    original_messages = [
        {"role": "system", "content": "Testing the systemn"},
        {"role": "user", "content": "Hello"}
    ]
    
    modified_messages = prepend_system_prompt(original_messages)
    
    assert modified_messages[0]["role"] == "system"
    assert modified_messages[0]["content"].startswith(SYSTEM_PROMPT)