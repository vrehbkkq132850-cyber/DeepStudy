"""
数据库初始化脚本
用于手动初始化数据库表结构
"""
import asyncio
from backend.data.sqlite_db import init_db


async def main():
    """初始化数据库"""
    print("正在初始化数据库...")
    await init_db()
    print("数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
