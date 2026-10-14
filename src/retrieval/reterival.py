from qdrant_client import AsyncQdrantClient, models
from typing import Literal
from langdetect import detect

from src.embeddings import EmbeddingModel

from src.config import Config

config = Config()


class Reterival:
    
    def __init__(self, arabic_embedding, english_embedding,
                 host = 'localhost', port=6333 ):
        
        self.host = host
        self.port = port
        self.english_embedding = english_embedding
        self.arabic_embedding = arabic_embedding
        self.client = AsyncQdrantClient(host=self.host , 
                                        port=self.port)
        
            
    async def search(self, collection_name:str , text:str,
                     lang:Literal['arabic', 'english'],
                    reterival_limit:int=20, score_threshold:float=0.5 , reterival_renkad_limit:int=10):
        
        if text.strip() and lang == 'arabic':
            
            vector = self.arabic_embedding.encode(text=text)
            
        elif text.strip() and lang == 'english' :
            
            vector = self.english_embedding.encode(text = text)
            
        prefetch = [ models.Prefetch(
                            query=vector,
                            using=lang,
                            limit=reterival_limit,
                            score_threshold=score_threshold
        ),
                   models.Prefetch(
                       query=models.Document(text=text , model="Qdrant/bm25"),
                       using=f"bm25_{lang}",
                       limit=reterival_limit
                   )
        ]
        
        response = await self.client.query_points(
            collection_name=collection_name, 
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=reterival_renkad_limit,
            with_payload=True
        )
        
        return response.points
        
async def main():
    lang_mapping = {"ar":"arabic" , "en":"english"}
    
     
    from src.embeddings import EmbeddingModel

    from src.config import Config

    config = Config()

    embedding_ar_name = config.ARABIC_EMBEDDING
    embedding_en_name = config.ENGLISH_EMBEDDING
    print(f"arabic embedding model name : {embedding_ar_name}")
    arabic_embedding = EmbeddingModel(model_path= embedding_ar_name , 
                                    lang='arabic')
    print(f"english embedding model name : {embedding_en_name}")
    english_embedding = EmbeddingModel(model_path=embedding_en_name , 
                                    lang="english") 
    
    search_clinet = Reterival(arabic_embedding=arabic_embedding, english_embedding=english_embedding)
    text = "ما هي الأركان الأساسية اللازمة لانعقاد العقد وفقًا للقانون المدني المصري؟"
    lang = detect(text = text)
    
    lang = lang_mapping[lang]
    
    results = await search_clinet.search(
        collection_name=config.COLLECTION_NAME ,text = text,lang=lang
    )
    
   
    
if __name__ =='__main__':
    import asyncio
    
    asyncio.run(main())