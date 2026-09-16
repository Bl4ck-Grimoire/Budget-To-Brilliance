import logging
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from config import get_sqlalchemy_url

log = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
QUERIES_SQL_PATH = Path("sql/analytical_queries.sql")

# Matches header comments like "-- R1: Official vs. non-official gap, by period"
_BLOCK_HEADER_RE = re.compile(r"^--\s*(R\d+):\s*(.+)$")


def _parse_queries(sql_path: Path = QUERIES_SQL_PATH) -> list[dict]:
    lines = sql_path.read_text(encoding="utf-8").splitlines()

    blocks = []
    current = None
    for line in lines:
        match = _BLOCK_HEADER_RE.match(line.strip())
        if match:
            if current is not None:
                blocks.append(current)
            current = {"id": match.group(1), "title": match.group(2), "raw_lines": []}
        elif current is not None:
            current["raw_lines"].append(line)
    if current is not None:
        blocks.append(current)

    queries = []
    for block in blocks:
        sql_lines = [l for l in block["raw_lines"] if not l.strip().startswith("--")]
        sql_text = "\n".join(sql_lines).strip()
        # Only keep the first statement of the block (up to its ";")
        first_statement = sql_text.split(";")[0].strip()
        if first_statement:
            queries.append({"id": block["id"], "title": block["title"], "sql": first_statement})
    return queries


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_(no rows returned)_"
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    rows = [
        "| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([header, separator] + rows)


def generar_reportes(output_dir: Path = PROCESSED_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = _parse_queries()

    if not queries:
        log.warning("[REPORT] no queries found in %s -- nothing generated", QUERIES_SQL_PATH)
        return []

    md_parts = [
        "# Analytical Results (R1-R5)",
        "",
        "Generated automatically by `python src/main.py` from the live MySQL "
        "Data Warehouse -- not a static file.",
    ]

    engine = create_engine(get_sqlalchemy_url())
    written_paths = []
    try:
        with engine.connect() as db_conn:
            for q in queries:
                df = pd.read_sql(q["sql"], db_conn)

                csv_path = output_dir / f"{q['id']}_{_slugify(q['title'])}.csv"
                df.to_csv(csv_path, index=False)
                written_paths.append(csv_path)
                log.info("[REPORT] %s: %s rows written to %s", q["id"], len(df), csv_path)

                md_parts.append(f"\n## {q['id']} -- {q['title']}\n")
                md_parts.append(_df_to_markdown(df))
    finally:
        engine.dispose()

    md_path = output_dir / "analytical_results.md"
    md_path.write_text("\n".join(md_parts) + "\n", encoding="utf-8")
    written_paths.append(md_path)
    log.info("[REPORT] consolidated report written to %s", md_path)

    return written_paths
