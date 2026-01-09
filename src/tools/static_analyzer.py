"""
static_analyzer.py - Interface avec Pylint
Analyse statique du code Python
"""
import subprocess
import json
from pathlib import Path
from typing import Tuple, List, Dict


def run_pylint_on_file(file_path: str) -> Tuple[float, List[Dict]]:
    """
    Exécute pylint sur un fichier et retourne le score + les issues
    
    Args:
        file_path: Chemin du fichier à analyser
        
    Returns:
        Tuple (score, liste_issues)
        - score: Note sur 10
        - liste_issues: Liste des problèmes détectés
    """
    path = Path(file_path)
    
    if not path.exists():
        return 0.0, [{"error": f"Fichier {file_path} introuvable"}]
    
    try:
        # Exécuter pylint avec format JSON
        result = subprocess.run(
            ["pylint", str(path), "--output-format=json", "--score=yes"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parser les résultats JSON
        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            issues = []
        
        # Extraire le score depuis stderr (où pylint écrit le score)
        score = extract_score_from_output(result.stderr)
        
        # Formater les issues
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
        
    except subprocess.TimeoutExpired:
        return 0.0, [{"error": "Timeout lors de l'exécution de pylint"}]
    except FileNotFoundError:
        return 0.0, [{"error": "Pylint n'est pas installé. Exécutez: pip install pylint"}]
    except Exception as e:
        return 0.0, [{"error": f"Erreur pylint: {str(e)}"}]


def extract_score_from_output(output: str) -> float:
    """
    Extrait le score depuis la sortie pylint
    
    Args:
        output: Sortie texte de pylint
        
    Returns:
        Score sur 10
    """
    try:
        # Chercher la ligne contenant "rated at"
        for line in output.split('\n'):
            if 'rated at' in line.lower():
                # Format: "Your code has been rated at 7.50/10"
                parts = line.split('rated at')
                if len(parts) > 1:
                    score_part = parts[1].split('/')[0].strip()
                    return float(score_part)
    except:
        pass
    
    # Score par défaut si extraction échoue
    return 5.0


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