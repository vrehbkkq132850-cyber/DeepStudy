from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# 引入你的 RAG 核心引擎
from backend.data.vector_store import vector_store_manager

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

# --- 定义请求的数据模型 ---
class MemoCreate(BaseModel):
    content: str
    source: Optional[str] = "user_note"
    metadata: Optional[Dict[str, Any]] = {}

class SearchQuery(BaseModel):
    query: str
    top_k: int = 3

# --- 1. 快速记笔记 (文本存入) ---
@router.post("/memo")
async def add_memo(memo: MemoCreate):
    """
    接收一段纯文本笔记，存入向量知识库。
    """
    if not memo.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    try:
        # 组合 metadata
        meta = memo.metadata or {}
        meta["source"] = memo.source
        meta["type"] = "memo"

        # 调用向量库
        await vector_store_manager.add_document(text=memo.content, metadata=meta)
        
        logger.info(f"已存入笔记，长度: {len(memo.content)}")
        return {"status": "success", "message": "笔记已存入大脑"}
    except Exception as e:
        logger.error(f"存入笔记失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. 知识检索 (RAG 测试) ---
@router.post("/search")
async def search_knowledge(search_req: SearchQuery):
    """
    输入问题，返回最相关的知识片段 (RAG)。
    """
    try:
        logger.info(f"正在搜索: {search_req.query}")
        results = await vector_store_manager.search_context(
            query=search_req.query, 
            top_k=search_req.top_k
        )
        return {"count": len(results), "results": results}
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. 文件上传 (支持 .md, .txt) ---
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件，自动读取内容并存入向量库。
    目前完美支持: .md, .txt
    (PDF 支持预留位)
    """
    filename = file.filename
    logger.info(f"收到文件上传: {filename}")

    try:
        # 读取文件内容 (二进制)
        content_bytes = await file.read()
        
        text_content = ""
        
        # 简单判断文件类型
        if filename.endswith(".md") or filename.endswith(".txt"):
            # 尝试解码为字符串
            text_content = content_bytes.decode("utf-8")
        elif filename.endswith(".pdf"):
            # TODO: 这里需要安装 pypdf 才能解析 PDF
            # 如果你想支持PDF，告诉我，我教你加几行代码
            return {"status": "warning", "message": "PDF解析功能暂未开启，请上传txt或md"}
        else:
            return {"status": "error", "message": "暂不支持该文件格式"}

        if text_content:
            # 存入向量库
            await vector_store_manager.add_document(
                text=text_content, 
                metadata={"source": filename, "type": "file"}
            )
            return {"status": "success", "message": f"文件 {filename} 已读入知识库"}
            
    except Exception as e:
        logger.error(f"文件处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")