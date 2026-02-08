"""
test_runner.py - Interface avec Pytest (VERSION ULTIME)
Extraction COMPLÈTE des erreurs sans troncature
"""
import subprocess
import json
import os
import re
from pathlib import Path
from typing import Dict


def run_pytest_on_directory(directory: str, timeout: int = 60) -> Dict:
    """
    Exécute pytest avec extraction COMPLÈTE des erreurs
    
    Args:
        directory: Chemin du répertoire contenant les tests
        timeout: Timeout en secondes
        
    Returns:
        Dict avec passed_count, failed_count, total_count, error_logs détaillés
    """
    path = Path(directory)
    
    if not path.exists():
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [{
                "test": "directory_check",
                "message": f"Le répertoire {directory} n'existe pas",
                "traceback": ""
            }]
        }
    
    # Fichier JSON temporaire
    report_file = Path("test_report.json")
    
    try:
        # Exécuter pytest avec verbose et JSON
        cmd = [
            "pytest",
            str(path),
            "-v",
            "--tb=short",
            f"--json-report",
            f"--json-report-file={report_file}",
            "--json-report-indent=2",
            "-o", "python_files=*.py"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        # Lire le rapport JSON
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Extraire statistiques
            summary = report_data.get("summary", {})
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            total = summary.get("total", 0)
            
            # 🔥 EXTRACTION ULTRA-DÉTAILLÉE DES ERREURS
            error_logs = []
            for test in report_data.get("tests", []):
                if test.get("outcome") == "failed":
                    # Nom complet du test (SANS troncature)
                    test_nodeid = test.get("nodeid", "unknown_test")
                    
                    # Extraire juste le nom de la fonction de test
                    test_name = test_nodeid
                    if "::" in test_nodeid:
                        test_name = test_nodeid.split("::")[-1]
                    
                    # Extraire le message d'erreur COMPLET
                    call_info = test.get("call", {})
                    message = ""
                    traceback_text = ""
                    
                    # Méthode 1: longrepr (le plus détaillé)
                    if "longrepr" in call_info:
                        longrepr = call_info["longrepr"]
                        if isinstance(longrepr, str):
                            traceback_text = longrepr
                            
                            # Extraire le message d'erreur principal
                            # Chercher les lignes qui contiennent l'erreur
                            lines = longrepr.strip().split('\n')
                            
                            # Chercher AssertionError, ValueError, etc.
                            for line in lines:
                                if any(err in line for err in ['AssertionError', 'ValueError', 'ZeroDivisionError', 'TypeError', 'Error']):
                                    message = line.strip()
                                    break
                            
                            # Si pas trouvé, prendre la dernière ligne non-vide
                            if not message:
                                for line in reversed(lines):
                                    if line.strip() and not line.startswith(' '):
                                        message = line.strip()
                                        break
                    
                    # Méthode 2: crash.message
                    if not message and "crash" in call_info:
                        crash_msg = call_info["crash"].get("message", "")
                        if crash_msg:
                            message = crash_msg
                    
                    # Méthode 3: Fallback
                    if not message:
                        message = f"Test failed: {test.get('outcome', 'unknown')}"
                    
                    # 🔥 NETTOYER LE MESSAGE POUR LE RENDRE PLUS CLAIR
                    message = _clean_error_message(message, traceback_text)
                    
                    error_logs.append({
                        "test": test_name,  # Nom court: test_divide_by_zero
                        "test_full_path": test_nodeid,  # Chemin complet
                        "message": message[:800],  # Message nettoyé
                        "traceback": traceback_text[:1500]  # Traceback complet
                    })
            
            # Nettoyer le fichier
            report_file.unlink()
            
            return {
                "passed_count": passed,
                "failed_count": failed,
                "total_count": total,
                "error_logs": error_logs,
                "execution_time": report_data.get("duration", 0)
            }
        
        else:
            # Fallback: parser stdout/stderr
            return parse_pytest_output(result.stdout, result.stderr, result.returncode)
    
    except subprocess.TimeoutExpired:
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [{
                "test": "timeout",
                "message": f"Timeout après {timeout} secondes",
                "traceback": ""
            }]
        }
    
    except FileNotFoundError:
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [{
                "test": "pytest_missing",
                "message": "Pytest n'est pas installé. Exécutez: pip install pytest pytest-json-report",
                "traceback": ""
            }]
        }
    
    except Exception as e:
        return {
            "passed_count": 0,
            "failed_count": 1,
            "total_count": 1,
            "error_logs": [{
                "test": "runner_error",
                "message": f"Erreur: {str(e)}",
                "traceback": ""
            }]
        }


