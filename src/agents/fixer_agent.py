"""
fixer_agent.py - Agent Correcteur
Applique les corrections au code selon le plan de l'Auditeur
"""
import os
import json
from google import generativeai as genai
from pathlib import Path
from src.utils.logger import log_experiment, ActionType
from src.tools.file_manager import read_file_safe, write_file_safe


class FixerAgent:
    """
    Agent responsable de la correction du code
    Utilise Gemini pour appliquer les corrections intelligemment
    """
    
    def __init__(self):
        """Initialise l'agent Correcteur avec le LLM"""
        # Configuration du modèle LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY non trouvée dans .env")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Charger le prompt système
        self.system_prompt = self._load_system_prompt()
        
        print("✅ Correcteur initialisé (Gemini 2.0 Flash)")
    
    def _load_system_prompt(self) -> str:
        """Charge le prompt système depuis le fichier"""
        prompt_path = Path("src/prompts/fixer_prompt.txt")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback si le fichier n'existe pas
        return """Tu es un expert Python chargé de corriger du code.

Ton rôle :
1. Lire le code buggy fourni
2. Appliquer les corrections selon le plan
3. Conserver la fonctionnalité du code
4. Ajouter des docstrings manquantes
5. Respecter PEP8
6. Ne PAS créer de nouveaux bugs

IMPORTANT :
- Retourne UNIQUEMENT le code corrigé complet
- Pas de markdown (```python), juste le code pur
- Conserve la structure du fichier
- Si des tests échouaient, corrige les erreurs indiquées

Sois précis et ne change que ce qui doit l'être."""
    
    def fix(self, plan: dict, error_logs: list = None) -> dict:
        """
        Applique les corrections selon le plan
        
        Args:
            plan: Plan de refactoring de l'Auditeur
            error_logs: Logs d'erreurs de l'itération précédente (self-healing)
            
        Returns:
            Dict avec les fichiers modifiés et le nombre de bugs corrigés
        """
        print(f"🔧 Application des corrections...\n")
        
        if error_logs:
            print(f"   🔄 Mode Self-Healing : {len(error_logs)} erreurs à traiter\n")
        
        files_modified = []
        bugs_fixed = 0
        
        issues = plan.get("issues", [])
        
        for issue_group in issues:
            file_path = issue_group.get("file")
            issues_list = issue_group.get("issues", [])
            
            if not file_path or not issues_list:
                continue
            
            print(f"   📝 Correction : {Path(file_path).name}")
            print(f"      🐛 {len(issues_list)} problèmes à corriger")
            
            try:
                # 1. Lire le code original
                original_code = read_file_safe(file_path)
                
                # 2. Construire le prompt de correction
                issues_summary = "\n".join([
                    f"- [{i['priority']}] {i['description']} (ligne {i.get('line', '?')})"
                    for i in issues_list[:10]  # Limiter à 10 issues
                ])
                
                error_context = ""
                if error_logs:
                    # Extraire seulement les messages d'erreur pertinents
                    error_messages = []
                    for err in error_logs[:3]:
                        if isinstance(err, dict):
                            error_messages.append(err.get('error', str(err)))
                        else:
                            error_messages.append(str(err))
                    
                    error_context = f"""
⚠️ ERREURS DE L'ITÉRATION PRÉCÉDENTE :
{chr(10).join(f"- {err}" for err in error_messages)}

Corrige ces erreurs en priorité !
"""
                
                user_prompt = f"""Corrige ce fichier Python :

**Fichier** : {Path(file_path).name}

**Problèmes identifiés** :
{issues_summary}

{error_context}

**Code actuel** :
```python
{original_code}
```

IMPORTANT : 
- Réponds UNIQUEMENT avec le code Python pur corrigé
- SANS ```python ni markdown
- SANS commentaires de type #===== CODE START =====
- Juste le code Python propre et fonctionnel"""
                
                # 3. Appel au LLM
                response = self.model.generate_content(
                    f"{self.system_prompt}\n\n{user_prompt}"
                )
                
                # Log obligatoire
                log_experiment(
                    agent_name="Fixer_Agent",
                    model_used="gemini-2.5-flash",
                    action=ActionType.FIX,
                    details={
                        "file_fixed": file_path,
                        "input_prompt": user_prompt[:500],
                        "output_response": response.text[:500],
                        "issues_count": len(issues_list),
                        "had_previous_errors": bool(error_logs)
                    },
                    status="SUCCESS"
                )
                
                # 4. Nettoyer la réponse de manière AGRESSIVE
                corrected_code = response.text.strip()
                
                # Enlever les balises markdown si présentes
                if "```python" in corrected_code:
                    corrected_code = corrected_code.split("```python")[1].split("```")[0].strip()
                elif "```" in corrected_code:
                    parts = corrected_code.split("```")
                    if len(parts) >= 2:
                        corrected_code = parts[1].strip()
                
                # NOUVEAU: Extraire SEULEMENT le code entre les balises si présentes
                if "#===== CORRECTED CODE START =====" in corrected_code:
                    start_marker = "#===== CORRECTED CODE START ====="
                    end_marker = "#===== CORRECTED CODE END ====="
                    
                    start_idx = corrected_code.find(start_marker)
                    end_idx = corrected_code.find(end_marker)
                    
                    if start_idx != -1 and end_idx != -1:
                        # Extraire seulement entre les balises
                        corrected_code = corrected_code[start_idx + len(start_marker):end_idx].strip()
                
                # Enlever toute ligne qui contient "===== FIX REPORT ====="
                if "#===== FIX REPORT =====" in corrected_code:
                    corrected_code = corrected_code.split("#===== FIX REPORT =====")[0].strip()
                
                # 5. Écrire le fichier corrigé (CODE PUR SEULEMENT)
                write_file_safe(file_path, corrected_code)
                
                files_modified.append(file_path)
                bugs_fixed += len(issues_list)
                
                print(f"      ✅ Fichier corrigé et sauvegardé")
                
            except Exception as e:
                print(f"      ❌ Erreur lors de la correction : {e}")
                log_experiment(
                    agent_name="Fixer_Agent",
                    model_used="gemini-2.5-flash",
                    action=ActionType.DEBUG,
                    details={
                        "file_fixed": file_path,
                        "input_prompt": f"Correction de {file_path}",
                        "output_response": f"Erreur: {str(e)}",
                        "error": str(e)
                    },
                    status="FAILURE"
                )
        
        print(f"\n✅ Corrections terminées : {len(files_modified)} fichiers modifiés\n")
        
        return {
            "files_modified": files_modified,
            "bugs_fixed": bugs_fixed,
            "status": "completed"
        }