from pydantic import BaseModel, Field
from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage
from typing_extensions import TypedDict, Literal, List

class AgentState(MessagesState):
    question: str

    selected_tables: List[str]
    sql_query: str
    execute_reasult: str
    feedback: str
    current_time: int
    dialect: str
    selected_tables: list
    db_schema: str
    num_turns: int = 3
    mermaid_output: dict
    SQL_reasons: dict



class SQL(BaseModel):
    sql_query: str = Field(..., description="sql语句")

class Mermaid(BaseModel):
    flowchart: str | None  = Field(None, description="Flowchart的mermaid结果")
    pip: str | None  = Field(None, description="Pie Chart的mermaid结果")
    gantt: str | None  = Field(None, description="Gantt Chart的mermaid结果")

class SQLAnalyse(BaseModel):
    sql_table: str = Field(..., description="SQL语句中相关表")
    sql_field: list = Field(..., description="SQL语句中相关的字段", examples=[
    """
    【输入】
    SELECT 
        TABLE_SCHEMA,
        TABLE_NAME,
        UPDATE_TIME
    FROM information_schema.tables
    WHERE TABLE_SCHEMA = '你的数据库名'
    AND TABLE_NAME = '你的表名';
                                                                     
    【输出】你需要的输出内容
    ["TABLE_SCHEMA", "TABLE_NAME", "UPDATE_TIME"]
    """,
    """"
    【输入】
    SELECT SQ AS 社区, COUNT(*) AS 人口数量
        FROM DWS_CETC_PP_PERSON_ALL
        GROUP BY SQ;
    【输出】
    ['SQ']
    """])
    
class TLAgentState(TypedDict):
    question: str

    pre_condition: str | None
    extra_body: str | None

    sql_query: str

class Pre_output(BaseModel):
    pre_condition : Literal[
        "WHERE EXIST_WG='是'", 
        "WHERE SFJL='是'", 
        "WHERE SFJL='是'", 
        ""
        ]