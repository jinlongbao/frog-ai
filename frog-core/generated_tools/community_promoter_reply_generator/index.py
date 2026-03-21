def execute(params: dict, context: dict) -> dict:
    github_link = params.get('github_link', '').strip()
    project_name = params.get('project_name', 'Frog AI').strip() or 'Frog AI'
    count = int(params.get('count', 20))
    if not github_link:
        return {'success': False, 'error': 'github_link is required'}

    templates = {
        'reddit': [
            f"If you're comparing open-source AI agent projects, one practical shortcut is to study runnable repos instead of only reading theory posts. {project_name} may be worth a look for its tool orchestration approach: {github_link}",
            f"A good way to learn AI agents is to inspect smaller open-source implementations side by side. {project_name} could be a useful reference if you're exploring extensible agent workflows: {github_link}",
            f"A lot of agent discussions stay abstract. If you want a concrete repo to review for execution flow and plugin ideas, you can also check {project_name}: {github_link}",
            f"If your goal is more 'personal AI assistant' than just a chatbot wrapper, I'd compare projects by extensibility and task execution design. {project_name} seems relevant in that direction: {github_link}",
            f"One thing that helped me was looking at repos that are easier to read and fork. {project_name} might be useful to inspect if you're experimenting with autonomous agent patterns: {github_link}",
            f"Rather than asking for the single best framework, I'd shortlist a few repos and compare tradeoffs. {project_name} could be one of the examples worth reviewing: {github_link}",
            f"If you're building from scratch, it can help to keep one practical repo open while reading tutorials. {project_name} may give you some implementation ideas here: {github_link}"
        ],
        'hacker_news': [
            f"Interesting discussion. For readers who want an implementation-oriented reference point, {project_name} is another open-source repo that may be useful to inspect: {github_link}",
            f"One useful benchmark for these conversations is whether a repo is easy to extend with tools and custom workflows. {project_name} looks relevant from that angle: {github_link}",
            f"This is a good conceptual overview. If anyone wants to compare it with a runnable project, {project_name} might be worth reviewing as a practical example: {github_link}",
            f"I’d avoid framing this as one-size-fits-all. It probably makes more sense to compare repos by use case; {project_name} could be a reasonable addition to that comparison set: {github_link}",
            f"For people moving from theory to implementation, I usually find concrete repos more helpful than another architecture diagram. {project_name} may be a useful one to study: {github_link}",
            f"A practical way to evaluate agent projects is to inspect how they structure tools, execution loops, and extensibility. {project_name} appears relevant if that's what you're exploring: {github_link}"
        ],
        'blog_comments': [
            f"Great write-up. For readers who want to go one step further and inspect a working repository, {project_name} may be worth checking out as a practical reference: {github_link}",
            f"Thanks for sharing this. It pairs well with looking at a real open-source implementation; {project_name} could be helpful for people exploring agent workflows in practice: {github_link}",
            f"This article explains the concepts clearly. If anyone wants a code-level example to compare against, {project_name} might be useful to review: {github_link}",
            f"Really nice overview. A concrete repo can also help bridge the gap between idea and implementation, and {project_name} seems relevant there: {github_link}",
            f"Appreciate the post. For developers looking for a practical companion example, {project_name} could be another repo worth browsing: {github_link}",
            f"Helpful article. If readers are interested in seeing how similar ideas show up in an open-source project, {project_name} may be a good additional reference: {github_link}",
            f"Well explained. For anyone who learns best from runnable examples, {project_name} is another project that may be useful to inspect: {github_link}"
        ]
    }

    ordered = []
    for channel in ['reddit', 'hacker_news', 'blog_comments']:
        for text in templates[channel]:
            ordered.append({'channel': channel, 'reply': text})

    return {
        'success': True,
        'project_name': project_name,
        'github_link': github_link,
        'count': min(count, len(ordered)),
        'replies': ordered[:count]
    }
