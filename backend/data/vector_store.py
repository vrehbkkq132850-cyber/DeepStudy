import os
from typing import List, Dict

# --- 1. LlamaIndex 核心组件 ---
from llama_index.core import (
    VectorStoreIndex, 
    Document, 
    StorageContext, 
    load_index_from_storage, 
    Settings
)

# --- 2. 关键：复刻你截图里的 ModelScope 配置 ---
# 我们引用 LlamaIndex 的 OpenAI 类，但通过修改参数让它去连魔搭
from llama_index.llms.openai import OpenAI

# 引用 HuggingFace 嵌入模型（本地运行，免费且快）
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 导入你的配置 (确保 settings 里有 API KEY)
from backend.config import settings 

class VectorStoreManager:
    """
    DeepFocus 向量知识库管理器
    核心逻辑：
    1. LLM: 使用 ModelScope (Qwen2.5) -> 对应截图逻辑
    2. Embedding: 使用本地 HuggingFace -> 负责把文字变向量
    3. Index: 负责存取和搜索
    """
    
    def __init__(self):
        # 数据的本地存储路径
        self.persist_dir = "./local_storage"
        
        # =====================================================
        # 👇 这里就是你截图里的逻辑复刻 👇
        # =====================================================
        # 虽然类名叫 OpenAI，但我们把 api_base 改成了魔搭的地址
        # 这就相当于：self.client = OpenAI(base_url="https://api-inference.modelscope.cn/v1/...")
        model_scope_llm = OpenAI(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",  # 截图同款模型
            api_key="ms-9b769e50-465c-4108-b47e-dc40e7bf22fd",      # 填你的 Token
            api_base="https://api-inference.modelscope.cn/v1", # 截图同款地址
            temperature=0.1,
            max_tokens=2048
        )
        
        # 将其设置为全局默认 LLM
        Settings.llm = model_scope_llm
        
        # =====================================================
        # 配置嵌入模型 (用来计算相似度)
        # =====================================================
        # 使用本地轻量级模型，不需要联网调 API
        # 配置 眼睛 (Embedding) -> 使用 BGE 中文模型 (专精中文语义)
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5"
        )
        
        # --- 初始化索引 (加载记忆或新建) ---
        if not os.path.exists(self.persist_dir):
            print("📭 [VectorStore] 本地为空，正在初始化新知识库...")
            self.index = VectorStoreIndex.from_documents([])
            self.index.storage_context.persist(persist_dir=self.persist_dir)
        else:
            print("📂 [VectorStore] 发现本地记忆，正在加载...")
            storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
            self.index = load_index_from_storage(storage_context)

    async def add_document(self, text: str, metadata: Dict = None):
        """
        对应功能点：【实现文本片段提取和标记】
        LlamaIndex 会自动把 text 切分成片段 (Chunk)，并计算向量存入。
        """
        if not text: return

        print(f"📥 [存入] 处理中: {text[:20]}...")
        
        # 封装为文档对象
        doc = Document(text=text, metadata=metadata or {})
        
        # 插入索引
        self.index.insert(doc)
        
        # 💾 只有执行这一步，重启后数据才不会丢
        self.index.storage_context.persist(persist_dir=self.persist_dir)
        print("✅ [存入] 成功并已保存到硬盘。")

    async def search_context(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        对应功能点：【完善划词追问上下文获取】
        用户问 -> 找相关片段 -> 返回
        """
        # 创建检索器 (Retriever)
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        
        # 执行检索 (同步操作)
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.text,          # 原文
                "score": node.score,        # 相似度 (1.0最高)
                "source": node.metadata.get("source", "unknown")
            })
            
        return results

# 全局单例供外部调用
vector_store_manager = VectorStoreManager()

# --- 👇 把文件最下面的测试代码改成这样 👇 ---
if __name__ == "__main__":
    import asyncio
    
    async def test():
        v = VectorStoreManager()
        
        print("\n--- 1. 正在给 AI 灌输两段不相关的记忆 ---")
        
        # 记忆 A：关于 AI 的
        text_ai = "Qwen2.5-Coder 是阿里推出的代码生成模型，擅长写 Python 和 C++。"
        await v.add_document(text_ai, metadata={"source": "AI News"})
        
        # 记忆 B：关于做菜的 (干扰项)
        text_food = "宫保鸡丁是一道著名的川菜，主要通过爆炒鸡丁和花生米制成，口味糊辣荔枝味。"
        await v.add_document(text_food, metadata={"source": "食谱"})
        
        print("✅ 记忆灌输完毕！")
        
        # --- 2. 见证奇迹的时刻 ---
        
        # 提问 1：问吃的
        query1 = "我想学做菜，有什么推荐？" 
        # 注意：这句话里完全没有“宫保鸡丁”这四个字！
        
        print(f"\n❓ 用户问: {query1}")
        results = await v.search_context(query1, top_k=1)
        print(f"🤖 AI 回答的参考资料: {results[0]['text']}")
        
        # 提问 2：问代码
        query2 = "哪个模型写代码比较好？"
        
        print(f"\n❓ 用户问: {query2}")
        results = await v.search_context(query2, top_k=1)
        print(f"🤖 AI 回答的参考资料: {results[0]['text']}")

    asyncio.run(test())