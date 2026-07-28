"""Create the `observation` table inside an existing GeoPackage and
generate campaign rows for it — no PyQGIS involved, just sqlite3.

Run this outside QGIS entirely (plain `python3 setup_observations.py`),
or import its functions from a QGIS Python console if you want a menu
button later. Either way, the logic is identical because it never
touches qgis.core.
"""

import sqlite3
from pathlib import Path

POINT_LAYER_NAME = "vine_samples"
POINT_ID_FIELD = "fid"

OBSERVATION_TABLE_NAME = "observation"
OBSERVATION_TABLE_SCHEMA = """
    CREATE TABLE {table} (
        fid INTEGER PRIMARY KEY NOT NULL,
        point_id INTEGER NOT NULL,
        item_no INTEGER NOT NULL,
        mildew_leaf_pct INTEGER,
        mildew_grape_pct INTEGER,
        powdery_mildew_pct INTEGER,
        phenology VARCHAR(2),
        UNIQUE (point_id, item_no),
        FOREIGN KEY (point_id) REFERENCES {point_layer}({point_id_field})
    );
"""

GPKG_CONTENTS_INSERT = """
    INSERT INTO gpkg_contents (table_name, data_type, identifier)
    VALUES (?, 'attributes', ?);
"""


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Check whether a table already exists in the database."""
    query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;"
    result = connection.execute(query, (table_name,)).fetchone()
    return result is not None


def create_observation_table(connection: sqlite3.Connection) -> None:
    """Create the observation table and register it in gpkg_contents.

    Does nothing if the table already exists, so it's safe to re-run.
    """
    if table_exists(connection, OBSERVATION_TABLE_NAME):
        print(f"'{OBSERVATION_TABLE_NAME}' already exists, skipping creation.")
        return

    create_statement = OBSERVATION_TABLE_SCHEMA.format(
        table=OBSERVATION_TABLE_NAME,
        point_layer=POINT_LAYER_NAME,
        point_id_field=POINT_ID_FIELD,
    )
    connection.execute(create_statement)
    connection.execute(
        GPKG_CONTENTS_INSERT, (OBSERVATION_TABLE_NAME, OBSERVATION_TABLE_NAME)
    )
    connection.commit()
    print(f"Created '{OBSERVATION_TABLE_NAME}' and registered it in gpkg_contents.")


def get_point_ids(connection: sqlite3.Connection) -> list:
    """Return every point id (fid) in the sampling layer."""
    query = f"SELECT {POINT_ID_FIELD} FROM {POINT_LAYER_NAME};"
    return [row[0] for row in connection.execute(query).fetchall()]


def generate_campaign_rows(connection: sqlite3.Connection, items_per_point: int) -> int:
    """Insert one empty observation row per (point, item), for every
    point currently in the sampling layer.

    Uses the UNIQUE(point_id, item_no) constraint plus INSERT OR IGNORE
    to make this idempotent: re-running with the same items_per_point
    only fills in rows that don't already exist, never duplicates.

    Returns the number of rows actually inserted.
    """
    point_ids = get_point_ids(connection)
    insert_statement = f"""
        INSERT OR IGNORE INTO {OBSERVATION_TABLE_NAME} (point_id, item_no)
        VALUES (?, ?);
    """
    rows_to_insert = [
        (point_id, item_no)
        for point_id in point_ids
        for item_no in range(1, items_per_point + 1)
    ]

    cursor = connection.executemany(insert_statement, rows_to_insert)
    connection.commit()
    return cursor.rowcount if cursor.rowcount != -1 else len(rows_to_insert)


def setup_and_generate(gpkg_path: str, items_per_point: int) -> None:
    """End-to-end: create the table if needed, then generate rows."""
    connection = sqlite3.connect(gpkg_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        create_observation_table(connection)
        rows_created = generate_campaign_rows(connection, items_per_point)
        total_rows = connection.execute(
            f"SELECT COUNT(*) FROM {OBSERVATION_TABLE_NAME};"
        ).fetchone()[0]
        print(f"Inserted {rows_created} new row(s). Table now has {total_rows} row(s).")
    finally:
        connection.close()


if __name__ == "__main__":
    gpkg_file = Path(__file__).parent / "montmartre_2026.gpkg"
    setup_and_generate(str(gpkg_file), items_per_point=10)
