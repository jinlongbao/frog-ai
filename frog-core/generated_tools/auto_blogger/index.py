import os, subprocess, json
from pathlib import Path

def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / '.git').exists() or (p / 'README.md').exists():
            return p
    for p in cur.rglob('README.md'):
        if p.is_file():
            root = p.parent
            if (root / '.git').exists() or (root / '.git').is_dir() or root != start:
                return root
    return cur

def _read_readme_intro(readme_path: Path, max_lines: int = 20) -> str:
    if not readme_path.exists():
        return 'README.md not found.'
    text = readme_path.read_text(encoding='utf-8', errors='ignore')
    lines = [line.strip() for line in text.splitlines()]
    cleaned = []
    for line in lines:
        if not line:
            if cleaned:
                cleaned.append('')
            continue
        if line.startswith('![') or line.startswith('<img'):
            continue
        cleaned.append(line)
        if len(cleaned) >= max_lines:
            break
    intro = '\n'.join(cleaned).strip()
    return intro[:2000] if intro else 'README intro is empty.'

def _git_log(repo_root: Path):
    try:
        result = subprocess.run(
            ['git', 'log', '-n', '5', '--pretty=format:%s'],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        logs = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return logs
    except Exception as e:
        return [f'Failed to read git log: {e}']

def execute(params: dict, context: dict) -> dict:
    start = Path(os.getcwd())
    repo_root = _find_repo_root(start)
    readme_path = repo_root / 'README.md'
    intro = _read_readme_intro(readme_path)
    commits = _git_log(repo_root)
    combined = {
        'repo_root': str(repo_root),
        'readme_intro': intro,
        'latest_commit_subjects': commits,
        'packed_text': 'README Intro:\n' + intro + '\n\nLatest 5 Git Commits:\n' + '\n'.join(f'- {c}' for c in commits)
    }
    return {'status': 'success', 'data': combined}
