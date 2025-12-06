from transformers import AutoTokenizer, AutoModel
from typing_extensions import List
import re
import torch
import asyncio
from dotenv import load_dotenv
load_dotenv()
import os


class SentenceQuery:
    def __init__(self):
        model_path = os.environ.get("EMBEDDING_MODEL_PATH", "BAAI/bge-large-en-v1.5")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path).to("cuda:0").eval()

    def pre_data(self, data : str):
        sentences = re.split(r"(?<=[。！？\n])\s*", data)
        encoded_input = self.tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
        return encoded_input
    
    async def single_paper_embedding(self, paper: str) -> torch.Tensor:
        encoded_input = self.pre_data(paper)
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            # Perform pooling. In this case, cls posoling.
            sentence_embeddings = model_output[0][:, 0]
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        return sentence_embeddings
    
    async def batch_paper_embedding(self, papers: List[str]) -> List[torch.Tensor]:
        tasks = [asyncio.create_task(self.single_paper_embedding(paper)) for paper in papers]
        return await asyncio.gather(*tasks)
    
    async def single_similar_caculate(self, source : torch.Tensor, target : torch.Tensor) -> float:
        return torch.matmul(source, target.transpose(-1, -2))[0][0].item()

    async def query(self, sentence: str, papers: List[str], top_k : int = 1):
        source, targets = await asyncio.gather(
            self.single_paper_embedding(sentence),
            self.batch_paper_embedding(papers)
        )

        similarities = await asyncio.gather(
            *[self.single_similar_caculate(source, t) for t in targets]
        )

        result = sorted(
            list(map(lambda x: {"paper": x[0], "similarity": x[1]}, zip(papers, similarities))), 
            key=lambda x : x['similarity'], 
            reverse=True
        )

        return result[:top_k]
    
if __name__ == "__main__":
    model = SentenceQuery()

    

