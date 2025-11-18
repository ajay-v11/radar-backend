"""
Test multi-model support with new AI models.
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print('=' * 70)
print('TESTING MULTI-MODEL SUPPORT')
print('=' * 70)

# Test 1: Default models (chatgpt, gemini)
print('\n[Test 1] Default models (chatgpt, gemini)...')
response = client.post('/analyze', json={
    'company_url': 'https://hellofresh.com',
    'company_name': 'HelloFresh',
    'company_description': 'Meal kit delivery service'
})

if response.status_code == 200:
    data = response.json()
    print(f'  ✓ Status: {response.status_code}')
    print(f'  ✓ Models tested: {list(data["model_results"]["by_model"].keys())}')
    print(f'  ✓ Visibility score: {data["visibility_score"]}%')
    print(f'  ✓ Total mentions: {data["total_mentions"]}')
else:
    print(f'  ✗ Failed with status: {response.status_code}')
    print(f'  Error: {response.json()}')

# Test 2: Custom models selection
print('\n[Test 2] Custom models (chatgpt, gemini, llama)...')
response = client.post('/analyze', json={
    'company_url': 'https://microsoft.com',
    'company_name': 'Microsoft',
    'company_description': 'Technology company',
    'models': ['chatgpt', 'gemini', 'llama']
})

if response.status_code == 200:
    data = response.json()
    print(f'  ✓ Status: {response.status_code}')
    print(f'  ✓ Models tested: {list(data["model_results"]["by_model"].keys())}')
    print(f'  ✓ Total queries: {data["total_queries"]}')
    print(f'  ✓ Visibility score: {data["visibility_score"]}%')
    
    # Show per-model breakdown
    print(f'\n  Per-model results:')
    for model, results in data["model_results"]["by_model"].items():
        print(f'    - {model}: {results.get("mentions", 0)} mentions, {results.get("mention_rate", 0)*100:.1f}% rate')
else:
    print(f'  ✗ Failed with status: {response.status_code}')
    print(f'  Error: {response.json()}')

# Test 3: All available models
print('\n[Test 3] All models (chatgpt, gemini, llama, mistral, qwen)...')
response = client.post('/analyze', json={
    'company_url': 'https://amazon.com',
    'company_name': 'Amazon',
    'company_description': 'E-commerce and cloud computing',
    'models': ['chatgpt', 'gemini', 'llama', 'mistral', 'qwen']
})

if response.status_code == 200:
    data = response.json()
    print(f'  ✓ Status: {response.status_code}')
    print(f'  ✓ Models tested: {list(data["model_results"]["by_model"].keys())}')
    print(f'  ✓ Visibility score: {data["visibility_score"]}%')
    
    # Show which models worked
    print(f'\n  Model status:')
    for model, results in data["model_results"]["by_model"].items():
        mentions = results.get("mentions", 0)
        total = results.get("total_responses", 0)
        status = "✓ Working" if total > 0 else "✗ Failed"
        print(f'    {status} {model}: {mentions}/{total} mentions')
else:
    print(f'  ✗ Failed with status: {response.status_code}')

print('\n' + '=' * 70)
print('MULTI-MODEL TESTING COMPLETE')
print('=' * 70)
