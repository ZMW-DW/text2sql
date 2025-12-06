from __future__ import annotations

import os
import re
from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional, cast
from utils import DB_config, SQL_client, AgentState, Mermaid, SQLAnalyse, MilvusRetriever
from utils import (
    WRITE_QUERY_PROMPT,
    REWRITE_QUERY_PROMPT,
    CHECK_QUERY_PROMPT,
    SQL_RESULT_TO_MERMAID,
    REASONS_SQL
)
import termcolor
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from dotenv import load_dotenv
import asyncio
from datetime import datetime

load_dotenv()

class SQLAgent: 
    def __init__(
        self,
        db_config: DB_config,

        is_prebuild_agent: bool = True,
        max_turns: int = 3,
        debug: bool = False,
        db_schema: str | None = None,
        selected_example_nums: int = 3,

        # LLM_max_token: int = 20000,
        max_prompt_token: int = 10000,
        execution_truncate: int = 4096,

        is_accelerate: bool = True,
        is_sql_reasion: bool = True
    ):
        self.db = SQL_client(db_config)
        self.db_name = db_config.db_name
        self.debug = debug
        self.max_turns = max_turns
        self.max_prompt_token = max_prompt_token
        self.execution_truncate = execution_truncate
        self.is_accelerate = is_accelerate
        self.is_sql_reasion = is_sql_reasion
        self.selected_example_nums= selected_example_nums

        self.llm = init_chat_model(
            model=os.environ['LLM_MODEL_NAME'],
            model_provider=os.environ['LLM_MODEL_PROVIDER'],
            openai_api_base=os.environ['LLM_MODEL_BASE_URL'],
            openai_api_key=os.environ['LLM_MODEL_KEY'],
            temperature=0,
            max_retries=2,
        )

        self.retriever = MilvusRetriever(
            db_name="test",
            embedding_type='local',
            top_k=2
        )
        
        if is_prebuild_agent:
            self.agent = self.build_agent()
        else:
            self.agent = None
        
    def invoke_prompt(self, prompt: Any, output_structed: BaseModel | None = None) -> AnyMessage:
        import re
        pattern = '^<think>.*?</think>'

        LLM = self.llm.with_structured_output(output_structed) if output_structed else self.llm
        
        if self.debug:
            for message in prompt.messages:
                termcolor.cprint(message.pretty_repr(), "blue")

        result = LLM.invoke(prompt)

        if self.debug:
            print_buffer = re.sub(pattern, "", result.content).strip()
            termcolor.cprint(print_buffer, "green")

        return result if not output_structed else result.sql_query
    
    def parse_query(self, message: AnyMessage) -> str | None:
        result: str | None = None
        for match in re.finditer(r".*```\w*\n(.*?)\n```.*", message.content, re.DOTALL):  # type: ignore
            result = match.group(1).strip()  # type: ignore
        return result  # type: ignore
    
    def receive_input(self, state: AgentState) -> Command[Literal['write']]:
        return Command(
            update={
                "current_time": 0,
                "dialect": self.db.db_dialect,
                "db_schema": self.db.get_schema(example_num=1),
                "num_turns" : 3,
                "messages" : [SystemMessage(state['question'])]
            },
            goto="retrieve"
        )
    
    def retrieve_relate_tables(self, state: AgentState) -> Command[Literal['write']]:
        tebles = self.retriever.retrieve(state['question'])
        return Command(
            update={
                "selected_tables": tebles,
                "db_schema": self.db.get_schema(selected_tables=tebles, example_num=self.selected_example_nums),
                "messages": [SystemMessage("检索相关表")]
            },
            goto="write"
        )

    def write_sql_query(self, state: AgentState) -> Command[Literal['execute']]:
        prompt = WRITE_QUERY_PROMPT.invoke(
            {
                "dialect": state['dialect'],
                "input": state["question"],
                "db_schema": state['db_schema'],
            }
        )

        result = self.invoke_prompt(prompt)
        sql_query = self.parse_query(result)
        return Command(
            update={
                "sql_query": sql_query,  
                "messages": [AIMessage(sql_query)],
            },
            goto="execute"
        )

    def execute_sql_query(self, state: AgentState) -> Command[Literal['determine']]:
        execute_reasult = self.db.execut_sql(state["sql_query"])

        if self.debug:
            termcolor.cprint(execute_reasult, "yellow")

        return Command(
            update={
                "execute_reasult": execute_reasult,
                "messages" : [SystemMessage(execute_reasult)]
            },
            goto="determine"
        )
    
    def determine_node(self, state: AgentState) -> Command[Literal['rewrite', "finish"]]:
        prompt = CHECK_QUERY_PROMPT.invoke(
            {
                "dialect": state['dialect'],
                "input": state["question"],
                "sql_query": state["sql_query"],
                "execute_reasult": state["execute_reasult"],
                "db_schema": state['db_schema'],
            }
        )

        sql_query = state["sql_query"]
        result = self.invoke_prompt(prompt)

        if state["current_time"] >= self.max_turns or "THE QUERY IS CORRECT" in result.content:
            return Command(
                update={"messages" : [SystemMessage(f"{sql_query} is right")]},
                goto="finish"
            )
        
        return Command(
            update={
                "feedback" : result.content,
                "messages": [AIMessage(f"{sql_query} is not right")],
            },
            goto="rewrite"
        )
    
    def rewrite_sql_query(self, state: AgentState) -> Command[Literal['execute']]:
        prompt = REWRITE_QUERY_PROMPT.invoke({
            "dialect": state['dialect'],
            "input": state["question"],
            "sql_query": state["sql_query"],
            "execute_reasult": state["execute_reasult"],
            "feedback": state["feedback"],
            "db_schema": state['db_schema'],
        })

        result = self.invoke_prompt(prompt)
        rewritten_query = self.parse_query(result) 

        current_time = state['num_turns']
        new_time = current_time + 1 if current_time else 1

        return Command(
            update={
                "sql_query" : rewritten_query if rewritten_query else state['sql_query'],
                "current_time" : new_time,
                "messages": [AIMessage(rewritten_query)]
            },
            goto="execute"
        )
    
    def parse_mermaid(self, mermaid: str):
        import re
        pattern = r"```mermaid\s+([\s\S]*?)```"
        match = re.search(pattern, mermaid)
        if match:
            return match.group(1).strip()
        return None
    
    async def visial_sql_result(self, question: str, sql_query: str, sql_result: str):
        prompt = SQL_RESULT_TO_MERMAID.invoke(
            {
                "question": question,
                "sql_query" : sql_query, 
                "sql_result": sql_result
            }
        )
        output = {}
        result = self.llm.with_structured_output(Mermaid).invoke(prompt).model_dump()
        for key, valuse in result.items():
            if valuse:
                output[key] = self.parse_mermaid(valuse)
        return output

    async def get_SQL_reasons(self, sql_query: str):
        prompt = REASONS_SQL.invoke({"sql_query": sql_query})
        return self.llm.with_structured_output(SQLAnalyse).invoke(prompt).model_dump()
    
    def sync_visial_sql_result(self, question: str, sql_query: str, sql_result: str):
        prompt = SQL_RESULT_TO_MERMAID.invoke(
            {
                "question": question,
                "sql_query" : sql_query, 
                "sql_result": sql_result
            }
        )
        output = {}
        result = self.llm.with_structured_output(Mermaid).invoke(prompt).model_dump()
        for key, valuse in result.items():
            if valuse:
                output[key] = self.parse_mermaid(valuse)
        return output

    def sycn_get_SQL_reasons(self, sql_query: str):
        prompt = REASONS_SQL.invoke({"sql_query": sql_query})
        return self.llm.with_structured_output(SQLAnalyse).invoke(prompt).model_dump()
    
    async def parallel_process(self, question: str, sql_query: str, execute_reasult: str):
        visial_task = self.visial_sql_result(
            question, 
            sql_query, 
            execute_reasult
        )
        reasons_task = self.get_SQL_reasons(sql_query)

        visial_result, reasons_result = await asyncio.gather(visial_task, reasons_task)
        return visial_result, reasons_result
    
    def get_reasons_ultra(self, reasons_result: dict, tables: list) -> dict:
        reasons_result['database_name'] = self.db_name
        full_map = {
            "db_name": self.db_name,
            "table_name": tables[0]
        }
        sql_query = """
        SELECT 
            UPDATE_TIME
        FROM information_schema.tables
        WHERE TABLE_SCHEMA = '{db_name}'
        AND TABLE_NAME = '{table_name}';
        """.format_map(full_map)        
        pattern = r"datetime\.datetime\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)"
        m = re.search(pattern, self.db.execut_sql(sql_query))
        if m:
            year, month, day, hour, minute, second = map(int, m.groups())
            dt = datetime(year, month, day, hour, minute, second).strftime("%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reasons_result['latest_update_time'] = dt
        return reasons_result

    
    def end_graph(self, state: AgentState):
        if self.debug:
            termcolor.cprint("finish!", "yellow")
        
        output = {}
        if self.is_accelerate:
            visial_result, reasons_result = asyncio.run(
                self.parallel_process(
                    state['question'], 
                    state['sql_query'], 
                    state['execute_reasult']
                )
            )
            output['mermaid_output'] = visial_result
            output['SQL_reasons'] = reasons_result
        else:
            visial_result = self.sync_visial_sql_result(
                state['question'], 
                state['sql_query'], 
                state['execute_reasult']
            )
            output['mermaid_output'] = visial_result
            if self.is_sql_reasion:
                reasons_result = self.get_reasons_ultra(
                    self.sycn_get_SQL_reasons(state['sql_query']),
                    state['selected_tables']
                )
                output['SQL_reasons'] = reasons_result
            
        return Command(
            update=output 
        )
    
    def build_agent(self) -> CompiledStateGraph[AgentState]:
        builder = StateGraph(AgentState)
        builder.add_node("start", self.receive_input)
        builder.add_node("retrieve", self.retrieve_relate_tables)
        builder.add_node("write", self.write_sql_query)
        builder.add_node("execute", self.execute_sql_query)
        builder.add_node("determine", self.determine_node)
        builder.add_node("rewrite", self.rewrite_sql_query)
        builder.add_node("finish", self.end_graph)
        builder.add_edge(START, "start")
        builder.add_edge("finish", END)
        return builder.compile()
    
    def __call__(self, question: str):
        if not self.agent:
            self.agent = self.build_agent()

        for chunk in self.agent.stream(
            input={"question" : question},
            stream_mode="updates"
        ):
            try:
                for node, update in chunk.items():
                    if node != "finish":
                        data = update['messages'][-1].content
                    else:
                        data = update
                    yield {"node": node, "update": data}
            except Exception as e:
                return f"error: {e}"
    
    async def parallel_batch_rasults(self, result: dict):
        x = None  
        y = {}
        for key, value in result.items():
            if key == 'question':
                x = value.replace("我想知道", "").strip()  
            elif key == 'sql_query':
                y['sql_query'] = value  
            elif key == "SQL_reasons":
                y['SQL_reasons'] = value
        return x, y
            
    async def batch_inference(self, task_list: List[str]) -> List[str]:
        if not self.agent:
            self.agent = self.build_agent()

        if self.is_accelerate:
            inputs = [{"question" : task} for task in task_list]
            results = await self.agent.abatch(inputs=inputs)
        else:
            results = []
            for task in task_list:
                result = await self.agent.ainvoke({"question" : task})
                results.append(result)
        
        tasks = [self.parallel_batch_rasults(item) for item in results]
        processed_results = await asyncio.gather(*tasks)  
        output = {x: y for x, y in processed_results if x and y}
        return output


if __name__ == "__main__":
    import yaml
    import os
    current_path = os.path.abspath(os.path.dirname(__file__))
    config_path = os.path.join(current_path, "config.yaml")
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f.read())
        config = data['DB']
        db_config = DB_config(**config)

    agent = SQLAgent(db_config=db_config, is_accelerate=False, is_sql_reasion=False)

    # # respond = agent.llm.invoke("hellow")
    # # print(respond.content)

    for item in agent(question="各个的社区人口数量"):
        print(item)

    # import asyncio
    # import pandas as pd
    # from io import BytesIO

    # with open('./test.xlsx', 'rb') as f:
    #     df = pd.read_excel(BytesIO(f.read()))
    #     column_list = df.columns.tolist()
    #     preprocess = ["我想知道"+ item for item in column_list]
    
    # result = asyncio.run(agent.batch_inference(preprocess))
    # print(result)


    # sql_query = "SELECT COUNT(*) AS 住宅数量\nFROM DWS_CET_ZT_MSZTFWXXB\nWHERE FWSYYTMC = '住宅';"
    # sql_result = agent.db.execut_sql(sql_query)

    # result = asyncio.run(agent.visial_sql_result(
    #     question="住宅数量",
    #     sql_query=sql_query,
    #     sql_result=sql_result
    # ))

    # print(result)

        


    