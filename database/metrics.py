from sqlalchemy import text

from database.postgres_sql import get_engine


def get_metrics():
    engine = get_engine()

    # Keep only the newest record for each company and year. If multiple records
    # exist for the same company-year, return the one with the latest created_at timestamp.
    query = """
    SELECT *
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY company, year
                   ORDER BY created_at DESC
               ) AS rn
        FROM financial_metrics
    ) t
    WHERE rn = 1
    ORDER BY company
    """

    with engine.connect() as connection:
        result = connection.execute(text(query))
        rows = [dict(row._mapping) for row in result]

    return rows