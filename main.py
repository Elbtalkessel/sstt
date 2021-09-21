#!/usr/bin/env python3
import enum
import math
import typing
from contextlib import contextmanager
import argparse
import sqlite3
from datetime import datetime
import os
from collections import namedtuple
from datetime import datetime


# I expect this to be called via symlink
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
TABLE = 'tracking'
Report = namedtuple('Report', ['slug', 'issue', 'created_at', 'closed_at'])


class CountEntity(str, enum.Enum):
    CLOSED = 'closed'
    OPEN = 'open'


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init():
    with connection() as c:
        sql = f"""
        CREATE TABLE {TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug CHAR(50) NOT NULL,
        issue INT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        closed_at TIMESTAMP
        );
        """
        c.execute(sql)


def truncate():
    with connection() as c:
        c.execute(f'DELETE from {TABLE}')


def close(slug: typing.Optional[str] = None, issue: typing.Optional[str] = None):
    now = datetime.now()
    with connection() as c:
        sql = f'UPDATE {TABLE} SET closed_at = ? WHERE closed_at IS NULL'
        if slug is None or issue is None:
            c.execute(sql, (now,))
            return
        sql = f"{sql} AND slug = ? AND issue = ?"
        c.execute(sql, (now, slug, issue))


def delete(slug: str, issue: typing.Optional[str] = None):
    with connection() as c:
        sql = f'DELETE FROM {TABLE} WHERE slug = ?'
        args = [slug]
        if issue:
            sql += ' AND issue = ?'
            args.append(issue)
        c.execute(sql, args)


def start(slug: str, issue: str):
    now = datetime.now()
    with connection() as c:
        cursor = c.execute(f'SELECT slug, issue FROM {TABLE} WHERE closed_at IS NULL')
        for row in cursor:
            close(row[0], row[1])
        sql = f"""
        INSERT INTO {TABLE} (slug, issue, created_at) VALUES (?, ?, ?)
        """
        c.execute(sql, (slug, issue, now))


def toggle(slug: str, issue: str) -> bool:
    """
    Closes an issue if open, opens if closed. Returns True if open and False if closed.
    """
    with connection() as c:
        open_id = c.execute(f'SELECT id FROM {TABLE} WHERE closed_at IS NULL AND slug = ? AND issue = ?', (slug, issue)).fetchone()
        (close if open_id else start)(slug, issue)



def report():
    with connection() as c:
        cursor = c.execute(f'SELECT {",".join(Report._fields)} FROM {TABLE} ORDER BY created_at desc')
        tfmt = '%H:%M'
        rows = cursor.fetchall()
        for row in rows:
            report = Report(*row)
            created_at = datetime.fromisoformat(report.created_at).strftime(tfmt)
            if report.closed_at:
                closed_at = datetime.fromisoformat(report.closed_at).strftime(tfmt)
            else:
                closed_at = 'not yet'
            print(f'{report.slug}#{report.issue} {created_at}-{closed_at}')


def count(entity: CountEntity):
    entity = CountEntity(entity)
    sql = None
    if entity == CountEntity.CLOSED:
        sql = f'SELECT COUNT(id) from {TABLE} WHERE closed_at NOT NULL'
    if entity == CountEntity.OPEN:
        sql = f'SELECT COUNT(id) from {TABLE} WHERE closed_at IS NULL'
    with connection() as c:
        cursor = c.execute(sql)
        non_reported_count = cursor.fetchone()
        print(non_reported_count[0] if non_reported_count else 0)


def time(entity: CountEntity, slug: typing.Optional[str] = None, issue: typing.Optional[str] = None):
    entity = CountEntity(entity)

    where = []
    params = []
    select = ''
    end = ''

    if slug:
        where.append('slug = ?')
        params.append(slug)
    if issue:
        where.append('issue = ?')
        params.append(issue)


    if entity == CountEntity.CLOSED:
        where.append('closed_at NOT NULL')
        select = 'ROUND((JULIANDAY(closed_at) - JULIANDAY(created_at)) * 86400)'
    if entity == CountEntity.OPEN:
        where.append('closed_at IS NULL')
        end = 'LIMIT 1'
        select = 'created_at'

    sql = f'SELECT {select} FROM {TABLE} WHERE {" AND ".join(where)} {end}'

    with connection() as c:
        result = c.execute(sql, params).fetchone()
        result = result[0] if isinstance(result, tuple) else result
        seconds = 0

        if result and entity == CountEntity.CLOSED:
            seconds = result
        elif result and entity == CountEntity.OPEN:
            created_at = datetime.strptime(result, '%Y-%m-%d %H:%M:%S.%f')
            seconds = (datetime.now() - created_at).seconds

        minutes = seconds / 60
        hours = minutes / 60
        if hours > 1:
            print(f'{round(hours)}h')
        elif minutes > 1:
            print(f'{round(minutes)}m')
        else:
            print(f'{round(seconds)}s')


def main():
    funcs = {
        'init': init,

        'start': start,
        'open': start,

        'close': close,
        'stop': close,
        'done': close,
        'toggle': toggle,

        'truncate': truncate,
        'delete': delete,

        'report': report,
        'count': count,
        'time': time,
    }

    args = argparse.ArgumentParser()
    args.add_argument("function", default='report', choices=funcs.keys())
    args.add_argument("arguments", nargs=argparse.REMAINDER)
    args = args.parse_args()

    funcs[args.function](*args.arguments)

if __name__ == '__main__':
    main()

