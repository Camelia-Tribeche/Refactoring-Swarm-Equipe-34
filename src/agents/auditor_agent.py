"""
auditor_agent.py - Agent Auditeur
Analyse le code et produit un plan de refactoring
"""
import os
import json
import google.generativeai as genai
from pathlib import Path
from src.utils.logger import log_experiment, ActionType
from src.tools.static_analyzer import run_pylint_on_file


class AuditorAgent:
    """
    Agent responsable de l'audit du code
    Utilise Gemini + Pylint pour analyser et détecter les problèmes
    """
    
    def __init__(self):
        """Initialise l'agent Auditeur avec le LLM"""
        # Configuration du modèle LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY non trouvée dans .env")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Charger le prompt système
        self.system_prompt = self._load_system_prompt()
        
        print("✅ Auditeur initialisé (Gemini 2.5 Flash)")
    
    def _load_system_prompt(self) -> str:
        """Charge le prompt système depuis le fichier"""
        prompt_path = Path("src/prompts/auditor_prompt.txt")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback si le fichier n'existe pas
        return """Tu es un expert Python chargé d'auditer du code.

Ton rôle :
1. Analyser le code fourni
2. Identifier les bugs, erreurs et violations PEP8
3. Détecter le code non documenté
4. Repérer les tests manquants

Retourne un plan structuré en JSON avec :
- file: nom du fichier
- issues: liste des problèmes trouvés
- priority: HIGH, MEDIUM, LOW
- suggestions: recommandations de correction

Sois précis et constructif."""
    
    def analyze(self, files: list) -> dict:
        """
        Analyse les fichiers et retourne un plan de refactoring
        
        Args:
            files: Liste des chemins de fichiers à analyser
            
        Returns:
            Dict contenant le plan de refactoring avec tous les problèmes détectés
        """
        print(f"🔍 Analyse de {len(files)} fichiers...\n")
        
        all_issues = []
        
        for file_path in files:
            print(f"   📄 Analyse : {Path(file_path).name}")
            
            try:
                # 1. Analyse statique avec Pylint
                pylint_score, pylint_issues = run_pylint_on_file(file_path)
                print(f"      📊 Score Pylint : {pylint_score}/10")
                
                # 2. Lecture du code
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                
                # 3. Analyse avec le LLM - PROMPT SIMPLIFIÉ
                user_prompt = f"""Analyse ce fichier Python et identifie UNIQUEMENT les 3-5 problèmes les PLUS CRITIQUES.

**Fichier** : {Path(file_path).name}

**Code** :
```python
{code_content[:1500]}
```

**Score Pylint** : {pylint_score}/10

Fournis un plan JSON COMPACT (max 10 lignes) :
{{
    "file": "CHEMIN_COMPLET_DU_FICHIER",
    "issues": [
        {{"type": "bug", "line": 1, "description": "Problème X", "priority": "HIGH", "suggestion": "Correction Y"}},
        {{"type": "pep8", "line": 2, "description": "Problème Z", "priority": "MEDIUM", "suggestion": "Fix W"}}
    ]
}}

IMPORTANT : 
- Maximum 5 issues
- Descriptions COURTES (max 50 caractères)
- JSON valide UNIQUEMENT, RIEN d'autre
- PAS de markdown ```json"""
                
                # Appel au LLM
                response = self.model.generate_content(
                    f"{self.system_prompt}\n\n{user_prompt}"
                )
                
                # Log obligatoire
                log_experiment(
                    agent_name="Auditor_Agent",
                    model_used="gemini-2.5-flash",
                    action=ActionType.ANALYSIS,
                    details={
                        "file_analyzed": file_path,
                        "input_prompt": user_prompt[:500],
                        "output_response": response.text[:500],
                        "pylint_score": pylint_score,
                        "code_length": len(code_content)
                    },
                    status="SUCCESS"
                )
                
                # Parser la réponse JSON
                try:
                    # Nettoyer la réponse (enlever ```json si présent)
                    clean_response = response.text.strip()
                    if "```json" in clean_response:
                        clean_response = clean_response.split("```json")[1].split("```")[0]
                    elif "```" in clean_response:
                        clean_response = clean_response.split("```")[1].split("```")[0]
                    
                    # Parser le JSON
                    analysis = json.loads(clean_response)
                    
                    # IMPORTANT : Forcer le chemin complet du fichier
                    analysis["file"] = file_path
                    
                    # Vérifier la structure
                    if "issues" not in analysis:
                        print(f"      ⚠️  JSON invalide - structure incorrecte")
                        # Fallback basique
                        analysis = {
                            "file": file_path,
                            "issues": [
                                {
                                    "type": "pylint",
                                    "line": 1,
                                    "description": f"Score Pylint: {pylint_score}/10",
                                    "priority": "MEDIUM",
                                    "suggestion": "Corriger violations PEP8"
                                }
                            ]
                        }
                    
                    all_issues.append(analysis)
                    
                    issues_count = len(analysis.get("issues", []))
                    print(f"      🐛 {issues_count} problèmes détectés")
                    
                except json.JSONDecodeError as e:
                    print(f"      ⚠️  Erreur parsing JSON : {e}")
                    print(f"      📄 Réponse brute : {response.text[:200]}...")
                    # Fallback : créer une structure basique
                    all_issues.append({
                        "file": file_path,
                        "issues": [
                            {
                                "type": "pylint",
                                "line": 1,
                                "description": f"Score Pylint : {pylint_score}/10",
                                "priority": "MEDIUM",
                                "suggestion": "Corriger les violations Pylint"
                            }
                        ]
                    })
            
            except Exception as e:
                print(f"      ❌ Erreur lors de l'analyse : {e}")
                log_experiment(
                    agent_name="Auditor_Agent",
                    model_used="gemini-2.5-flash",
                    action=ActionType.DEBUG,
                    details={
                        "file_analyzed": file_path,
                        "input_prompt": f"Analyse de {file_path}",
                        "output_response": f"Erreur: {str(e)}",
                        "error": str(e)
                    },
                    status="FAILURE"
                )
        
        print(f"\n✅ Audit terminé : {len(all_issues)} fichiers analysés\n")
        
        return {
            "issues": all_issues,
            "total_files": len(files),
            "status": "completed"
        }