import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

# --- Academic periods to process (year-semester) ----------------------
PERIODOS = [
    "2021-2", "2022-1", "2022-2", "2023-1", "2023-2",
    "2024-1", "2024-2", "2025-1", "2025-2",
]

# --- Paths --------------------------------------------------------------
RAW_DATA_DIR = Path(os.getenv("ICFES_RAW_DIR", "data/raw"))
CHUNK_SIZE = int(os.getenv("ICFES_CHUNK_SIZE", "100000"))


def periodo_a_nombre_archivo(periodo: str) -> str:
    """'2021-2' -> 'Examen_Saber_11_20212.txt' (DataIcfes' real file pattern)."""
    codigo = periodo.replace("-", "")
    return f"Examen_Saber_11_{codigo}.txt"


# --- Database (Data Warehouse) -----------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/icfes_dw")
_url = make_url(DATABASE_URL)

DB_CONFIG = {
    "host": _url.host or "localhost",
    "port": _url.port or 3306,
    "dbname": _url.database,
    "user": _url.username,
    "password": _url.password or "",
}


def get_sqlalchemy_url() -> str:
    return DATABASE_URL
