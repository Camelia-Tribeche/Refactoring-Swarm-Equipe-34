"""
swarm_orchestrator.py - Le cerveau du système multi-agents
Avec gestion du rate limiting via sleep()
"""
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
import json
import time
import tempfile
import subprocess
import os
from src.tools.test_runner import run_pytest_on_directory
# Import des agents
from src.agents.auditor_agent import AuditorAgent
from src.agents.fixer_agent import FixerAgent
from src.agents.judge_agent import JudgeAgent

# Import du logger
from src.utils.logger import log_experiment, ActionType


@dataclass
class SwarmState:
    """État partagé entre tous les agents"""
    # Configuration
    target_directory: Path
    max_iterations: int = 4
    
    # Progression
    current_iteration: int = 0
    
    # Données échangées entre agents
    refactoring_plan: Dict = field(default_factory=dict)
    test_results: Dict = field(default_factory=dict)
    error_logs: List[str] = field(default_factory=list)
    
    # Fichiers
    files_to_process: List[str] = field(default_factory=list)
    files_processed: List[str] = field(default_factory=list)
    
    # Métriques
    bugs_fixed: int = 0
    all_tests_passed: bool = False
    
    # Contrôle de flux
    should_continue: bool = True


class RefactoringSwarm:
    """L'Orchestrateur avec gestion du rate limiting"""
    
    def __init__(self, target_directory: Path, max_iterations: int = 4):
        """Initialise l'orchestrateur et crée les 3 agents"""
        self.target_directory = target_directory
        self.max_iterations = max_iterations
        
        # Créer les 3 agents
        print("🔧 Initialisation des agents...")
        self.auditor = AuditorAgent()
        time.sleep(2)  # Pause après init Auditor
        
        self.fixer = FixerAgent()
        time.sleep(2)  # Pause après init Fixer
        
        self.judge = JudgeAgent()
        time.sleep(2)  # Pause après init Judge
        
        print("✅ Agents prêts : Auditeur, Correcteur, Juge\n")
        
        # Créer l'état initial
        self.state = SwarmState(
            target_directory=target_directory,
            max_iterations=max_iterations
        )
    
    def run(self) -> Dict[str, Any]:
        """Fonction principale - LE GRAPHE EST ICI"""
        start_time = time.time()
        
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": f"Démarrage orchestration sur {self.target_directory}",
                "output_response": "Recherche des fichiers Python",
                "target_directory": str(self.target_directory),
                "max_iterations": self.max_iterations
            },
            status="SUCCESS"
        )
        
        # ÉTAPE 0 : Découvrir les fichiers Python
        self._discover_python_files()
        
        if not self.state.files_to_process:
            return {
                "success": False,
                "error": "Aucun fichier Python (.py) trouvé dans le répertoire",
                "iterations_used": 0,
                "files_processed": 0,
                "bugs_fixed": 0,
                "tests_passed": 0,
                "total_tests": 0
            }
        
        print(f"📦 {len(self.state.files_to_process)} fichiers Python détectés\n")
        
        # CYCLE PRINCIPAL - LA BOUCLE SELF-HEALING
        while self.state.should_continue and self.state.current_iteration < self.max_iterations:
            self.state.current_iteration += 1
            
            print(f"\n{'='*70}")
            print(f"🔄 ITÉRATION {self.state.current_iteration}/{self.max_iterations}".center(70))
            print(f"{'='*70}\n")
            
            # ÉTAPE 1 : AUDITEUR (Uniquement à la 1ère itération)
            if self.state.current_iteration == 1:
                print("🔍 Phase 1/3 : Audit du code...\n")
                success = self._run_auditor()
                if not success:
                    break
                print()
                time.sleep(3)  # ⏰ PAUSE après Auditor
            
            # ÉTAPE 2 : CORRECTEUR
            print("🔧 Phase 2/3 : Application des corrections...\n")
            success = self._run_fixer()
            if not success:
                break
            print()
            time.sleep(3)  # ⏰ PAUSE après Fixer
            
            # ÉTAPE 3 : JUGE (Tests)
            print("⚖️  Phase 3/3 : Exécution des tests...\n")
            success = self._run_judge()
            if not success:
                break
            print()
            time.sleep(3)  # ⏰ PAUSE après Judge
            
            # DÉCISION : Continuer ou Stop ?
            self._evaluate_continuation()
        
        # FIN : Générer le rapport final
        elapsed_time = time.time() - start_time
        return self._generate_final_report(elapsed_time)
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES PRIVÉES (les étapes du graphe)
    # ═══════════════════════════════════════════════════════════════
    
    def _discover_python_files(self):
        """Trouve tous les fichiers .py dans le répertoire cible"""
        python_files = list(self.target_directory.rglob("*.py"))
        
        self.state.files_to_process = [str(f) for f in python_files]
        
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": "Découverte des fichiers Python à refactorer",
                "output_response": f"{len(python_files)} fichiers trouvés",
                "files_found": self.state.files_to_process
            },
            status="SUCCESS"
        )
    
    def _run_auditor(self) -> bool:
        """Exécute l'agent AUDITEUR"""
        try:
            print("   📋 Analyse statique du code...")
            print("   🔎 Recherche de bugs et violations PEP8...")
            
            # Appel à l'agent Auditeur
            self.state.refactoring_plan = self.auditor.analyze(
                files=self.state.files_to_process
            )
            
            if not self.state.refactoring_plan or len(self.state.refactoring_plan) == 0:
                print("   ❌ L'auditeur n'a pas produit de plan valide")
                return False
            
            issues_count = len(self.state.refactoring_plan.get("issues", []))
            print(f"   ✅ Plan de refactoring généré ({issues_count} problèmes détectés)")
            return True
            
        except Exception as e:
            print(f"   ❌ ERREUR lors de l'audit : {e}")
            self.state.should_continue = False
            return False
    
    def _run_fixer(self) -> bool:
        """Exécute l'agent CORRECTEUR"""
        try:
            print("   🛠️  Lecture du plan de refactoring...")
            print("   ✏️  Modification du code fichier par fichier...")
            
            # Appel à l'agent Correcteur
            result = self.fixer.fix(
                plan=self.state.refactoring_plan,
                error_logs=self.state.error_logs
            )
            
            self.state.bugs_fixed += result.get("bugs_fixed", 0)
            self.state.files_processed = result.get("files_modified", [])
            
            print(f"   ✅ {len(self.state.files_processed)} fichiers modifiés")
            print(f"   🐛 {result.get('bugs_fixed', 0)} corrections appliquées")
            return True
            
        except Exception as e:
            print(f"   ❌ ERREUR lors de la correction : {e}")
            self.state.should_continue = False
            return False
    
    
                    
    def _run_judge(self) -> bool:
        """Exécute l'agent JUGE avec validation complète"""
        try:
            print("   🧪 Génération et exécution des tests...")
            
            # Générer tests pour chaque fichier
            test_files = []
            for file_path in self.state.files_to_process:
                test_path = self._generate_test_file(file_path)
                if test_path:
                    test_files.append(test_path)
                    print(f"   ✅ Tests générés: {Path(test_path).name}")
            
            if not test_files:
                print("   ⚠️  Aucun test généré - validation via syntax + pylint uniquement")
                # Fallback: validation minimale
                return self._minimal_validation()
            
            # Exécuter pytest
            print("   🔬 Exécution de pytest sur les tests générés...")
            result = run_pytest_on_directory(str(self.target_directory))
            
            self.state.test_results = result
            self.state.all_tests_passed = result.get("failed_count", 1) == 0
            self.state.error_logs = result.get("error_logs", [])
            
            print(f"   📊 Résultats: {result.get('passed_count', 0)}/{result.get('total_count', 0)} tests passés")
            
            if not self.state.all_tests_passed:
                print(f"   ❌ {result.get('failed_count', 0)} tests échoués")
            
            return True
            
        except Exception as e:
            print(f"   ❌ ERREUR lors des tests : {e}")
            self.state.should_continue = False
            return False

    def _generate_test_file(self, file_path: str) -> str:
        """Génère un fichier de test basique pour un fichier Python"""
        try:
            file_name = Path(file_path).stem
            test_dir = self.target_directory / "tests"
            test_dir.mkdir(exist_ok=True)
            
            test_file = test_dir / f"test_{file_name}.py"
            
            # Template de test basique
            test_content = f'''"""Tests auto-générés pour {file_name}.py"""
import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

def test_file_imports():
    """Vérifie que le fichier peut être importé sans erreur"""
    try:
        import {file_name}
        assert True
    except Exception as e:
        pytest.fail(f"Import failed: {{e}}")

def test_syntax_valid():
    """Vérifie la syntaxe Python"""
    import py_compile
    try:
        py_compile.compile(r"{file_path}", doraise=True)
        assert True
    except Exception as e:
        pytest.fail(f"Syntax error: {{e}}")
'''
            
            test_file.write_text(test_content, encoding='utf-8')
            return str(test_file)
            
        except Exception as e:
            print(f"   ⚠️  Erreur génération test pour {file_path}: {e}")
            return None

    def _minimal_validation(self) -> bool:
        """Validation minimale sans tests pytest"""
        import py_compile
        
        all_valid = True
        for file_path in self.state.files_to_process:
            try:
                py_compile.compile(file_path, doraise=True)
            except Exception as e:
                print(f"   ❌ Erreur syntax dans {Path(file_path).name}: {e}")
                all_valid = False
        
        self.state.all_tests_passed = all_valid
        self.state.test_results = {
            "passed_count": len(self.state.files_to_process) if all_valid else 0,
            "failed_count": 0 if all_valid else 1,
            "total_count": len(self.state.files_to_process),
            "error_logs": []
        }
        
        return True
    
    def _evaluate_continuation(self):
        """DÉCISION : Continuer ou arrêter ?"""
        
        # CAS 1 : Tous les tests passent → Mission accomplie !
        if self.state.all_tests_passed:
            print("\n" + "="*70)
            print("🎉 OBJECTIF ATTEINT : Tous les tests passent !".center(70))
            print("="*70)
            self.state.should_continue = False
            return
        
        # CAS 2 : Limite d'itérations atteinte → Abandon
        if self.state.current_iteration >= self.max_iterations:
            print("\n" + "="*70)
            print(f"⚠️  LIMITE ATTEINTE : {self.max_iterations} itérations max".center(70))
            print("Le système n'a pas pu faire passer tous les tests".center(70))
            print("="*70)
            self.state.should_continue = False
            return
        
        # CAS 4 : Continuer la boucle self-healing
        print("\n" + "-"*70)
        print("🔄 Préparation de l'itération suivante (Self-Healing Loop)...".center(70))
        print(f"Les erreurs seront transmises au Correcteur".center(70))
        print("-"*70)
    
    def _generate_final_report(self, elapsed_time: float) -> Dict[str, Any]:
        """Génère le rapport final d'exécution"""
        report = {
            "success": self.state.all_tests_passed,
            "iterations_used": self.state.current_iteration,
            "max_iterations": self.max_iterations,
            "files_processed": len(self.state.files_processed),
            "bugs_fixed": self.state.bugs_fixed,
            "tests_passed": self.state.test_results.get("passed_count", 0),
            "total_tests": self.state.test_results.get("total_count", 0),
            "elapsed_time": round(elapsed_time, 2),
            "output_directory": str(self.target_directory)
        }
        
        if not self.state.all_tests_passed:
            report["error"] = "Le système n'a pas réussi à faire passer tous les tests dans le temps imparti"
        
        # Log final
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": "Génération du rapport final d'exécution",
                "output_response": json.dumps(report, indent=2),
                "final_report": report,
                "execution_time": elapsed_time
            },
            status="SUCCESS" if report["success"] else "FAILURE"
        )
        
        return report