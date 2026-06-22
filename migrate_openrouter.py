import glob
import os

agent_dir = os.path.join('backend', 'agents')
agent_files = glob.glob(os.path.join(agent_dir, '*.py'))

for file_path in agent_files:
    basename = os.path.basename(file_path)
    if basename == '__init__.py':
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace imports
    content = content.replace(
        'from langchain_google_genai import ChatGoogleGenerativeAI',
        'from langchain_openai import ChatOpenAI'
    )
    
    # Replace env var names
    content = content.replace(
        'os.getenv("GOOGLE_API_KEY", "")',
        'os.getenv("OPENROUTER_API_KEY", "")'
    )
    content = content.replace(
        'os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")',
        'os.getenv("OPENROUTER_MODEL", "qwen/qwen3-8b")'
    )
    
    # Replace class instantiation
    content = content.replace('ChatGoogleGenerativeAI(', 'ChatOpenAI(')
    content = content.replace('google_api_key=self.api_key,', 'api_key=self.api_key,')
    
    # Add base_url for OpenRouter — find "temperature=" line and add base_url before it
    content = content.replace(
        'api_key=self.api_key,\n            model=self.model,\n            temperature=',
        'api_key=self.api_key,\n            model=self.model,\n            base_url="https://openrouter.ai/api/v1",\n            temperature='
    )
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated: {basename}')
    else:
        print(f'No changes: {basename}')

print('Migration to OpenRouter complete.')
