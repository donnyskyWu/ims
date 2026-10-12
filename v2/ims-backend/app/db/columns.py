"""列声明帮手。"""
from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import mapped_column

from app.db.refs import NotARef, RefSpec


def ref_column(ref: RefSpec, nullable: bool = True):
    return mapped_column(BigInteger, nullable=nullable, info={"ref": ref})


def plain_id(nullable: bool = True):
    return mapped_column(BigInteger, nullable=nullable, info={"not_a_ref": NotARef("polymorphic")})


def code_column(length: int = 64, nullable: bool = True):
    return mapped_column(String(length), nullable=nullable)
