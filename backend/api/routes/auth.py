"""
认证相关路由
"""
from fastapi import APIRouter, HTTPException, status, Depends
from passlib.context import CryptContext
from backend.api.schemas.request import UserCreate, UserLogin
from backend.api.schemas.response import AuthResponse, ErrorResponse
from backend.api.middleware.auth import create_access_token
from backend.data.sqlite_db import (
    get_db_connection,
    create_user,
    get_user_by_username,
    get_user_by_email
)


router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    """
    用户注册
    
    Args:
        user_data: 用户注册信息
        
    Returns:
        认证响应（包含 token）
    """
    async with get_db_connection() as db:
        # 检查用户名是否已存在
        existing_user = await get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        existing_email = await get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        # 创建用户
        hashed_password = get_password_hash(user_data.password)
        user_id = await create_user(
            db,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        # 生成 token
        access_token = create_access_token(data={"sub": str(user_id)})
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user_id),
            username=user_data.username
        )


@router.post("/login", response_model=AuthResponse)
async def login(user_data: UserLogin):
    """
    用户登录
    
    Args:
        user_data: 用户登录信息
        
    Returns:
        认证响应（包含 token）
    """
    async with get_db_connection() as db:
        # 获取用户
        user = await get_user_by_username(db, user_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 验证密码
        if not verify_password(user_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 生成 token
        access_token = create_access_token(data={"sub": str(user["id"])})
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user["id"]),
            username=user["username"]
        )
