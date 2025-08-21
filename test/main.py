from openai import OpenAI
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import logging
from config import model_config as CFG


app = FastAPI()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

class QueryInput(BaseModel):
    query: str
    session_id: Optional[str] = None

class Chat:
    def __init__(
        self, 
        model=CFG.model_name,
        base_url=CFG.base_url,
        api_key=CFG.api_key
    ):
        self.model = model
        self.openai_client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        self.messages = lambda x : [
            {
                "role": "system",
                "content": "你是一个AI助手。根据用户问题的主题，将其归类为以下之一：'外交'、'安全'、'经贸财经'、'科技'。只输出对应的类别，不要输出其他内容。"
            },
            {
                "role": "user",
                "content": x
            }
        ]
            
    async def chat(self, query:str):
        response = self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=self.messages(query)
                        )
        return response
    
user_client = None
        
@app.on_event("startup")
async def startup_event():
    """启动时初始化客户端"""
    global user_client
    try:
        user_client = Chat()
        logger.info("服务启动完成")
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        raise
        
@app.post("/query/category", summary="提交问题获取结构化答案")
async def get_data(query: QueryInput):
    respond = await user_client.chat(query.query)
    return respond.choices[0].message.content
    
if __name__ == "__main__":
#     asyncio.run(main())
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
