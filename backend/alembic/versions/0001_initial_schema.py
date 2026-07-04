r"""initial schema (squashed from 001-008)

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-14

将原始 8 个增量迁移 (001_initial → 008) 合并为单一初始迁移。
建表 DDL 取自 squash 时点已迁到 008 的库的 ``pg_dump --schema-only`` 输出
(已剥离 alembic_version 表定义与 ``\restrict``/``\unrestrict`` psql 元命令)。
对应的 ORM model 漂移 (memory/knowledge_base) 已同步修正。
"""
from __future__ import annotations

import re
from pathlib import Path

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

_DDL_FILE = Path(__file__).with_name("0001_initial_schema.sql")


def _split_sql(ddl: str) -> list[str]:
    """按分号切分 SQL 语句;忽略单引号字符串内、``--`` 行注释内的分号。

    asyncpg 经 SQLAlchemy 在多语句上的行为不稳定,逐条执行更可靠。
    pg_dump 的 ``-- Name: foo; Type: BAR;`` 注释里含分号,必须跳过。
    """
    stmts: list[str] = []
    buf: list[str] = []
    in_str = False
    in_comment = False
    i = 0
    n = len(ddl)
    while i < n:
        ch = ddl[i]
        if in_comment:
            buf.append(ch)
            if ch == "\n":
                in_comment = False
            i += 1
            continue
        if ch == "'":
            if in_str and i + 1 < n and ddl[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_str = not in_str
            buf.append(ch)
        elif ch == "-" and i + 1 < n and ddl[i + 1] == "-" and not in_str:
            in_comment = True
            buf.append("--")
            i += 2
            continue
        elif ch == ";" and not in_str:
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def _has_executable(stmt: str) -> bool:
    """跳过纯注释/空白语句(如 pg_dump 尾部的 'dump complete' 注释)。"""
    for line in stmt.splitlines():
        s = line.strip()
        if s and not s.startswith("--"):
            return True
    return False


def upgrade() -> None:
    ddl = _DDL_FILE.read_text()
    for stmt in _split_sql(ddl):
        if _has_executable(stmt):
            op.execute(sa.text(stmt))


def downgrade() -> None:
    ddl = _DDL_FILE.read_text()
    tables = re.findall(r"CREATE TABLE public\.(\w+)", ddl)
    # 逆序 DROP;CASCADE 兜底 FK/索引/约束依赖,顺序非必须但更直观。
    for table in reversed(tables):
        op.execute(f'DROP TABLE IF EXISTS public."{table}" CASCADE')
    op.execute("DROP EXTENSION IF EXISTS vector")
