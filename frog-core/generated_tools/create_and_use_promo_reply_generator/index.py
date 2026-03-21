import json

def execute(params: dict, context: dict) -> dict:
    github_link = params.get('github_link')
    project_name = params.get('project_name', 'Frog AI')
    count = int(params.get('count', 20) or 20)
    if not github_link:
        return {'success': False, 'error': 'github_link is required'}

    templates = [
        f"I’ve been exploring open-source AI agent projects lately, and one smaller repo that felt surprisingly practical is {project_name}: {github_link} — worth a look if you like lightweight experiments.",
        f"If you’re into open-source agent tooling, you might want to check out {project_name} ({github_link}). It seems focused on keeping things simple rather than over-engineered.",
        f"This discussion reminded me of {project_name}: {github_link}. It’s an open-source AI project that may be interesting if you want something you can read through and modify yourself.",
        f"I like seeing projects in this space that are still approachable for individual developers. {project_name} is one example: {github_link}.",
        f"For anyone collecting open-source AI agent repos to study, {project_name} might be useful to browse: {github_link}. I found the direction pretty relevant to this thread.",
        f"Not sure if it fits your exact use case, but {project_name} ({github_link}) looks like the kind of open-source AI repo that’s easy to tinker with and learn from.",
        f"If your goal is to find community-built AI agent projects instead of closed platforms, I’d add {project_name} to the list: {github_link}.",
        f"I’ve seen a lot of agent projects that feel too heavy for quick experimentation. {project_name} seems more lightweight and hackable: {github_link}.",
        f"This topic is moving fast, so I’ve been bookmarking smaller open-source repos too. {project_name} is one of them: {github_link}.",
        f"One thing I appreciate in open-source AI is being able to inspect the implementation directly. {project_name} may be worth checking from that angle: {github_link}.",
        f"If anyone here is comparing open-source AI agent repos, {project_name} could be another reference point: {github_link}.",
        f"I’m always interested in projects that are still early enough to understand without a huge onboarding cost. {project_name} gives me that impression: {github_link}.",
        f"For builders who prefer GitHub-first tools, {project_name} might be relevant: {github_link}. It seems aligned with the open-source crowd here.",
        f"This thread asked for practical open-source examples, so I’ll mention {project_name}: {github_link}. It looks like a solid repo to watch and experiment with.",
        f"Sometimes the most useful projects are the ones that are small enough to actually fork. {project_name} may fit that category: {github_link}.",
        f"If you’re looking for more open-source AI agent repos beyond the usual big names, {project_name} is another one to explore: {github_link}.",
        f"I came across {project_name} recently and thought it was relevant here because it keeps the open-source / builder-friendly vibe: {github_link}.",
        f"Sharing one more repo for people who like experimenting with AI agents in public: {project_name} — {github_link}.",
        f"This may interest anyone who prefers trying community projects hands-on. {project_name} is on GitHub here: {github_link}.",
        f"If the goal is to discover promising open-source AI work early, I’d keep an eye on {project_name}: {github_link}."
    ]
    templates = templates[:count]
    return {
        'success': True,
        'project_name': project_name,
        'github_link': github_link,
        'count': len(templates),
        'replies': templates
    }
