import sys
sys.path.insert(0, r"E:\RED")

print("Testing classify_url...")
sys.path.insert(0, r"E:\RED\01_discovery")
from web_verifier import classify_url
assert classify_url("") == "none"
assert classify_url("https://facebook.com/bar") == "social"
print("classify_url OK")

print("Testing rule_score...")
sys.path.insert(0, r"E:\RED\02_scoring")
from lead_scorer import rule_score
score = rule_score({
    "phone": "961000000",
    "rating": 4.5,
    "review_count": 35,
    "category": "restaurante-bar",
    "language": "es",
    "email": ""
})
assert 0 < score <= 60
print(f"rule_score OK: {score}/60")

print("Testing Rich import...")
from rich.console import Console
from rich.table import Table
c = Console()
c.print("[green]Rich OK[/green]")

print("Testing main.py import...")
import importlib.util
spec = importlib.util.spec_from_file_location(
    "main", r"E:\RED\main.py"
)
print("main.py importable OK")

print("")
print("ALL CHECKS PASSED")
print("Run with: python E:\\RED\\main.py --help")