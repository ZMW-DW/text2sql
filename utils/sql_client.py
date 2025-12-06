import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.engine import Engine
from pydantic import BaseModel
from typing_extensions import Optional, Literal, List, Any
from llama_index.core import SQLDatabase
import random
import datetime, decimal
from dotenv import load_dotenv
load_dotenv()

class DB_config(BaseModel):
    dialect: Literal["mysql", "postgresql", "sqlite", "oracle", "dm"]
    db_path: Optional[str] = None
    db_name: Optional[str] = None
    user_name: Optional[str] = None
    db_pwd: Optional[str] = None
    db_host: Optional[str] = None
    port: Optional[int] = None

    @property
    def connection_string(self):
        if self.dialect == "sqlite":
            return f"sqlite:///{self.db_path}"  # SQLite 使用 db_path 作为路径
        elif self.dialect == "mysql":
            return f"mysql+pymysql://{self.user_name}:{self.db_pwd}@{self.db_host}:{self.port}/{self.db_name}"
        elif self.dialect == "postgresql":
            return f"postgresql+psycopg2://{self.user_name}:{self.db_pwd}@{self.db_host}:{self.port}/{self.db_name}"
        elif self.dialect == "oracle":
            return f"oracle+oracledb://{self.user_name}:{self.db_pwd}@{self.db_host}:{self.port}/{self.db_name}"
        elif self.dialect == "dm":
            return f"dm+dmPython://{self.user_name}:{self.db_pwd}@{self.db_host}:{self.port}"
            # return f"dm+dmPython://{self.user_name}:{self.db_pwd}@{self.db_host}:{self.port}/{self.db_name}"
        else:
            raise ValueError(f"Unsupported dialect: {self.dialect}")
    
    @property
    def get_dialect(self):
        return self.dialect if self.dialect != "dm" else "达梦数据库"
        
def is_email(string):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        match = re.match(pattern, string)
        if match:
            return True
        else:
            return False

def examples_to_str(examples: list) -> list[str]:
    values = examples
    for i in range(len(values)):
        if isinstance(values[i], datetime.date):
            values = [values[i]]
            break
        elif isinstance(values[i], datetime.datetime):
            values = [values[i]]
            break
        elif isinstance(values[i], decimal.Decimal):
            values[i] = str(float(values[i]))
        elif is_email(str(values[i])):
            values = []
            break
        elif 'http://' in str(values[i]) or 'https://' in str(values[i]):
            values = []
            break
        elif values[i] is not None and not isinstance(values[i], str):
            pass
        elif values[i] is not None and '.com' in values[i]:
            pass

    return [str(v) for v in values if v is not None and len(str(v)) > 0]
        
