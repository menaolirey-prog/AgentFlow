"""Aplica un archivo SQL en una transacción. Uso: python scripts/apply_migration.py sql/migrations/001_x.sql"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database import obtener_conexion

with obtener_conexion() as conexion:  # commit al salir; rollback si hay excepción
    conexion.execute(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("OK:", sys.argv[1])
