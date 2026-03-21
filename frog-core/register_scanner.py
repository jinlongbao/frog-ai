from tool_writer import tool_writer

code = """
import os
import ast

def execute(params, context):
    file_path = params.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return {"error": "File not found"}
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        tree = ast.parse(content)
        
        lines = len(content.splitlines())
        classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        functions = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
        docstrings = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module)) and ast.get_docstring(n)])
        
        score = 100
        issues = []
        
        if lines > 500:
            score -= 20
            issues.append(f"High line count ({lines}). Consider refactoring into modules.")
        
        if functions > 0 and (lines / functions) > 50:
             score -= 10
             issues.append("Functions are relatively long on average.")
             
        coverage = docstrings / (functions + classes + 1)
        if coverage < 0.5:
             score -= 15
             issues.append(f"Low docstring coverage ({coverage*100:.1f}%). Add more documentation.")
             
        return {
            "file": os.path.basename(file_path),
            "score": max(0, score),
            "stats": {
                "lines": lines,
                "functions": functions,
                "classes": classes,
                "docstring_coverage": f"{coverage*100:.1f}%"
            },
            "issues": issues
        }
    except Exception as e:
        return {"error": str(e)}
"""

params = {
    'type': 'object', 
    'properties': {
        'file_path': {'type': 'string', 'description': 'Absolute path to the python file to scan.'}
    }, 
    'required': ['file_path']
}

print(tool_writer.write_tool('code_quality_scanner', 'Analyzes Python files for quality and metrics.', code, params))
