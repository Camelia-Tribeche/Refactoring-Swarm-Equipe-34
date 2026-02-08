"""
fixer_agent.py - Agent Correcteur (VERSION DEBUG + ULTRA-FIXÉE + EXCEPTION DETECTION)
Inclut des prints de debug pour comprendre pourquoi les tests échouent
🔥 NEW: Détecte les erreurs de type d'exception (ValueError vs ZeroDivisionError)
"""
import os
import json
import ast
import re
from google import generativeai as genai
from pathlib import Path
from src.utils.logger import log_experiment, ActionType
from src.tools.file_manager import read_file_safe, write_file_safe


class FixerAgent:
    """
    Agent responsable de la correction du code
    VERSION DEBUG: Affiche ce qui se passe
    """
    
    def __init__(self):
        """Initialise l'agent Correcteur avec le LLM"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY non trouvée dans .env")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "stop_sequences": []  # Empêche l'arrêt prématuré
            }
        )
        
        # Charger le prompt système
        self.system_prompt = self._load_system_prompt()
        
        print("✅ Correcteur initialisé (Gemini 2.5 Flash)")
    
    def _load_system_prompt(self) -> str:
        """Charge le prompt système depuis le fichier"""
        prompt_path = Path("src/prompts/fixer_prompt.txt")
        if not prompt_path.exists():
            raise FileNotFoundError(
                "Le fichier src/prompts/fixer_prompt.txt est requis!"
            )
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_function_signatures(self, code: str) -> dict:
        """Extrait toutes les signatures de fonctions du code"""
        signatures = {}
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    
                    # Extraire les noms de paramètres
                    param_names = []
                    for arg in node.args.args:
                        param_names.append(arg.arg)
                    
                    # Extraire les valeurs par défaut
                    defaults = []
                    for default in node.args.defaults:
                        if isinstance(default, ast.Constant):
                            defaults.append(default.value)
                        else:
                            defaults.append(None)
                    
                    signatures[func_name] = {
                        'params': param_names,
                        'defaults': defaults,
                        'line': node.lineno
                    }
        
        except Exception as e:
            print(f"      ⚠️ Erreur extraction signatures: {e}")
        
        return signatures
    
    def _get_function_list_from_code(self, code: str) -> list:
        """Extrait la liste des noms de fonctions du code"""
        try:
            tree = ast.parse(code)
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):
                        functions.append(node.name)
            return functions
        except:
            # Fallback: regex
            return re.findall(r'^\s*def\s+([a-zA-Z_]\w*)\s*\(', code, re.MULTILINE)
    
    def _validate_signatures_preserved(self, original_code: str, fixed_code: str) -> tuple[bool, list]:
        """Vérifie que toutes les signatures sont préservées"""
        original_sigs = self._extract_function_signatures(original_code)
        fixed_sigs = self._extract_function_signatures(fixed_code)
        
        violations = []
        
        for func_name, orig_sig in original_sigs.items():
            if func_name.startswith('_'):
                continue
            
            if func_name not in fixed_sigs:
                violations.append(f"Function '{func_name}' was removed or renamed!")
                continue
            
            fixed_sig = fixed_sigs[func_name]
            
            if orig_sig['params'] != fixed_sig['params']:
                violations.append(
                    f"Function '{func_name}': parameters changed from "
                    f"{orig_sig['params']} to {fixed_sig['params']}"
                )
        
        return len(violations) == 0, violations
    
    def _validate_code_completeness(self, code: str, original_code: str) -> bool:
        """Vérifie que le code généré est complet"""
        code_stripped = code.rstrip()
        
        # Vérifications basiques
        suspicious_endings = ['# ', 'def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ', '=', '+', '-', '*']
        
        for ending in suspicious_endings:
            if code_stripped.endswith(ending):
                print(f"      ⚠️ Fin suspecte: '{ending}'")
                return False
        
        if len(code_stripped) < 50:
            print(f"      ⚠️ Code trop court: {len(code_stripped)} chars")
            return False
        
        # Compter les fonctions
        original_funcs = self._get_function_list_from_code(original_code)
        generated_funcs = self._get_function_list_from_code(code)
        
        if len(generated_funcs) < len(original_funcs):
            print(f"      ⚠️ Fonctions manquantes: {len(generated_funcs)}/{len(original_funcs)}")
            print(f"         Original: {original_funcs}")
            print(f"         Generated: {generated_funcs}")
            return False
        
        # Vérifier syntaxe
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            print(f"      ⚠️ Erreur syntaxe: {e}")
            return False
        
        return True
    
    def _validate_python_syntax(self, code: str) -> tuple[bool, str]:
        """Valide si le code est du Python valide"""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Parse error: {str(e)}"
    
    def _analyze_test_errors_deeply(self, error_logs: list) -> str:
        """
        🔥 ANALYSE VRAIMENT les erreurs de tests + DEBUG
        🔥 NEW: Détecte les erreurs de type d'exception!
        """
        print(f"\n      🔍 DEBUG: Analyse de {len(error_logs) if error_logs else 0} erreurs de tests")
        
        if not error_logs or len(error_logs) == 0:
            print(f"      🔍 DEBUG: Aucune erreur de test à analyser")
            return ""
        
        print(f"      🔍 DEBUG: Erreurs reçues:")
        for i, err in enumerate(error_logs[:3]):  # Afficher les 3 premières
            print(f"         Error {i+1}: test={err.get('test', 'N/A')[:50]}")
            print(f"                 message={err.get('message', 'N/A')[:80]}")
        
        analysis = "\n" + "="*60 + "\n"
        analysis += "🧪 TEST FAILURES - YOU MUST FIX THESE:\n"
        analysis += "="*60 + "\n\n"
        
        for i, error in enumerate(error_logs, 1):
            test_name = error.get("test", "unknown_test")
            message = error.get("message", "")
            traceback = error.get("traceback", "")
            
            analysis += f"❌ FAILED TEST #{i}: {test_name}\n"
            
        
            # Extraire le nom de la fonction automatiquement depuis le test
            func_name = "unknown"

            # Si le test suit la convention "test_<function_name>_..."
            match = re.match(r'test_([a-zA-Z0-9_]+)', test_name)
            if match:
              func_name = match.group(1)
            # Analyser le type d'erreur
            
            combined_error = (message + " " + traceback).lower()

            if "with pytest.raises" in traceback.lower():
            # logique exception automatique
               exc_match = re.search(r'with pytest\.raises\((\w+)\)', traceback, re.IGNORECASE)
               expected_exc = exc_match.group(1) if exc_match else None
    
               raised_exc = None
               for exc_type in ['ValueError', 'ZeroDivisionError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError']:
                  if exc_type.lower() in combined_error:
                    raised_exc = exc_type
                    break
    
               if expected_exc and raised_exc and expected_exc.lower() != raised_exc.lower():
                  analysis += f"   Error type: ❌ WRONG EXCEPTION TYPE\n"
                  analysis += f"   🔧 ACTION: In '{func_name}', change 'raise {raised_exc}' to 'raise {expected_exc}'\n"
               elif expected_exc and not raised_exc:
                  analysis += f"   Error type: ❌ MISSING EXCEPTION\n"
                  analysis += f"   🔧 ACTION: Add 'raise {expected_exc}(...)' in '{func_name}'\n"

               elif "assert" in combined_error:
                  analysis += f"   Error type: ❌ ASSERTION FAILED (wrong output)\n"
                  analysis += f"   🔧 ACTION REQUIRED: Fix the LOGIC inside function '{func_name}'\n"

               elif "import" in combined_error or "module" in combined_error:
                  analysis += f"   Error type: ❌ IMPORT ERROR\n"
                  analysis += f"   🔧 Function '{func_name}' might be missing from file\n"

               else:
                  analysis += f"   Error type: ❌ UNKNOWN ERROR\n"
                  analysis += f"   🔧 ACTION REQUIRED in function '{func_name}'\n"
         
        print(f" 🔍 DEBUG: Analyse générée ({len(analysis)} chars)") 
                  
        return analysis

    
    def _clean_response_safely(self, response_text: str) -> str:
        """Nettoie la réponse du LLM"""
        cleaned = response_text.strip()
        
        # Enlever markdown
        if "```python" in cleaned:
            match = re.search(r'```python\s*\n(.*?)```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
        elif "```" in cleaned:
            match = re.search(r'```\s*\n(.*?)```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
        
        # Enlever marqueurs
        patterns_to_remove = [
            r'^##+\s*FIXED CODE.*$',
            r'^##+\s*CORRECTED.*$',
            r'^##+\s*SOLUTION.*$',
            r'^##+\s*START.*$',
            r'^##+\s*END.*$',
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        
        return cleaned.strip()
    
    def fix(self, plan: dict, error_logs: list = None, max_retries: int = 3) -> dict:
        """
        Applique les corrections avec DEBUG MODE
        """
        print("🔧 Application des corrections...\n")
        
        print(f"   🔍 DEBUG: error_logs={'None' if error_logs is None else f'{len(error_logs)} errors'}")
        
        if error_logs and len(error_logs) > 0:
            print(f"   🔄 Mode Self-Healing : {len(error_logs)} erreurs à traiter\n")
        
        files_modified = []
        bugs_fixed = 0
        
        for file_issue in plan.get("issues", []):
            file_path = file_issue.get("file", "")
            issues_list = file_issue.get("issues", [])
            
            if not file_path or not issues_list:
                continue
            
            print(f"   📝 Correction : {Path(file_path).name}")
            print(f"      🐛 {len(issues_list)} problèmes à corriger")
            
            # Lire code original
            try:
                original_code = read_file_safe(file_path)
                is_orig_valid, _ = self._validate_python_syntax(original_code)
                if is_orig_valid:
                    print(f"      ℹ️  Code original syntaxiquement valide")
            except Exception as e:
                print(f"      ⚠️ Impossible de lire: {e}")
                continue
            
            original_funcs = self._get_function_list_from_code(original_code)
            print(f"      🔍 DEBUG: Fonctions originales: {original_funcs}")
            
            # Retry loop
            for attempt in range(max_retries + 1):
                try:
                    # Construire le prompt
                    issues_summary = "\n".join([
                        f"- [{i.get('priority', 'MEDIUM')}] Line {i.get('line', '?')}: {i.get('description', 'Issue')} → {i.get('suggestion', 'Fix')}"
                        for i in issues_list[:10]
                    ])
                    
                    # 🔥 Analyse des erreurs
                    test_error_analysis = ""
                    if error_logs and len(error_logs) > 0:
                        test_error_analysis = self._analyze_test_errors_deeply(error_logs)
                    else:
                        print(f"      🔍 DEBUG: Pas d'erreurs de tests (première itération ou erreurs vides)")
                    
                    retry_note = ""
                    if attempt > 0:
                        retry_note = f"""
