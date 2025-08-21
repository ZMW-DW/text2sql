from openai import OpenAI
from fastmcp import Client
from typing import List, Dict, Optional, Union
import asyncio
import json
import re
from fastapi import FastAPI, HTTPException
import logging
from pydantic import BaseModel, Field, ValidationError



app = FastAPI()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)
parent_logger = logging.getLogger("xiyan_mcp_server")


class QueryInput(BaseModel):
    """输入查询模型"""
    query: str
    session_id: Optional[str] = None  # 可选会话ID，用于多轮对话
    
class UserClient:
    def __init__(self, script="server.py", model_name="ZhipuAI/GLM-4.5"):
        self.model_name = model_name
        self.mcp_client = Client(script)
        self.openai_client = OpenAI(
            base_url="https://api-inference.modelscope.cn/v1",
            api_key="ms-b052e4ed-4183-4027-8574-9b8f6fc9ad56"
        )
        logger.info("UserClient initialized successfully")

    async def query_and_format(self, query: str):
        async with self.mcp_client:
            raw_result = await self.mcp_client.call_tool("get_data", {"query": query})
        raw_text = raw_result.content[0].text
        
        messages = [
            {
                "role": "system",
                "content": (
                    "你是结构化数据格式化助手，任务是将输入的 Markdown 表格解析为标准 JSON 数组格式。"
                )
            },
            {
                "role": "user",
                "content": raw_text
            }
        ]
        
        json_data = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )
        
        # return raw_text
        return json_data.choices[0].message.content
    
user_client = None

@app.on_event("startup")
async def startup_event():
    """启动时初始化客户端"""
    global user_client
    try:
        user_client = UserClient("server.py")
        logger.info("服务启动完成")
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        raise

@app.post("/query/text2sql", summary="提交问题获取结构化答案")
async def get_data(query: QueryInput):
    if not user_client:
        raise HTTPException(status_code=503, detail="服务未初始化完成")

    raw_data = await user_client.query_and_format(query.query)
    
    try:
        raw_structured = raw_data.replace("```json", "").replace("```", "").replace("\n", "").strip()
        return raw_structured 
    except Exception as e:
        return raw_data


if __name__ == "__main__":
    # asyncio.run(main())
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
