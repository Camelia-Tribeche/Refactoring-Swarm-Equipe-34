"""
swarm_orchestrator.py - Orchestrateur du système multi-agents
Gère le flux d'exécution et la boucle de self-healing
VERSION FIXÉE - Le Juge génère ET exécute les tests
VERSION MODIFIÉE - Succès si au moins 80% des tests passent
"""
import sys
from pathlib import Path
from typing import Dict, List


from src.agents.auditor_agent import AuditorAgent
from src.agents.fixer_agent import FixerAgent
from src.agents.judge_agent import JudgeAgent
from src.tools.file_manager import list_python_files, backup_file
from src.utils.logger import log_experiment, ActionType


class RefactoringSwarm:
    """
    Orchestrateur principal du système de refactoring
    Gère la collaboration entre les agents selon le schéma:
    Auditeur → Correcteur → Juge (génère tests + valide) → (loop si échec)
    """
    
    # ========================================
    # CONFIGURATION CONSTANTS
    # ========================================
    
    # Success threshold: minimum percentage of tests that must pass
    SUCCESS_THRESHOLD = 0.80  # 80% of tests must pass for success
    
    def __init__(self, target_directory: Path, max_iterations: int = 3, success_threshold: float = None):
        """
        Initialise l'orchestrateur
        
        Args:
            target_directory: Dossier contenant le code à refactorer
            max_iterations: Nombre maximum d'itérations de self-healing
            success_threshold: Seuil de réussite (0.0 à 1.0). Si None, utilise SUCCESS_THRESHOLD
        """
        self.target_directory = Path(target_directory)
        self.max_iterations = max_iterations
        self.current_iteration = 0
        
        # Configurer le seuil de succès
        if success_threshold is not None:
            if not 0.0 <= success_threshold <= 1.0:
                raise ValueError(f"success_threshold doit être entre 0.0 et 1.0, reçu: {success_threshold}")
            self.success_threshold = success_threshold
        else:
            self.success_threshold = self.SUCCESS_THRESHOLD
        
        # Initialiser les agents
        print("🔧 Initialisation des agents...")
        self.auditor = AuditorAgent()
        self.fixer = FixerAgent()
        self.judge = JudgeAgent()  # Juge = Génère tests + Exécute tests
        
        print(f"✅ Agents prêts : Auditeur, Correcteur, Juge")
        print(f"📊 Seuil de succès configuré : {self.success_threshold * 100:.0f}% des tests doivent passer\n")
    
    def _discover_files(self) -> List[str]:
        """Découvre les fichiers Python à traiter"""
        files = list_python_files(str(self.target_directory))
        print(f"📦 {len(files)} fichiers Python détectés\n")
        return files
    
    def _cleanup_test_directory(self):
        """Nettoie le répertoire de tests dans sandbox avant de commencer"""
        test_dir = self.target_directory / "tests"
        
        if test_dir.exists():
            import shutil
            try:
                print(f"🧹 Nettoyage du répertoire {test_dir}...")
                shutil.rmtree(test_dir)
                print(f"   ✅ Répertoire {test_dir} supprimé")
            except Exception as e:
                print(f"   ⚠️  Impossible de supprimer {test_dir}: {e}")
        else:
            print(f"ℹ️  Aucun répertoire de tests à nettoyer dans {self.target_directory}")
        
        print()
    
    def _phase_audit(self, files: List[str]) -> Dict:
        """
        Phase 1: Audit du code
        L'Auditeur analyse le code et produit un plan
        """
        print("\n🔍 Phase 1/4 : Audit du code...\n")
        print("   📋 Analyse statique du code...")
        print("   🔎 Recherche de bugs et violations PEP8...")
        
        plan = self.auditor.analyze(files)
        
        total_issues = sum(len(f.get("issues", [])) for f in plan.get("issues", []))
        print(f"\n   ✅ Plan de refactoring généré ({total_issues} problèmes détectés)")
        
        return plan
    
    def _phase_test_generation(self, files: List[str]) -> Dict:
        """
        Phase 2: Génération des tests intelligents
        Le Juge crée des tests basés sur l'INTENTION des fonctions
        """
        print("\n🧪 Phase 2/4 : Génération des tests intelligents...\n")
        print("   🧠 Analyse du code pour comprendre la logique métier...")
        print("   📝 Génération de tests par le Juge...")
        
        test_files = []
        for file_path in files:
            # Le JUGE génère les tests (pas un agent séparé)
            test_file = self.judge.generate_tests(file_path, self.target_directory)
            if test_file:
                test_files.append(test_file)
        
        if test_files:
            print(f"      ✅ Tests générés: {', '.join([Path(f).name for f in test_files])}")
        
        print(f"   ✅ {len(test_files)} fichiers de tests créés")
        
        return {
            "test_files": test_files,
            "status": "completed"
        }
    
    def _phase_fix(self, plan: Dict, error_logs: List = None) -> Dict:
        """
        Phase 3: Application des corrections
        Le Fixer modifie le code selon le plan
        """
        print("\n🔧 Phase 3/4 : Application des corrections...\n")
        print("   🛠️  Lecture du plan de refactoring...")
        print("   ✏️  Modification du code fichier par fichier...")
        
        result = self.fixer.fix(plan, error_logs)
        
        print(f"\n   ✅ {len(result['files_modified'])} fichiers modifiés")
        print(f"   🐛 {result['bugs_fixed']} corrections appliquées")
        
        return result
    
    def _phase_validation(self, files: List[str]) -> Dict:
        """
        Phase 4: Validation par le Juge
        Le Juge exécute les tests qu'il a générés
        """
        print("\n⚖️  Phase 4/4 : Validation par le Juge...\n")
        
        # Le JUGE fait tout: syntaxe + exécution des tests
        validation_result = self.judge.validate(files, self.target_directory)
        
        return validation_result
    
    def _evaluate_success(self, validation_result: Dict) -> tuple[bool, str]:
        """
        Évalue si le refactoring est réussi selon le seuil configuré
        
        Args:
            validation_result: Résultats de validation du Juge
            
        Returns:
            Tuple (success: bool, reason: str)
        """
        # Si le Juge a détecté des erreurs de syntaxe, échec automatique
        gate_failed = validation_result.get("gate_failed", None)
        if gate_failed == "syntax":
            return False, "Erreurs de syntaxe détectées"
        
        # Calculer le pourcentage de tests réussis
        tests_passed = validation_result.get("tests_passed", 0)
        tests_total = validation_result.get("tests_total", 0)
        
        # Cas où aucun test n'existe (traiter comme un avertissement, pas un échec)
        if tests_total == 0:
            print("   ⚠️  AVERTISSEMENT: Aucun test disponible pour valider le code")
            return True, "Aucun test disponible (validation impossible)"
        
        # Calculer le taux de réussite
        success_rate = tests_passed / tests_total
        
        print(f"\n   📊 Taux de réussite: {success_rate * 100:.1f}% ({tests_passed}/{tests_total} tests)")
        print(f"   🎯 Seuil requis: {self.success_threshold * 100:.0f}%")
        
        # Vérifier si on atteint le seuil
        if success_rate >= self.success_threshold:
            return True, f"{success_rate * 100:.1f}% des tests passent (>= {self.success_threshold * 100:.0f}% requis)"
        else:
            tests_needed = int(self.success_threshold * tests_total) - tests_passed
            return False, f"Seulement {success_rate * 100:.1f}% des tests passent, {tests_needed} test(s) de plus nécessaire(s)"
    
    def _self_healing_iteration(self, plan: Dict, validation_result: Dict) -> Dict:
        """
        Boucle de self-healing
        Le Fixer réessaie en tenant compte des erreurs
        """
        print("\n" + "-" * 70)
        print("       🔄 Préparation de l'itération suivante (Self-Healing)...")
        
        gate_failed = validation_result.get("gate_failed", "unknown")
        
        if gate_failed == "syntax":
            print("             Correction des erreurs de syntaxe...")
        elif gate_failed == "tests":
            failed_count = validation_result.get("tests_failed", 0)
            print(f"             Correction de {failed_count} erreur(s) de logique métier...")
        else:
            # Cas où on a un pourcentage insuffisant mais pas d'échec catégorique
            tests_passed = validation_result.get("tests_passed", 0)
            tests_total = validation_result.get("tests_total", 1)
            success_rate = tests_passed / tests_total if tests_total > 0 else 0
            print(f"             Amélioration du taux de réussite ({success_rate * 100:.1f}% → {self.success_threshold * 100:.0f}% cible)...")
        
        print("-" * 70)
        
        # Récupérer les erreurs pour informer le Fixer
        error_logs = validation_result.get("errors", [])
        
        # Réappliquer les corrections avec le contexte d'erreur
        fix_result = self._phase_fix(plan, error_logs)
        
        return fix_result
    
    def run(self) -> Dict:
        """
        Exécute le processus complet de refactoring
        
        Returns:
            Dict avec les résultats finaux
        """
        # Nettoyer le répertoire de tests dans sandbox
        self._cleanup_test_directory()
        
        # Découverte des fichiers
        files = self._discover_files()
        
        if not files:
            return {
                "success": False,
                "error": "Aucun fichier Python trouvé",
                "iterations_used": 0,
                "files_processed": 0,
                "bugs_fixed": 0,
                "tests_passed": 0,
                "total_tests": 0,
                "success_rate": 0.0,
                "threshold": self.success_threshold
            }
        
        # Sauvegarder les fichiers originaux
        print("💾 Sauvegarde des fichiers originaux...")
        for file_path in files:
            try:
                backup_file(file_path)
            except Exception as e:
                print(f"   ⚠️  Impossible de sauvegarder {file_path}: {e}")
        
        # Phase 1: Audit initial
        plan = self._phase_audit(files)
        
        # Phase 2: Génération des tests (par le Juge)
        test_gen_result = self._phase_test_generation(files)
        
        total_bugs_fixed = 0
        last_validation = None
        
        # Boucle de refactoring avec self-healing
        for iteration in range(1, self.max_iterations + 1):
            self.current_iteration = iteration
            
            print("\n" + "=" * 70)
            print(f"                           🔄 ITÉRATION {iteration}/{self.max_iterations}")
            print("=" * 70)
            
            # Phase 3: Correction
            if iteration == 1:
                fix_result = self._phase_fix(plan)
            else:
                # Self-healing avec les erreurs de l'itération précédente
                fix_result = self._self_healing_iteration(plan, last_validation)
            
            total_bugs_fixed += fix_result.get("bugs_fixed", 0)
            
            # Phase 4: Validation (par le Juge)
            validation_result = self._phase_validation(files)
            last_validation = validation_result
            
           
            # Calculer les métriques finales
            tests_passed = validation_result.get("tests_passed", 0)
            tests_total = validation_result.get("tests_total", 0)
            success_rate = (tests_passed / tests_total) if tests_total > 0 else 0.0
            
                # Succès immédiat si TOUS les tests passent
            if tests_total > 0 and tests_passed == tests_total:
                print("\n" + "=" * 70)
                print("                ✅ SUCCÈS - Tous les tests réussis!")
                print("=" * 70)

                return {
                "success": True,
                "reason": "Tous les tests ont été validés avant la limite d'itérations",
                "iterations_used": iteration,
                "files_processed": len(files),
                "bugs_fixed": total_bugs_fixed,
                "tests_passed": tests_passed,
                "total_tests": tests_total,
                "success_rate": success_rate,
                "threshold": self.success_threshold,
                "output_directory": str(self.target_directory)
               }

            
            # Si c'est la dernière itération et on a encore échoué
            if iteration == self.max_iterations:
                # NOUVELLE LOGIQUE: Évaluer le succès selon le seuil
              is_successful, reason = self._evaluate_success(validation_result)
              if is_successful:
                print("\n" + "=" * 70)
                print("                ✅ SUCCÈS - Code refactoré et validé!")
                print(f"                   {reason}")
                print("=" * 70)
                
                return {
                    "success": True,
                    "reason": reason,
                    "iterations_used": iteration,
                    "files_processed": len(files),
                    "bugs_fixed": total_bugs_fixed,
                    "tests_passed": tests_passed,
                    "total_tests": tests_total,
                    "success_rate": success_rate,
                    "threshold": self.success_threshold,
                    "output_directory": str(self.target_directory)
                }
              else :
                print("\n" + "=" * 70)
                print(f"                ⚠️  LIMITE ATTEINTE : {self.max_iterations} itérations max")
                print(f"                   {reason}")
                print("=" * 70)
                
                return {
                    "success": False,
                    "error": reason,
                    "iterations_used": iteration,
                    "files_processed": len(files),
                    "bugs_fixed": total_bugs_fixed,
                    "tests_passed": tests_passed,
                    "total_tests": tests_total,
                    "success_rate": success_rate,
                    "threshold": self.success_threshold,
                    "output_directory": str(self.target_directory)
                }
        
        # Cas par défaut (ne devrait jamais arriver)
        return {
            "success": False,
            "error": "Erreur inconnue",
            "iterations_used": self.max_iterations,
            "files_processed": len(files),
            "bugs_fixed": total_bugs_fixed,
            "tests_passed": 0,
            "total_tests": 0,
            "success_rate": 0.0,
            "threshold": self.success_threshold
        }