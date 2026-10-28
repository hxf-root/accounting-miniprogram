#!/usr/bin/env python3
"""Rehearse create_all in memory; never migrate or print source database contents."""
import argparse
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

# Import model definitions without importing the application or touching its engine.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from database import Base  # noqa: E402
import models  # noqa: E402,F401


def check(path: Path) -> list[str]:
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('source unavailable')
    source = sqlite3.connect('file:' + quote(str(path), safe='/') + '?mode=ro', uri=True)
    memory = sqlite3.connect(':memory:', check_same_thread=False)
    engine = None
    try:
        source.backup(memory)
        if memory.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('integrity check failed')
        original_tables = [r[0] for r in memory.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        if 'users' not in original_tables:
            raise ValueError('missing users table')
        def row_count(table):
            identifier = '"' + table.replace('"', '""') + '"'
            return memory.execute('SELECT COUNT(*) FROM ' + identifier).fetchone()[0]
        counts = {name: row_count(name) for name in original_tables}
        engine = create_engine('sqlite://', creator=lambda: memory, poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        issues = []
        for table in Base.metadata.sorted_tables:
            columns = {col['name']: col for col in inspector.get_columns(table.name)}
            for expected in table.columns:
                actual = columns.get(expected.name)
                if actual is None:
                    issues.append(f'{table.name}: missing column {expected.name}')
                elif not expected.nullable and not expected.primary_key and actual['nullable']:
                    issues.append(f'{table.name}: nullable column {expected.name}')
            primary = tuple(inspector.get_pk_constraint(table.name)['constrained_columns'])
            if primary != tuple(col.name for col in table.primary_key.columns):
                issues.append(f'{table.name}: primary key mismatch')
            actual_indexes = {(tuple(index['column_names']), bool(index['unique']))
                              for index in inspector.get_indexes(table.name)
                              if index.get('dialect_options', {}).get('sqlite_where') is None}
            actual_unique = {tuple(item['column_names']) for item in inspector.get_unique_constraints(table.name)}
            actual_unique |= {columns for columns, unique in actual_indexes if unique}
            for constraint in table.constraints:
                if constraint.__class__.__name__ == 'UniqueConstraint':
                    cols = tuple(col.name for col in constraint.columns)
                    if cols not in actual_unique:
                        issues.append(f'{table.name}: missing unique constraint {",".join(cols)}')
            for index in table.indexes:
                cols = tuple(col.name for col in index.columns)
                if (cols, bool(index.unique)) not in actual_indexes:
                    issues.append(f'{table.name}: missing index {",".join(cols)}')
        if any(row_count(name) != count for name, count in counts.items()):
            issues.append('original row counts changed')
        if memory.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            issues.append('integrity check failed after rehearsal')
        return issues
    finally:
        source.close()
        if engine is not None:
            engine.dispose()
        else:
            memory.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    args = parser.parse_args()
    try:
        issues = check(args.database)
    except Exception:
        print('Schema rehearsal failed; source was not modified.', file=sys.stderr)
        return 1
    if issues:
        for issue in issues:
            print(issue)
        print('Schema rehearsal found incompatibilities; do not deploy.')
        return 1
    print('Schema rehearsal passed; constraints, types, values and production cutover still need independent validation.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
