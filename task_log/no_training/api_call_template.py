import requests
import json

# VLLM API endpoint
api_url = "http://10.1.1.15:11111/v1/chat/completions"
api_key = "qwen2_5_05"
model_name = "qwen2_5_05"

# Test message
test_message = "Hello, how are you?"

# Prepare the request payload
payload = {
    "model": model_name,
    "messages": [
        {
            "role": "user",
            "content": test_message
        }
    ],
    "max_tokens": 512,
    "temperature": 0.0
}

# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

try:
    # Make the request
    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("VLLM API Response:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Extract the generated text
        if "choices" in result and len(result["choices"]) > 0:
            generated_text = result["choices"][0]["message"]["content"]
            print(f"\nGenerated text: {generated_text}")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("Connection error: Make sure VLLM server is running on localhost:6379")
except Exception as e:
    print(f"Error: {e}")
