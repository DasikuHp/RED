import sys, ast, os

def get_functions(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        return [n.name for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef)]
    except Exception as e:
        return [f"ERROR: {e}"]

files = {
    "web_verifier": r"E:\RED\01_discovery\web_verifier.py",
    "lead_scorer":  r"E:\RED\02_scoring\lead_scorer.py",
}
for name, path in files.items():
    funcs = get_functions(path)
    print(f"{name}: {funcs}")
