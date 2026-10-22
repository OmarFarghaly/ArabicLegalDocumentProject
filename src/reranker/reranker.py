from sentence_transformers import CrossEncoder
from src.schemas import Payload
from typing import List, Literal
from src.logger import Logger
logger = Logger().logger

class Reranker:
    
    def __init__(self, reranker_model:CrossEncoder):
        
        self.reranker_model = reranker_model
        
    def rerank(self, query :str , payloads:List[Payload], lang:Literal['arabic', 'english'],
               limit:int)->List[Payload]:
        
        if payloads and query.strip():
            logger.info(f"Reranking payloads for query: {query}")
            docs =[item.ar_text if lang=='arabic' else item.text_en for  item in payloads]
            
            pairs = [(query , doc) for doc in docs]    
            
            scores = self.reranker_model.predict(pairs)
            
            sorted_docs = sorted(list(zip(payloads, scores)), key=lambda x:x[1], reverse=True)
            
            sorted_payloads = [doc[0] for doc in sorted_docs[:limit]]
            
            return sorted_payloads
        else:
            logger.error("No payloads or empty query provided for reranking")
            return payloads[:limit]
            
            

            
            
            

