import os
import requests
import openai
import tempfile
import subprocess
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
import re
import argparse

GITHUB_API = "https://api.github.com"

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Instantiate OpenAI client (new API)
client = OpenAI()

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# List of code file extensions to consider
CODE_EXTS = (
    '.py', '.js', '.ts', '.java', '.go', '.rb', '.cpp', '.c',
    '.cs', '.php', '.rs', '.swift', '.kt', '.scala', '.sh',
    '.pl', '.html', '.css'
)

def ensure_command(cmd):
    from shutil import which
    if which(cmd) is None:
        raise RuntimeError(f"Required command not found: {cmd}")

def list_repos(username: str) -> List[dict]:
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/user/repos?per_page=100&page={page}"
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return [repo for repo in repos if repo['owner']['login'].lower() == username.lower()]

def clone_repo(clone_url: str, dest: str) -> str:
    # git clone will refuse if dest exists; so clone into dest/<repo_name>
    repo_name = clone_url.rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
    target = os.path.join(dest, repo_name)
    subprocess.run(["git", "clone", "--depth", "1", clone_url, target], check=True)
    return target

def collect_code_snippets(repo_path: str, max_files=5, max_bytes=2048) -> str:
    code = []
    count = 0
    for root, dirs, files in os.walk(repo_path):
        # Skip unwanted directories
        for skip in ('node_modules', 'vendor', '__pycache__', '.git'):
            if skip in dirs:
                dirs.remove(skip)
        for file in files:
            if file.lower().endswith(CODE_EXTS):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        snippet = f.read(max_bytes)
                    code.append(f"# {file}\n{snippet}")
                    count += 1
                    if count >= max_files:
                        return '\n'.join(code)
                except Exception:
                    continue
    return '\n'.join(code)

def suggest_topics_with_openai(code_snippet: str) -> List[str]:
    prompt = (
        "Given the following code snippets from a GitHub repository, suggest 3-8 relevant GitHub topics (single words or short phrases) that best describe the repository. "
        "Return only a comma-separated list of topics, no explanations.\n\n"
        f"{code_snippet}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
        temperature=0.3,
    )
    content = response.choices[0].message.content.strip()
    return [t.strip() for t in content.split(',') if t.strip()]

def sanitize_topics(topics: List[str]) -> List[str]:
    clean = []
    for t in topics:
        t = t.strip().lower().replace(' ', '-')
        t = re.sub(r'[^a-z0-9-]', '', t)
        if t and len(t) <= 35:
            clean.append(t)
    return clean[:20]

def update_repo_topics(owner: str, repo: str, topics: List[str]):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/topics"
    topic_headers = {**HEADERS, "Accept": "application/vnd.github+json"}
    r = requests.put(url, headers=topic_headers, json={"names": topics})
    r.raise_for_status()
    print(f"Updated topics for {owner}/{repo}: {topics}")

def get_repo_topics(owner: str, repo: str) -> list:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/topics"
    topic_headers = {**HEADERS, "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=topic_headers)
    r.raise_for_status()
    return r.json().get("names", [])

def main():
    parser = argparse.ArgumentParser(description="Auto-tag GitHub repos with OpenAI.")
    parser.add_argument("--only-public", action="store_true", help="Only process public repositories.")
    parser.add_argument("--only-untagged", action="store_true", help="Only process repositories with no topics.")
    args = parser.parse_args()

    ensure_command("git")
    repos = list_repos(GITHUB_USERNAME)
    print(f"Found {len(repos)} repos.")
    for repo in repos:
        name = repo['name']
        # Optionally skip forks
        if repo.get('fork'):
            print(f" → Skipping forked repo: {name}")
            continue
        if args.only_public and repo.get('private', False):
            print(f" → Skipping private repo (only-public): {name}")
            continue
        if args.only_untagged:
            try:
                topics = get_repo_topics(GITHUB_USERNAME, name)
            except requests.HTTPError as e:
                print(f" → Error fetching topics for {name}: {e}")
                continue
            if topics:
                print(f" → Skipping repo with topics (only-untagged): {name}")
                continue
        print(f"\nProcessing {name}...")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Embed token in clone URL for non-interactive cloning
                clone_url = repo['clone_url'].replace(
                    'https://', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@')
                repo_dir = clone_repo(clone_url, tmpdir)
                code = collect_code_snippets(repo_dir)
                if not code:
                    print(" → No code found; skipping.")
                    continue
                topics = suggest_topics_with_openai(code)
                topics = sanitize_topics(topics)
                if topics:
                    update_repo_topics(GITHUB_USERNAME, name, topics)
                else:
                    print(" → No valid topics to update.")
            except subprocess.CalledProcessError as e:
                print(f" → Git error cloning {name}: {e}")
            except requests.HTTPError as e:
                print(f" → GitHub API error on {name}: {e}")
                print(f" → Response: {e.response.text}")
            except Exception as e:
                print(f" → Unexpected error on {name}: {e}")

if __name__ == "__main__":
    main() 