class LocalDBInformation:
    def __init__(self, schema : Any = None):
        self.schema = schema
        self.tables = {}
        self.foreign_keys = []

    def add_table(self, table_name: str, fields: dict = {}, comment: str | None = None):
        self.tables[table_name] = {"fields": fields.copy(), 'comment' : comment}

    def add_field(self,table_name: str, field_name: str, field_type: str = "",
            primary_key: bool = False, nullable: bool = True, default: Any = None,
            autoincrement: bool = False, comment: str = "", examples: list = [], **kwargs):
        self.tables[table_name]['fields'][field_name] = {
            "type": field_type,
            "primary_key": primary_key,
            "nullable": nullable,
            "default": default if default is None else f'{default}',
            "autoincrement": autoincrement,
            "comment": comment,
            "examples": examples.copy(),
            **kwargs}
        
    def add_foreign_key(self, table_name: str, field_name: str, ref_schema: str, ref_table_name: str, ref_field_name: str):
        self.foreign_keys.append([table_name, field_name, ref_schema, ref_table_name, ref_field_name])

    def get_field_type(self, field_type, simple_mode=True)->str:
        if not simple_mode:
            return field_type
        else:
            return field_type.split("(")[0]

    def get_single_table_schema(self, table_name: str, selected_columns: List = None,
                             example_num=3, show_type_detail=False, shuffle=True) -> str:
        table_info = self.tables.get(table_name, {})
        table_comment = table_info.get('comment', '')

        table_output = []
        if table_comment is not None and table_comment != 'None' and len(table_comment) > 0:
            if self.schema is not None and len(self.schema) > 0:
                table_output.append(f"# Table: {self.schema}.{table_name}, {table_comment}")
            else:
                table_output.append(f"# Table: {table_name}, {table_comment}")
        else:
            if self.schema is not None and len(self.schema) > 0:
                table_output.append(f"# Table: {self.schema}.{table_name}")
            else:
                table_output.append(f"# Table: {table_name}")

        fields_output = []
        for field_name, field_info in table_info['fields'].items():
            if selected_columns is not None and field_name.lower() not in selected_columns:
                continue

            raw_type = self.get_field_type(field_info['type'], not show_type_detail)
            field_line = f"({field_name}:{raw_type.upper()}"
            if field_info['comment'] != '':
                field_line += f", {field_info['comment'].strip()}"
            else:
                pass
            
            is_primary_key = field_info.get('primary_key', False)
            if is_primary_key:
                field_line += f", Primary Key"

            if len(field_info.get('examples', [])) > 0 and example_num > 0:
                examples = field_info['examples']
                examples = [s for s in examples if s is not None]
                examples = examples_to_str(examples)
                if len(examples) > example_num:
                    examples = examples[:example_num]

                if raw_type in ['DATE', 'TIME', 'DATETIME', 'TIMESTAMP']:
                    examples = [examples[0]]
                elif len(examples) > 0 and max([len(s) for s in examples]) > 20:
                    if max([len(s) for s in examples]) > 50:
                        examples = []
                    else:
                        examples = [examples[0]]
                else:
                    pass
                if len(examples) > 0:
                    example_str = ', '.join([str(example) for example in examples])
                    field_line += f", Examples: [{example_str}]"
                else:
                    pass
            else:
                field_line += ""
            field_line += ")"

            fields_output.append(field_line)

        if shuffle:
            random.shuffle(fields_output)

        table_output.append('[')
        table_output.append("\n".join(fields_output))
        table_output.append(']')
        return '\n'.join(table_output)
    
    def get_DB_information(self, selected_tables: List = None, selected_columns: List = None,
                   example_num=3, show_type_detail=False, shuffle=True) -> str:
        output = []
        if selected_tables is not None:
            selected_tables = [s.lower() for s in selected_tables]
        if selected_columns is not None:
            selected_columns = [s.lower() for s in selected_columns]
            selected_tables = [s.split('.')[0].lower() for s in selected_columns]
        
        for table_name, table_info in self.tables.items():
            if selected_tables is None or table_name.lower() in selected_tables:
                column_names = list(table_info['fields'].keys())
                if selected_columns is not None:
                    cur_selected_columns = [c for c in column_names if f"{table_name}.{c}".lower() in selected_columns]
                else:
                    cur_selected_columns = selected_columns
                output.append(self.get_single_table_schema(table_name, cur_selected_columns, example_num, show_type_detail, shuffle))

        if shuffle:
            random.shuffle(output)

        output.insert(0, f"【Schema】")

        if self.foreign_keys:
            output.append("【Foreign keys】")
            for fk in self.foreign_keys:
                ref_schema = fk[2]
                table1, _, _, table2, _ = fk
                if selected_tables is None or \
                        (table1.lower() in selected_tables and table2.lower() in selected_tables):
                    
                    if ref_schema == self.schema:
                        output.append(f"{fk[0]}.{fk[1]}={fk[3]}.{fk[4]}")

        return '\n'.join(output)
        
class Database(SQLDatabase):
    def __init__(self, engine: Engine, schema: Optional[str] = None, metadata: Optional[MetaData] = None,
                 ignore_tables: Optional[List[str]] = None, include_tables: Optional[List[str]] = None,
                 sample_rows_in_table_info: int = 3, indexes_in_table_info: bool = False,
                 custom_table_info: Optional[dict] = None, view_support: bool = False, max_string_length: int = 300,
                 localDBInformation: Optional[LocalDBInformation] = None, db_name: Optional[str] = ''):
        super().__init__(engine, schema, metadata, ignore_tables, include_tables, sample_rows_in_table_info,
                         indexes_in_table_info, custom_table_info, view_support, max_string_length)
        
        self._db_name = db_name
        self._usable_tables = [table_name for table_name in self._usable_tables if self._inspector.has_table(table_name, schema)]
        self._dialect = engine.dialect.name
        if localDBInformation is not None:
            self._local_db_information = localDBInformation
        else:
            self._local_db_information = LocalDBInformation(schema=schema)
            self._setup()

    def get_table_comment(self, table_name: str):
        try:
            return self._inspector.get_table_comment(table_name, self._schema)['text']
        except:    # sqlite不支持添加注释
            return ''

    def fectch_distinct_values(self, table_name: str, column_name: str, max_num: int = 3):
        table = Table(table_name, self.metadata_obj, autoload_with=self._engine)
        query = select(table.c[column_name]).distinct().limit(max_num)
        values = []
        with self._engine.connect() as connection:
            result = connection.execute(query)
            distinct_values = result.fetchall()
            for value in distinct_values:
                if value[0] is not None and value[0] != '':
                    values.append(value[0])
        return values

    def _setup(self):
        for table_name in self._usable_tables:
            table_comment = self.get_table_comment(table_name)
            table_comment = '' if table_comment is None else table_comment.strip()

            self._local_db_information.add_table(table_name, fields={}, comment=table_comment)
            
            # pks = self.get_pk_constraint(table_name)
            pks = self._inspector.get_pk_constraint(table_name, self._schema)['constrained_columns']

            # fks = self.get_foreign_keys(table_name)
            fks = self._inspector.get_foreign_keys(table_name, self._schema)

            for fk in fks:
                referred_schema = fk['referred_schema']
                for c, r in zip(fk['constrained_columns'], fk['referred_columns']):
                    self._local_db_information.add_foreign_key(table_name, c, referred_schema, fk['referred_table'], r)

            fields = self._inspector.get_columns(table_name, schema=self._schema)
            for field in fields:
                field_type = f"{field['type']!s}"
                field_name = field['name']
                if field_name in pks:
                    primary_key = True
                else:
                    primary_key = False

                field_comment = field.get("comment", None)
                field_comment = "" if field_comment is None else field_comment.strip()
                autoincrement = field.get('autoincrement', False)
                default = field.get('default', None)
                if default is not None:
                    default = f'{default}'

                try:
                    examples = self.fectch_distinct_values(table_name, field_name, 5)
                except:
                    examples = []

                examples = examples_to_str(examples)

                self._local_db_information.add_field(table_name, field_name, field_type=field_type, primary_key=primary_key,
                    nullable=field['nullable'], default=default, autoincrement=autoincrement,
                    comment=field_comment, examples=examples)
    
    @property
    def db_name(self) -> str:
        """Return db_name"""
        return self._db_name


