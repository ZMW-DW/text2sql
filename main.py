from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
import yaml
from utils import DB_config, make_json
from sql_agent import SQLAgent
from pydantic import BaseModel, Field
import json
from io import BytesIO
import pandas as pd
import os
import redis
from dotenv import load_dotenv
base_path = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    config_file = os.path.join(base_path, 'config.yaml')
    with open(config_file, "r") as f:
        data = yaml.safe_load(f.read())
        db_config = data['DB']

    db_config = DB_config(
        **db_config
    )
    app.state.agent_1 = SQLAgent(
        db_config=db_config,
        is_accelerate=False,
        is_sql_reasion=False
    )
    app.state.agent_2 = SQLAgent(
        db_config=db_config,
        is_accelerate=False,
        is_sql_reasion=True
    )

    # sql = SQL_client(db_config=db_config)
    # table = 

    app.state.r = redis.Redis(
        host=os.environ['REDIS_URL'],
        port=os.environ['REDIS_PORT'],
        db=os.environ['REDIS_DB'],
        password=os.environ['REDIS_PASSWORD']
    )
    yield
    del app.state.agent_1
    del app.state.agent_2
    del db_config
    app.state.r.close()

app = FastAPI(lifespan=lifespan)

class InputParameters(BaseModel):
    user_id: str = Field(..., description="用户id")
    session_id: str = Field(..., description="会话id")
    task_id: str = Field(..., description="任务id")
    question: str = Field(..., description="用户的问题", examples=["How many different series and contents are listed in the TV Channel table?"])

def verification(user_id: str, session_id: str, task_id: str):
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing user_id")
    
    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(status_code=402, detail="Invalid or missing session_id")

    if not isinstance(task_id, str) or not task_id:
        raise HTTPException(status_code=403, detail="Invalid or missing task_id")

@app.post("/stream_get_sql")
async def get_sql(query: InputParameters):
    agent = app.state.agent_1
    r = app.state.r
    data = {
        "user_id" : query.user_id,
        "session_id" : query.session_id,
        "task_id" : query.task_id
    }
    verification(**data)
    key = "user_id:{user_id}:session_id:{session_id}:task_id:{task_id}".format_map(data)
    async def general(question: str):
        try:
            for item in agent(question):
                # print(item)
                node = item.get('node')
                if node in ['start', 'execute', 'determine', 'retrieve']:
                    if node == "start":
                        title = "用户输入"
                    elif node == 'execute':
                        title = "SQL执行结果"
                    elif node == 'determine':
                        title = 'SQL查询语句判断'
                    elif node == "retrieve":
                        title = "检索相关内容"
                    type_class = "text"
                elif node in ['write', 'rewrite']:
                    if node == 'write':
                        title = 'SQL语句书写'
                    elif node == 'rewrite':
                        title = 'SQL语句重写'
                    type_class = "sql" 
                elif node == "finish":
                    title = '结果可视化'
                    type_class = "images"
                    # r.set(key, json.dumps(item['update']))

                payload = {"title" : title, "type" : type_class, 'content': item['update'] if item.get('update') else "None"}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal Server Error")

    return StreamingResponse(general(query.question), media_type="text/event-stream")

class InputParameters(BaseModel):
    title: str
    head: list

@app.post("/excel_task")
async def process_execel(query : InputParameters):
    agent = app.state.agent_2
    task_list = ["我想知道"+ item for item in query.head]
    print(task_list)
    output = await agent.batch_inference(task_list=task_list)
    # print(output)
    return JSONResponse(
        output
    )

@app.get("/get_table")
async def get_table(
    user_id : str = Query(..., description="用户ID"),
    session_id : str = Query(..., description="会话ID"),
    task_id : str = Query(..., description="任务ID")
):
    verification(user_id, session_id, task_id)
    r = app.state.r
    key = f"user_id:{user_id}:session_id:{session_id}:task_id:{task_id}"
    data = r.get(key).decode("utf-8")

    return JSONResponse(
        json.loads(data)
    )

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=45689)
    uvicorn.run(app, host=str(os.environ['SERVER_HOST']), port=int(os.environ['SERVER_PORT']))