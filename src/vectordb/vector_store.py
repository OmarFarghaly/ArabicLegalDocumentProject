from qdrant_client import QdrantClient, models

from pydantic import BaseModel

from typing import Literal, List, Dict , Optional

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

class Payload(BaseModel):
    article_number :int
    ar_text : str
    text_en : str
    book: Optional[str | None]
    chapter  : Optional[str | None]
    section : Optional[str | None]
    topic : Optional[str | None]
    is_repealed : bool
    source_page : int
    citation :str
    
#indexing, reterivel 

class QdrantVectorStore:
    
    def __init__(self, host='localhost', port=6333):
        
        self.client = QdrantClient(host=host, port = port)
        
        self.vectors_config = {
            "english" : models.VectorParams(size= english_embedding.model_size , distance=models.Distance.COSINE),
            "arabic" : models.VectorParams(size= arabic_embedding.model_size , distance=models.Distance.COSINE)
        }
        
        #
        self.sparse_vectors_config = {"bm25" : models.SparseVectorParams(modifier= models.Modifier.IDF)}
        
        self.arabic_embedding = arabic_embedding
        
        self.english_embedding = english_embedding
        
    def create_collection(self, collection_name :str ):
        
        collections = self.client.get_collections()
        
        collection_exists = any(
            collection_name == collection
            for collection in collections.collections
        )
        
        if  collection_exists:
            print(f"collection {collection_name} already exists.")
        
            self.client.delete_collection(collection_name=collection_name)
        
        self.client.create_collection(collection_name=collection_name , 
                                            vectors_config=self.vectors_config, 
                                            sparse_vectors_config=self.sparse_vectors_config)
        return True
        
        
    def delete_collection(self, collection_name):
        
        return self.client.delete_collection(collection_name=collection_name)
    
    def create(self , collection_name:str, payload :Payload):
        
        response = self.client.count(collection_name=collection_name)
        
        if  payload.ar_text.strip() and payload.text_en.strip():
            
            #raise ValueError("Both ar_text and text_en are required to create a point")

            ar_vector = self.arabic_embedding.encode(text=payload.ar_text)
            en_vector = self.english_embedding.encode(text=payload.text_en)
        
            
            
            points = [models.PointStruct(id=response.count, 
                                        vector={"english":en_vector , 
                                                "arabic":ar_vector} ,
                                        
                                        payload=payload.model_dump()
                                        
                                        )
            ]
            self.client.upsert(
                collection_name=collection_name, 
                points=points
            )
        
    # async def search(self, collection_name:str , text:str,
    #                 reterival_limit:int, score_threshold:float , reterival_renkad_limit:int,
    #                 lang:Literal['arabic', 'english']):
        
    #     if text and lang == 'arabic':
            
    #         vector = self.arabic_embedding.encode(text=text)
            
    #     elif text and lang == 'english' :
            
    #         vector = self.english_embedding.encode(text = text)
            
    #     prefetch = [ models.Prefetch(
    #                         query=vector,
    #                         using=lang,
    #                         limit=reterival_limit,
    #                         score_threshold=score_threshold
    #     ),
    #                models.Prefetch(
    #                    query=models.Document(text=text , model="Qdrant/bm25")
    #                )
    #     ]
        
    #     response = await self.client.query_points(
    #         collection_name=collection_name, 
    #         prefetch=prefetch,
    #         query=models.FusionQuery(fusion=models.Fusion.RRF),
    #         limit=reterival_renkad_limit,
    #         with_payload=True
    #     )
        
    #     return response.points
        
        
                 