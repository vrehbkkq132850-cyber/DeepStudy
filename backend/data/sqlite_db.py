"""
SQLite 数据库操作
管理用户数据和对话记录
"""
import aiosqlite
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, List
from backend.config import settings


async def get_db():
    """
    获取数据库连接
    
    Returns:
        数据库连接对象
    """
    # 确保数据目录存在
    db_path = settings.SQLITE_DB_PATH
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db


@asynccontextmanager
async def get_db_connection():
    """
    数据库连接上下文管理器
    自动管理连接的打开和关闭
    
    Usage:
        async with get_db_connection() as db:
            # 使用 db 进行数据库操作
            user = await get_user_by_username(db, "username")
    """
    db = await get_db()
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """初始化数据库表结构"""
    db = await get_db()
    
    # 创建用户表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # 创建对话表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            parent_id TEXT,
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    await db.commit()
    await db.close()


async def create_user(
    db: aiosqlite.Connection,
    username: str,
    email: str,
    hashed_password: str
) -> int:
    """
    创建用户
    
    Args:
        db: 数据库连接
        username: 用户名
        email: 邮箱
        hashed_password: 密码哈希
        
    Returns:
        用户 ID
    """
    created_at = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "INSERT INTO users (username, email, hashed_password, created_at) VALUES (?, ?, ?, ?)",
        (username, email, hashed_password, created_at)
    )
    await db.commit()
    return cursor.lastrowid


async def get_user_by_username(
    db: aiosqlite.Connection,
    username: str
) -> Optional[Dict]:
    """
    根据用户名获取用户
    
    Args:
        db: 数据库连接
        username: 用户名
        
    Returns:
        用户信息字典，如果不存在则返回 None
    """
    cursor = await db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None


async def get_user_by_email(
    db: aiosqlite.Connection,
    email: str
) -> Optional[Dict]:
    """
    根据邮箱获取用户
    
    Args:
        db: 数据库连接
        email: 邮箱
        
    Returns:
        用户信息字典，如果不存在则返回 None
    """
    cursor = await db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None


async def save_conversation(
    db: aiosqlite.Connection,
    user_id: str,
    conversation_id: str,
    parent_id: Optional[str],
    query: str,
    answer: str
):
    """
    保存对话记录
    
    Args:
        db: 数据库连接
        user_id: 用户 ID
        conversation_id: 对话 ID
        parent_id: 父对话 ID
        query: 用户查询
        answer: AI 回答
    """
    created_at = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO conversations (id, user_id, parent_id, query, answer, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (conversation_id, user_id, parent_id, query, answer, created_at)
    )
    await db.commit()


async def get_conversation_tree(
    db: aiosqlite.Connection,
    conversation_id: str,
    user_id: str
) -> Optional[Dict]:
    """
    获取对话树
    
    Args:
        db: 数据库连接
        conversation_id: 对话 ID
        user_id: 用户 ID
        
    Returns:
        对话树节点字典，如果不存在则返回 None
    """
    # 获取当前对话
    cursor = await db.execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    
    conversation = dict(row)
    
    # 递归获取子对话
    children_cursor = await db.execute(
        "SELECT * FROM conversations WHERE parent_id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    children_rows = await children_cursor.fetchall()
    children = [dict(row) for row in children_rows]
    
    # 递归构建子树
    for child in children:
        child_tree = await get_conversation_tree(db, child["id"], user_id)
        if child_tree:
            child["children"] = child_tree.get("children", [])
        else:
            child["children"] = []
    
    conversation["children"] = children
    return conversation