╔═══════════════════════════════════════════════════════════╗
║   ⚠️  RETRY #{attempt + 1}/{max_retries + 1} - PREVIOUS FAILED!  ⚠️    ║
╚═══════════════════════════════════════════════════════════╝

Your previous attempt was INCOMPLETE or had WRONG LOGIC.
You MUST do better this time!

CRITICAL: Include ALL {len(original_funcs)} functions and fix the LOGIC errors!

"""
                    
                    # Liste des fonctions
                    functions_checklist = "\n".join([
                        f"   - Function '{func}' (REQUIRED)"
                        for func in original_funcs
                    ])
                    
                    user_prompt = f"""You are fixing a Python file. Generate the COMPLETE corrected code.

📁 File: {Path(file_path).name}
📊 Original: {len(original_code)} chars, {len(original_funcs)} functions

🐛 Issues from audit:
{issues_summary}

{test_error_analysis}

📋 FUNCTIONS YOU MUST INCLUDE:
{functions_checklist}

📄 Current code:
```python
{original_code}
```

{retry_note}

╔═══════════════════════════════════════════════════════════╗
║                  CRITICAL INSTRUCTIONS                     ║
╚═══════════════════════════════════════════════════════════╝

1. Return ONLY Python code (no markdown, no explanations)
2. Include ALL {len(original_funcs)} functions
3. Fix syntax errors (missing colons)
4. Fix EXCEPTION TYPE mismatches (see test failures - change ValueError to ZeroDivisionError if needed!)
5. Fix LOGIC errors (wrong formulas - see test failures above!)
6. Add docstrings
7. PRESERVE function names: {', '.join(original_funcs)}
8. PRESERVE parameter names
9. Minimum {int(len(original_code) * 0.7)} characters

