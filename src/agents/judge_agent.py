"""
judge_agent.py - Agent Juge (LLM-augmented)
Valide le code via syntax check, pylint, pytest,
puis délègue l'évaluation finale à un LLM (Gemini)
"""

import os
import json
import time
import py_compile
import subprocess
from pathlib import Path
from google import generativeai as genai
from src.utils.logger import log_experiment, ActionType
from src.tools.test_runner import run_pytest_on_directory


class JudgeAgent:
    """
    Agent responsable de la validation finale du code.
    Combine des outils déterministes + analyse LLM.
    """

    def __init__(self):
        """Initialise l'agent Juge avec LLM"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY non trouvée dans .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.system_prompt = self._load_tester_prompt()

        print("✅ Juge initialisé (pytest + pylint + LLM QA)")

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------
    def _load_tester_prompt(self) -> str:
        prompt_path = Path("src/prompts/tester_prompt.txt")
        if not prompt_path.exists():
            raise FileNotFoundError("tester_prompt.txt introuvable")
        return prompt_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # GATE 1 — Syntax validation
    # ------------------------------------------------------------------
    def _run_syntax_check(self, target_directory: Path) -> dict:
        errors = []

        for py_file in target_directory.rglob("*.py"):
            try:
                py_compile.compile(py_file, doraise=True)
            except Exception as e:
                errors.append({
                    "file": str(py_file),
                    "error_type": type(e).__name__,
                    "message": str(e)
                })

        return {
            "passed": len(errors) == 0,
            "errors": errors
        }

    # ------------------------------------------------------------------
    # GATE 2 — Pylint analysis
    # ------------------------------------------------------------------
    def _run_pylint(self, target_directory: Path) -> dict:
        try:
            result = subprocess.run(
                ["pylint", str(target_directory)],
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr

            score = None
            for line in output.splitlines():
                if "Your code has been rated at" in line:
                    score = float(line.split("/")[0].split()[-1])
                    break

            violations = []
            for line in output.splitlines():
                if line.startswith(("E", "W", "R", "C")):
                    violations.append(line.strip())

            return {
                "executed": True,
                "score": score,
                "violations": violations,
                "raw_output": output
            }

        except Exception as e:
            return {
                "executed": False,
                "error": str(e)
            }

    # ------------------------------------------------------------------
    # GATE 3 — Pytest execution
    # ------------------------------------------------------------------
    def _run_tests(self, target_directory: Path) -> dict:
        start = time.time()
        result = run_pytest_on_directory(str(target_directory))
        duration = round(time.time() - start, 2)

        return {
            "passed_count": result.get("passed_count", 0),
            "failed_count": result.get("failed_count", 0),
            "total_count": result.get("total_count", 0),
            "error_logs": result.get("error_logs", []),
            "execution_time_seconds": duration
        }

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------
    def validate(
        self,
        target_directory: Path,
        audit_plan: dict,
        iteration_count: int
    ) -> dict:
        """
        Exécute toutes les validations puis appelle le LLM pour verdict final.
        """

        print(f"⚖️  Validation du code : {target_directory} (itération {iteration_count})\n")

        # -------------------------
        # Collect evidence
        # -------------------------
        syntax_result = self._run_syntax_check(target_directory)
        pylint_result = self._run_pylint(target_directory)
        pytest_result = self._run_tests(target_directory)

        evidence = {
            "iteration_count": iteration_count,
            "syntax_check": syntax_result,
            "static_analysis": pylint_result,
            "functional_tests": pytest_result,
            "audit_issues": audit_plan.get("issues", [])
        }

        # -------------------------
        # Call LLM
        # -------------------------
        user_prompt = f"""
Voici les preuves de validation (JSON factuel, ne rien inventer) :

{json.dumps(evidence, indent=2)}

Analyse STRICTEMENT selon les règles.
Retourne UNIQUEMENT un JSON valide.
"""

        response = self.model.generate_content(
            f"{self.system_prompt}\n\n{user_prompt}"
        )

        # -------------------------
        # Parse LLM output
        # -------------------------
        try:
            verdict = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Réponse LLM invalide (JSON attendu): {e}\n{response.text}"
            )

        # -------------------------
        # Logging
        # -------------------------
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-2.5-flash",
            action=ActionType.DEBUG,
            details={
                "iteration": iteration_count,
                "evidence_summary": {
                    "syntax_passed": syntax_result["passed"],
                    "pylint_score": pylint_result.get("score"),
                    "tests_failed": pytest_result["failed_count"]
                },
                "llm_verdict": verdict
            },
            status=verdict.get("validation_result", "UNKNOWN")
        )

        # -------------------------
        # Human-readable output
        # -------------------------
        print("📋 Verdict du Juge :")
        print(json.dumps(verdict, indent=2))
        print()

        return {
            "validation_result": verdict.get("validation_result"),
            "next_action": verdict.get("next_action"),
            "verdict": verdict,
            "status": "completed"
        }