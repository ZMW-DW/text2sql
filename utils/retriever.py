import os
from langchain_milvus import Milvus
from abc import ABC, abstractmethod
from typing_extensions import Literal, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import JSONLoader
from langchain_huggingface import HuggingFaceEmbeddings
from .sql_client import DB_config, make_json
import json
import yaml
from dotenv import load_dotenv
load_dotenv()

class Retriever(ABC):
    def __init__(self, category: Literal['milvus'], embedding_type: Literal['local', 'web(open_ai)'],
                 local_model: Optional[str] = None, model_name: Optional[str] = None, 
                 base_url: Optional[str] = None, api_key: Optional[str] = None, 
                 data_dir: Optional[str] = None):
        self.data_dir = data_dir if data_dir else os.environ['STORE_DIR']
        self.store_dir = os.path.join(self.data_dir, category)
        os.makedirs(self.store_dir, exist_ok=True)

        self.embedding_type = embedding_type

        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key

        self.local_model = local_model
    
    @property
    def embedding_model(self):
        if self.embedding_type == "web(open_ai)":
            return OpenAIEmbeddings(
                model=self.model_name if self.model_name else os.environ['EMBEDDING_MODEL'],
                base_url=self.base_url if self.base_url else os.environ['EMBEDDING_MODEL_BASE_URL'],
                api_key=self.api_key if self.api_key else os.environ['EMBEDDING_MODEL_API_KEY']
            )
        else:
            return HuggingFaceEmbeddings(
                model_name=self.local_model if self.local_model else os.environ['EMBEDDING_MODEL_LOCAL']
            )

    @abstractmethod
    def upload(self, file_path: str):
        pass
    @abstractmethod
    def retrieve(self, query: str):
        pass

class MilvusRetriever(Retriever):
    def __init__(self, db_name: str, embedding_type: Literal['local', 'web(open_ai)'], 
                 top_k: int=2, kwargs: dict = None):
        super().__init__(
            category='milvus', 
            embedding_type=embedding_type, 
            **(kwargs or {})
        )
        self.uri_path = os.path.join(self.store_dir, db_name + ".db")

        self.vector_store = Milvus(
            embedding_function=self.embedding_model,
            connection_args={"uri": self.uri_path},
            index_params={"index_type": "FLAT", "metric_type": "L2"}
        )

        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": top_k})

    def upload(self, json_path: str):
        loader = JSONLoader(
            file_path=json_path,
            jq_schema="to_entries[]",
            text_content=False,
        )
        docs = loader.load()
        self.vector_store.add_documents(documents=docs)
        print("complete upload to vectore")

    def retrieve(self, query: str):
        results =  self.retriever.invoke(query)
        return list(map(lambda x: json.loads(x.page_content)['key'], results))
    
def make_vectory_store(mbedding_type: Literal['local', 'web(open_ai)'] = 'local'):
    with open('/home/david/data1/work/query_data/config.yaml', 'r') as f:
        data = yaml.safe_load(f.read())
        config = data['DB']
        da_name = config['db_name']
        db_config = DB_config(**config)
        tasks = [
            {da_name: db_config},
        ]
    
    make_json(tasks)
    

    

    
if __name__ == "__main__":
    retriever = MilvusRetriever(db_name="test2", embedding_type="local")
    retriever.upload(json_path='/home/david/data1/work/query_data/assets/test.json')
    # upload("test2", "/home/david/data1/work/query_data/assets/test.json", embedding_type='local')
    # results = retriever.retrieve("全区人口")
    # print(results)



