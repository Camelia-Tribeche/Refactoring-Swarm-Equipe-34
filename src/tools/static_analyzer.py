"""
static_analyzer.py - Interface avec Pylint
Analyse statique du code Python
"""
import subprocess
import json
from pathlib import Path
from typing import Tuple, List, Dict
import re
import sys

def run_pylint_on_file(file_path: str) -> Tuple[float, List[Dict]]:
    path = Path(file_path)
    
    if not path.exists():
        return 0.0, [{"error": f"Fichier {file_path} introuvable"}]
    
    try:
        # Appel PyLint pour récupérer le score (texte normal)
        result = subprocess.run(
            [sys.executable, "-m", "pylint", str(path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Score
        report = result.stdout + "\n" + result.stderr
        score = extract_score_from_output(report)
        if score is None:
            score = 0.0
        
        # Appel séparé pour JSON si nécessaire (issues)
        try:
            result_json = subprocess.run(
                [sys.executable, "-m", "pylint", str(path), "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            issues = json.loads(result_json.stdout)
        except Exception:
            issues = []

        formatted_issues = [
            {
                "type": issue.get("type", "unknown"),
                "line": issue.get("line", 0),
                "column": issue.get("column", 0),
                "message": issue.get("message", ""),
                "symbol": issue.get("symbol", ""),
                "message_id": issue.get("message-id", "")
            }
            for issue in issues
        ]
        
        return score, formatted_issues
    
    except Exception as e:
        return 0.0, [{"error": f"Erreur pylint: {str(e)}"}]


def extract_score_from_output(report: str) -> float:
    match = re.search(r"rated at (-?\d+(\.\d+)?)/10", report)
    if match:
        return float(match.group(1))
    return None


def run_pylint_on_directory(directory: str) -> Dict:
    """
    Exécute pylint sur tous les fichiers d'un répertoire
    
    Args:
        directory: Chemin du répertoire
        
    Returns:
        Dict avec les résultats agrégés
    """
    path = Path(directory)
    
    if not path.exists() or not path.is_dir():
        return {"error": f"{directory} n'est pas un répertoire valide"}
    
    python_files = list(path.rglob("*.py"))
    
    if not python_files:
        return {
            "average_score": 0.0,
            "files_analyzed": 0,
            "total_issues": 0
        }
    
    total_score = 0.0
    all_issues = []
    
    for py_file in python_files:
        if "__pycache__" in str(py_file):
            continue
        
        score, issues = run_pylint_on_file(str(py_file))
        total_score += score
        all_issues.extend(issues)
    
    files_count = len([f for f in python_files if "__pycache__" not in str(f)])
    
    return {
        "average_score": round(total_score / files_count, 2) if files_count > 0 else 0.0,
        "files_analyzed": files_count,
        "total_issues": len(all_issues),
        "issues": all_issues[:20]  # Top 20 issues
    }


def get_pylint_summary(file_path: str) -> str:
    """
    Retourne un résumé textuel de l'analyse pylint
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Résumé formaté
    """
    score, issues = run_pylint_on_file(file_path)
    
    summary = f"Pylint Score: {score}/10\n"
    summary += f"Issues détectés: {len(issues)}\n\n"
    
    if issues:
        summary += "Top 5 problèmes:\n"
        for i, issue in enumerate(issues[:5], 1):
            if "error" in issue:
                summary += f"{i}. {issue['error']}\n"
            else:
                summary += f"{i}. [{issue['type']}] Ligne {issue['line']}: {issue['message']}\n"
    
    return summary