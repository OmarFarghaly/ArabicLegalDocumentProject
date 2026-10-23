from qdrant_client import AsyncQdrantClient, models
from typing import Literal
from langdetect import detect

from src.config import Config
from src.embeddings import EmbeddingModel
from src.logger import Logger

logger = Logger().logger
config = Config()


class Reterival:
    
    def __init__(self, arabic_embedding: EmbeddingModel, english_embedding: EmbeddingModel,
                 host = 'localhost', port=6333 ):
        
        self.host = host
        self.port = port
        self.english_embedding = english_embedding
        self.arabic_embedding = arabic_embedding
        self.client = AsyncQdrantClient(host=self.host , 
                                        port=self.port)
        logger.info(f"Initialized Reterival with host: {self.host}, port: {self.port}")
        logger.info(f"Arabic embedding model: {self.arabic_embedding.model_path}, size: {self.arabic_embedding.model_size}")
        logger.info(f"English embedding model: {self.english_embedding.model_path}, size: {self.english_embedding.model_size}")
            
    async def search(self, collection_name:str , text:str,
                     lang:Literal['arabic', 'english'],
                    reterival_limit:int=20, score_threshold:float=0.5 , reterival_renkad_limit:int=10):
        logger.info(f"Searching in collection: {collection_name} for text: {text} in language: {lang}")
        if text.strip() and lang == 'arabic':
            logger.info("Encoding text using Arabic embedding model")
            try:
                vector = self.arabic_embedding.encode(text=text)
                logger.info(f"Encoded vector size: {len(vector)}")
            except Exception as e:
                logger.error(f"Error encoding text with Arabic embedding model: {e}")
                raise ValueError(f"Error encoding text with Arabic embedding model: {e}")
        elif text.strip() and lang == 'english' :
            logger.info("Encoding text using English embedding model")
            try:
                vector = self.english_embedding.encode(text = text)
                logger.info(f"Encoded vector size: {len(vector)}")
            except Exception as e:
                logger.error(f"Error encoding text with English embedding model: {e}")
                raise ValueError(f"Error encoding text with English embedding model: {e}")
        else:
            logger.error("Empty text provided for search")
            raise ValueError("Empty text provided for search")
        prefetch = [ models.Prefetch( # semantic meaning dense 
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
        #logger.info(f"Prefetch configuration: {prefetch}")
        try:
            response = await self.client.query_points(
                collection_name=collection_name, 
                prefetch=prefetch,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=reterival_renkad_limit,
                with_payload=True
            )
            logger.info(f"Search completed. Number of points retrieved: {len(response.points)}")
        except Exception as e:
            logger.error(f"Error occurred while querying points: {e}")
            raise ValueError(f"Error occurred while querying points: {e}")
        
        return response.points
        
# async def main():
#     lang_mapping = {"ar":"arabic" , "en":"english"}
    
     
#     from src.embeddings import EmbeddingModel

#     from src.config import Config

#     config = Config()

#     embedding_ar_name = config.ARABIC_EMBEDDING
#     embedding_en_name = config.ENGLISH_EMBEDDING
#     print(f"arabic embedding model name : {embedding_ar_name}")
#     arabic_embedding = EmbeddingModel(model_path= embedding_ar_name , 
#                                     lang='arabic')
#     print(f"english embedding model name : {embedding_en_name}")
#     english_embedding = EmbeddingModel(model_path=embedding_en_name , 
#                                     lang="english") 
    
#     search_clinet = Reterival(arabic_embedding=arabic_embedding, english_embedding=english_embedding)
#     text = "ما هي الأركان الأساسية اللازمة لانعقاد العقد وفقًا للقانون المدني المصري؟"
#     lang = detect(text = text)
    
#     lang = lang_mapping[lang]
    
#     results = await search_clinet.search(
#         collection_name=config.COLLECTION_NAME ,text = text,lang=lang
#     )
    
   
    
# if __name__ =='__main__':
#     import asyncio
    
#     asyncio.run(main())