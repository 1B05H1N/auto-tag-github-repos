# Auto Tag GitHub Repos

This script downloads all your GitHub repositories, analyzes their code using OpenAI, and automatically updates their topics (tags) on GitHub based on the code content.

## Features
- Authenticates with GitHub and OpenAI
- Clones all your (non-fork) repositories
- Analyzes code to suggest relevant topics using GPT-4
- Updates topics for each repo via the GitHub API
- **NEW:** Optionally only process public repos or repos without tags (topics)

## Setup

### 1. Clone this repository or copy the script files

### 2. Create a `.env` file in the project directory:

```
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
```

- **GITHUB_TOKEN**: Needs `repo` scope for private repos and topic editing.
- **OPENAI_API_KEY**: Needs access to GPT-4.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the script

```bash
python auto_tag_github_repos.py [--only-public] [--only-untagged]
```

- `--only-public`: Only process public repositories (skip private repos)
- `--only-untagged`: Only process repositories that have no topics/tags set
- You can use both flags together to process only public, untagged repos

## Notes
- The script skips forked repositories by default.
- It only scans a sample of files per repo to stay within OpenAI prompt limits.
- Make sure you have `git` installed and available in your PATH.

## OpenAI API Cost Warning
- **Be very careful about your spend by selecting the correct model!** Each repo analysis sends code to OpenAI, which can add up quickly in API costs. Monitor your usage and set limits as needed. I wasted money testing by using an expensive model.
- You can check your OpenAI usage and billing at: [OpenAI Billing Overview](https://platform.openai.com/settings/organization/billing/overview)

## Security
- Never share your `.env` file or API keys.
- The script embeds your GitHub token in the clone URL for non-interactive cloning.

## References
- [GitHub API: Replace all repository topics](https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#replace-all-repository-topics)

## License
MIT 