class SQL_client:
    def __init__(self, db_config: DB_config):
        # self.db_config = db_config
        self.db_dialect = db_config.get_dialect
        connect_args = {'connection_timeout': 3600} if self.db_dialect == "dm" else {}

        self.engin = create_engine(
            db_config.connection_string,
            connect_args=connect_args
        )
        self.DB = Database(self.engin)

    def execut_sql(self, sql_query: str):
        with self.engin.connect() as con:
            try:
                cursor = con.execute(text(sql_query))
                records = cursor.fetchall()
                records = [tuple(row) for row in records]
                return str(records)
            except Exception as e:
                records = str(e)
            return records
        
    def get_teble_information(self) -> dict:
        return self.DB._local_db_information.tables
    
    def get_schema(self, selected_tables: List = None, selected_columns: List = None,
                   example_num=3, show_type_detail=False, shuffle=True)->str:
        
        return self.DB._local_db_information.get_DB_information(
            selected_tables,
            selected_columns,
            example_num,
            show_type_detail,
            shuffle
        )
    
def worker(task: dict[str, DB_config], save_dir: str, llm, prompt) -> dict[str, str]:
    database, db_config = next(iter(task.items()))
    sql = SQL_client(db_config=db_config)
    table = sql.get_teble_information()

    def parse_respond(data: str):
        import re
        pattern = r"```output\s*([\s\S]*?)```"
        match = re.search(pattern, data)
        if match:
            return match.group(1).strip()
        return None

    tasks = []
    indeies = []
    output = {}
    for key, valuse in table.items():
        indeies.append(key)
        task = prompt.invoke({"query": valuse})
        tasks.append(task)
    results = llm.batch(tasks)
    for index, result in zip(indeies, results):
        output[index] = parse_respond(result.content)

    save_path = os.path.join(save_dir, f"{database}.json")
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return {database: save_path}
    
        
def make_json(tasks: List[dict[str, DB_config]]) -> dict[str, str]:
    llm = init_chat_model(
        model=os.environ['LLM_MODEL_NAME'],
        model_provider=os.environ['LLM_MODEL_PROVIDER'],
        openai_api_base=os.environ['LLM_MODEL_BASE_URL'],
        openai_api_key=os.environ['LLM_MODEL_KEY'],
        temperature=0,
        max_retries=2,
    )

    PROMPT = ChatPromptTemplate(
        [
            ("system", """
            You are an expert summarization assistant. 
            Your task is to generate a concise, accurate, and lossless summary of the given content.

            ### Requirements:
            1. **Objectivity**
            - Do not invent, guess, or hallucinate facts.
            - Only summarize information explicitly present in the input.

            2. **Information Coverage**
            - Capture key facts, important actions, decisions, tasks, and user intents.
            - Preserve all critical numbers, names, steps, requirements, constraints, and context.

            3. **Writing Style**
            - Clear, short, and professional.
            - Avoid subjective descriptions.
            - Use neutral language.

            4. **Structure**
            Output must be formatted into the following sections:
            - **Summary**: A short paragraph with the main idea.
            - **Key Points**: 3–8 bullet points capturing the most important information.
            - **Action Items (if any)**: Tasks or follow-ups explicitly mentioned in the input.
            - **Risks / Concerns (if any)**: Only list what appears in the input.

            5. **Do NOT**
            - Add interpretations, assumptions, or external knowledge.
            - Add suggestions unless explicitly present in the input.
             
            ### output format:
            ```output
             your generation
            ```

            Your output must be fully factual and strictly derived from the input content, and you must output chinese.

            /no_think
            """),
            ("user", "{query}")
        ]
    )

    max_workers = len(tasks)
    output = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(worker, item, os.environ['TEMP_DIR'], llm, PROMPT)
            for item in tasks
        ]

        for fut in as_completed(futures):
            output.append(fut.result())
    return output
    

if __name__ == "__main__":
    import yaml
    import json
    with open('/home/david/data1/work/query_data/config.yaml', 'r') as f:
        data = yaml.safe_load(f.read())
        config = data['DB']
        db_config = DB_config(**config)

    tasks = [{"zyzx1": db_config}]

    result = make_json(tasks=tasks)

    print(result)


    