⚠️  SELF-CHECK BEFORE RESPONDING:
   ✓ ALL {len(original_funcs)} functions included?
   ✓ Each function COMPLETE?
   ✓ Function names preserved?
   ✓ Exception types match tests?
   ✓ LOGIC bugs fixed (check test errors)?

START WITH CODE. END WITH CODE. NO MARKDOWN."""
                    
                    # Appel LLM
                    full_prompt = f"{self.system_prompt}\n\n{user_prompt}"
                    response = self.model.generate_content(full_prompt)
                    
                    corrected_code = self._clean_response_safely(response.text)
                    
                    print(f"      📏 Longueur: {len(corrected_code)} chars (original: {len(original_code)})")
                    gen_funcs = self._get_function_list_from_code(corrected_code)
                    print(f"      🔢 Fonctions: {len(gen_funcs)}/{len(original_funcs)}")
                    print(f"      🔍 DEBUG: Fonctions générées: {gen_funcs}")
                    
                    if len(gen_funcs) < len(original_funcs):
                        print(f"         ⚠️ Manquantes: {set(original_funcs) - set(gen_funcs)}")
                    
                    # VALIDATIONS
                    if not self._validate_code_completeness(corrected_code, original_code):
                        print(f"      ⚠️ Tentative {attempt + 1}: Code incomplet")
                        if attempt < max_retries:
                            continue
                        else:
                            print(f"      ❌ Échec: Code original conservé")
                            corrected_code = original_code
                    
                    is_valid, error_msg = self._validate_python_syntax(corrected_code)
                    if not is_valid:
                        print(f"      ⚠️ Tentative {attempt + 1}: Syntaxe invalide: {error_msg}")
                        if attempt < max_retries:
                            continue
                        else:
                            print(f"      ❌ Échec syntaxe")
                            break
                    
                    sigs_valid, violations = self._validate_signatures_preserved(original_code, corrected_code)
                    if not sigs_valid:
                        print(f"      🚨 Signatures modifiées!")
                        for v in violations:
                            print(f"         - {v}")
                        
                        if attempt < max_retries:
                            continue
                        else:
                            corrected_code = original_code
                    
                    # Écrire
                    write_file_safe(file_path, corrected_code)
                    
                    files_modified.append(file_path)
                    bugs_fixed += len(issues_list)
                    
                    print(f"      ✅ Fichier corrigé (tentative {attempt + 1})")
                    
                    log_experiment(
                        agent_name="Fixer_Agent",
                        model_used="gemini-2.5-flash",
                        action=ActionType.FIX,
                        details={
                            "file_fixed": file_path,
                            "input_prompt": user_prompt[:500],
                            "output_response": corrected_code[:500],
                            "issues_count": len(issues_list),
                            "had_previous_errors": bool(error_logs),
                            "error_logs_count": len(error_logs) if error_logs else 0,
                            "attempt_number": attempt + 1,
                            "signatures_preserved": sigs_valid,
                            "functions_generated": gen_funcs,
                            "functions_expected": original_funcs
                        },
                        status="SUCCESS"
                    )
                    
                    break
                    
                except Exception as e:
                    print(f"      ❌ Erreur (tentative {attempt + 1}): {e}")
                    if attempt >= max_retries:
                        log_experiment(
                            agent_name="Fixer_Agent",
                            model_used="gemini-2.5-flash",
                            action=ActionType.DEBUG,
                            details={
                                "file_fixed": file_path,
                                "input_prompt": "Error occurred",
                                "output_response": str(e),
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