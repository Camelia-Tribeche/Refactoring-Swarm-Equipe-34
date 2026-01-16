"""
main.py - Point d'entrée du système Refactoring Swarm
Orchestrateur : Gère le flux d'exécution des agents

Commande : python main.py --target_dir ./sandbox/code_buggy
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()   # ← OBLIGATOIRE AVANT TOUT IMPORT D’AGENTS

from src.orchestrator.swarm_orchestrator import RefactoringSwarm
from src.utils.logger import log_experiment, ActionType



def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(
        description="🐝 Refactoring Swarm - Système multi-agents de refactoring automatique"
    )
    parser.add_argument(
        "--target_dir",
        type=str,
        required=True,
        help="Chemin vers le dossier contenant le code à refactorer"
    )
    parser.add_argument(
        "--max_iterations",
        type=int,
        default=3,
        help="Nombre maximum d'itérations (défaut: 3)"
    )
    return parser.parse_args()


def validate_target_directory(target_dir: str) -> Path:
    """Valide que le répertoire cible existe"""
    path = Path(target_dir)
    if not path.exists():
        print(f"❌ Erreur : Le répertoire '{target_dir}' n'existe pas")
        sys.exit(1)
    if not path.is_dir():
        print(f"❌ Erreur : '{target_dir}' n'est pas un répertoire")
        sys.exit(1)
    return path


def print_banner():
    """Affiche la bannière de démarrage"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║           🐝 THE REFACTORING SWARM 🐝                    ║
║     Système Multi-Agents de Refactoring Automatique      ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_final_summary(result: dict):
    """Affiche le résumé final de l'exécution"""
    print("\n" + "="*70)
    print("📊 RÉSUMÉ FINAL".center(70))
    print("="*70)
    
    if result["success"]:
        print("✅ STATUT : SUCCÈS - Le code a été refactoré avec succès !")
    else:
        print("❌ STATUT : ÉCHEC - Le système n'a pas pu terminer le refactoring")
        if "error" in result:
            print(f"💥 Raison : {result['error']}")
    
    print(f"\n📈 STATISTIQUES :")
    print(f"   • Itérations utilisées : {result['iterations_used']}/{result.get('max_iterations', 3)}")
    print(f"   • Fichiers traités : {result['files_processed']}")
    print(f"   • Bugs corrigés : {result['bugs_fixed']}")
    print(f"   • Tests réussis : {result['tests_passed']}/{result['total_tests']}")
    
    print("\n📁 FICHIERS DE SORTIE :")
    print(f"   • Logs détaillés : logs/experiment_data.json")
    print(f"   • Code refactoré : {result.get('output_directory', 'sandbox/')}")
    
    print("="*70 + "\n")


def main():
    """Fonction principale d'orchestration"""
    print_banner()
    
    # 1. Parser les arguments
    args = parse_arguments()
    target_dir = validate_target_directory(args.target_dir)
    
    print(f"📁 Répertoire cible : {target_dir}")
    print(f"🔄 Itérations max : {args.max_iterations}")
    print("="*70 + "\n")
    
    # Log du démarrage
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "input_prompt": "Démarrage du système Refactoring Swarm",
            "output_response": f"Configuration validée pour {target_dir}",
            "target_directory": str(target_dir),
            "max_iterations": args.max_iterations
        },
        status="SUCCESS"
    )
    
    try:
        # 2. Initialiser l'orchestrateur
        print("🔧 Initialisation du système multi-agents...\n")
        swarm = RefactoringSwarm(
            target_directory=target_dir,
            max_iterations=args.max_iterations
        )
        
        # 3. Lancer le processus de refactoring
        print("\n🚀 Démarrage du processus de refactoring...\n")
        result = swarm.run()
        
        # 4. Afficher les résultats
        print_final_summary(result)
        
        # 5. Exit code approprié
        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption manuelle détectée (Ctrl+C)")
        print("🛑 Arrêt du système en cours...")
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.DEBUG,
            details={
                "input_prompt": "Interruption manuelle",
                "output_response": "Système arrêté par l'utilisateur",
            },
            status="INTERRUPTED"
        )
        sys.exit(130)
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE : {e}")
        import traceback
        traceback.print_exc()
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.DEBUG,
            details={
                "input_prompt": "Erreur système",
                "output_response": str(e),
                "traceback": traceback.format_exc()
            },
            status="ERROR"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()