def _clean_error_message(message: str, traceback: str) -> str:
    """
    Nettoie et clarifie le message d'erreur pour le rendre actionnable
    
    Args:
        message: Message d'erreur brut
        traceback: Traceback complet
        
    Returns:
        Message d'erreur nettoyé et clarifié
    """
    # Enlever les préfixes pytest
    message = message.replace('E       ', '').replace('E   ', '').strip()
    
    # Si c'est une AssertionError avec pytest.raises
    if 'DID NOT RAISE' in message.upper() or 'did not raise' in message:
        # Extraire quelle exception était attendue
        expected_match = re.search(r'Expected\s+(\w+)', message, re.IGNORECASE)
        if expected_match:
            expected_exc = expected_match.group(1)
            return f"Expected {expected_exc} but no exception was raised"
        return "Expected exception was not raised"
    
    # Si c'est "Failed: DID NOT RAISE <exception>"
    if 'Failed: DID NOT RAISE' in message:
        exc_match = re.search(r'DID NOT RAISE <class \'(\w+)\'>', message)
        if exc_match:
            exc_type = exc_match.group(1)
            return f"Expected {exc_type} exception but got different exception or no exception"
    
    # Chercher dans le traceback pour plus de contexte
    if traceback and 'with pytest.raises' in traceback:
        # C'est un test qui attend une exception
        exc_type_match = re.search(r'with pytest\.raises\((\w+)\)', traceback)
        raised_exc_match = re.search(r'(ValueError|ZeroDivisionError|TypeError|KeyError|IndexError|AttributeError):', traceback)
        
        if exc_type_match and raised_exc_match:
            expected = exc_type_match.group(1)
            raised = raised_exc_match.group(1)
            if expected != raised:
                return f"Expected {expected} but got {raised} instead"
    
    return message


def parse_pytest_output(stdout: str, stderr: str, returncode: int) -> Dict:
    """
    Parse la sortie texte de pytest (fallback)
    """
    passed = 0
    failed = 0
    error_logs = []
    
    output = stdout + "\n" + stderr
    
    # Extraire passed/failed
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
    
    # Si pas de tests
    if passed == 0 and failed == 0:
        if returncode == 0:
            return {
                "passed_count": 0,
                "failed_count": 0,
                "total_count": 0,
                "error_logs": [{
                    "test": "no_tests",
                    "message": "Aucun test trouvé",
                    "traceback": ""
                }]
            }
        else:
            failed = 1
    
    total = passed + failed
    
    # Extraire les erreurs
    if failed > 0:
        # Chercher FAILED
        failed_tests = re.findall(r'FAILED\s+([\w/:.]+)\s*-\s*(.*)', output)
        
        if failed_tests:
            for test_path, error_msg in failed_tests:
                # Extraire juste le nom du test
                test_name = test_path.split("::")[-1] if "::" in test_path else test_path
                
                error_logs.append({
                    "test": test_name,
                    "test_full_path": test_path,
                    "message": error_msg[:500],
                    "traceback": ""
                })
        else:
            error_logs.append({
                "test": "unknown_test",
                "message": stderr[:500] if stderr else "Tests échoués",
                "traceback": ""
            })
    
    return {
        "passed_count": passed,
        "failed_count": failed,
        "total_count": total,
        "error_logs": error_logs
    }


def check_pytest_installed() -> bool:
    """Vérifie si pytest est installé"""
    try:
        result = subprocess.run(
            ["pytest", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False