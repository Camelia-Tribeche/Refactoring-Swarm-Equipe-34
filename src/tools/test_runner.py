"""
test_runner.py - Interface avec Pytest
Exécution des tests unitaires
"""
import subprocess
import json
import os
from pathlib import Path
from typing import Dict


def run_pytest_on_directory(directory: str, timeout: int = 60) -> Dict:
    """
    Exécute pytest sur un répertoire et retourne les résultats
    
    Args:
        directory: Chemin du répertoire contenant les tests
        timeout: Timeout en secondes (défaut: 60)
        
    Returns:
        Dict contenant :
        - passed_count: Nombre de tests réussis
        - failed_count: Nombre de tests échoués
        - total_count: Nombre total de tests
        - error_logs: Liste des erreurs
    """
    path = Path(directory)
    
    if not path.exists():
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [f"Le répertoire {directory} n'existe pas"]
        }
    
    # Fichier temporaire pour le rapport JSON
    report_file = Path("test_report.json")
    
    try:
        # Exécuter pytest avec rapport JSON
        cmd = [
            "pytest",
            str(path),
            "-v",  # Verbose
            "--tb=short",  # Traceback court
            f"--json-report",
            f"--json-report-file={report_file}",
            "--json-report-indent=2",
            "-o python_files=*.py"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        # Lire le rapport JSON si disponible
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
                
            
            # Extraire les statistiques
            summary = report_data.get("summary", {})
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            total = summary.get("total", 0)
            
            # Extraire les erreurs
            error_logs = []
            for test in report_data.get("tests", []):
                
                if test.get("outcome") == "failed":
                    error_logs.append({
                        "test": test.get("nodeid", "unknown"),
                        "message": test.get("call", {}).get("crash", {}).get("message", ""),
                        "traceback": test.get("call", {}).get("longrepr", "")[:500]  # Limiter
                    })
            
            # Nettoyer le fichier temporaire
            report_file.unlink()
            
            return {
                "passed_count": passed,
                "failed_count": failed,
                "total_count": total,
                "error_logs": error_logs,
                "execution_time": report_data.get("duration", 0)
            }
        
        else:
            # Fallback : parser la sortie standard
            return parse_pytest_output(result.stdout, result.stderr, result.returncode)
    
    except subprocess.TimeoutExpired:
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [f"Timeout après {timeout} secondes"]
        }
    
    except FileNotFoundError:
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": ["Pytest n'est pas installé. Exécutez: pip install pytest pytest-json-report"]
        }
    
    except Exception as e:
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [f"Erreur lors de l'exécution de pytest: {str(e)}"]
        }


def parse_pytest_output(stdout: str, stderr: str, returncode: int) -> Dict:
    """
    Parse la sortie texte de pytest (fallback si pas de JSON)
    
    Args:
        stdout: Sortie standard
        stderr: Sortie d'erreur
        returncode: Code de retour
        
    Returns:
        Dict avec les résultats
    """
    # Chercher la ligne de résumé (ex: "5 passed, 2 failed in 1.23s")
    passed = 0
    failed = 0
    
    output = stdout + stderr
    
    for line in output.split('\n'):
        line_lower = line.lower()
        
        if 'passed' in line_lower:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'passed' in part and i > 0:
                        passed = int(parts[i-1])
            except:
                pass
        
        if 'failed' in line_lower:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'failed' in part and i > 0:
                        failed = int(parts[i-1])
            except:
                pass
    
    # Si aucun test n'a été trouvé
    if passed == 0 and failed == 0:
        if returncode == 0:
            # Peut-être qu'il n'y a pas de tests
            return {
                "passed_count": 0,
                "failed_count": 0,
                "total_count": 0,
                "error_logs": ["Aucun test trouvé dans le répertoire"]
            }
        else:
            # Erreur d'exécution
            failed = 1
    
    total = passed + failed
    
    # Extraire les erreurs depuis stdout/stderr
    error_logs = []
    if failed > 0:
        error_logs.append(stderr[:500] if stderr else "Tests échoués (voir logs)")
    
    return {
        "passed_count": passed,
        "failed_count": failed,
        "total_count": total,
        "error_logs": error_logs
    }


def check_pytest_installed() -> bool:
    """
    Vérifie si pytest est installé
    
    Returns:
        True si pytest est disponible, False sinon
    """
    try:
        result = subprocess.run(
            ["pytest", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False