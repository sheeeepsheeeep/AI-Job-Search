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
        'from langchain_openai import ChatOpenAI',
        'from langchain_groq import ChatGroq'
    )
    
    # Replace env vars
    content = content.replace('OPENROUTER_API_KEY', 'GROQ_API_KEY')
    content = content.replace('OPENROUTER_MODEL', 'GROQ_MODEL')
    
    # Replace default model string if any
    content = content.replace('qwen/qwen3-8b', 'llama-3.1-8b-instant')
    content = content.replace('openrouter/free', 'llama-3.1-8b-instant')
    
    # Replace class instantiation
    content = content.replace('ChatOpenAI(', 'ChatGroq(')
    
    # Remove base_url lines
    content = content.replace('            base_url="https://openrouter.ai/api/v1",\n', '')
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated: {basename}')
    else:
        print(f'No changes: {basename}')

print('Migration to Groq complete.')
