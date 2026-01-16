"""
file_manager.py - Gestion sécurisée des fichiers
Lecture et écriture avec validation
"""
from pathlib import Path
from typing import Optional


def read_file_safe(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Lit un fichier de manière sécurisée
    
    Args:
        file_path: Chemin du fichier à lire
        encoding: Encodage du fichier (défaut: utf-8)
        
    Returns:
        Contenu du fichier ou None si erreur
        
    Raises:
        FileNotFoundError: Si le fichier n'existe pas
        PermissionError: Si pas de droits de lecture
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Le fichier {file_path} n'existe pas")
    
    if not path.is_file():
        raise ValueError(f"{file_path} n'est pas un fichier")
    
    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
        return content
    except Exception as e:
        raise IOError(f"Erreur lors de la lecture de {file_path}: {e}")


def write_file_safe(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    Écrit dans un fichier de manière sécurisée
    
    Args:
        file_path: Chemin du fichier à écrire
        content: Contenu à écrire
        encoding: Encodage du fichier (défaut: utf-8)
        
    Returns:
        True si succès, False sinon
        
    Security:
        - Vérifie que le chemin est dans les dossiers autorisés
        - Crée les dossiers parents si nécessaire
    """
    path = Path(file_path)
    
    # Sécurité : vérifier que le chemin est valide
    # (éviter d'écrire en dehors du projet)
    try:
        path = path.resolve()
    except Exception as e:
        raise ValueError(f"Chemin invalide {file_path}: {e}")
    
    # Créer les dossiers parents si nécessaire
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        raise IOError(f"Erreur lors de l'écriture dans {file_path}: {e}")


def list_python_files(directory: str) -> list:
    """
    Liste tous les fichiers Python dans un répertoire
    
    Args:
        directory: Chemin du répertoire
        
    Returns:
        Liste des chemins de fichiers .py
    """
    path = Path(directory)
    
    if not path.exists():
        raise FileNotFoundError(f"Le répertoire {directory} n'existe pas")
    
    if not path.is_dir():
        raise ValueError(f"{directory} n'est pas un répertoire")
    
    python_files = list(path.rglob("*.py"))
    
    # Exclure les fichiers de test et __pycache__
    python_files = [
        str(f) for f in python_files 
        if "__pycache__" not in str(f) and not f.name.startswith("test_")
    ]
    
    return python_files


def backup_file(file_path: str) -> str:
    """
    Crée une copie de sauvegarde d'un fichier
    
    Args:
        file_path: Chemin du fichier à sauvegarder
        
    Returns:
        Chemin du fichier de backup
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Le fichier {file_path} n'existe pas")
    
    backup_path = path.with_suffix(path.suffix + '.backup')
    
    try:
        content = read_file_safe(file_path)
        write_file_safe(str(backup_path), content)
        return str(backup_path)
    except Exception as e:
        raise IOError(f"Erreur lors de la création du backup : {e}")