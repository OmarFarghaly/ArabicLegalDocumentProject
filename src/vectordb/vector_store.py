import time
from typing import Optional

from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException

from src.utils.arabic_text import normalize_arabic_for_sparse

from src.config import Config
from src.embeddings import EmbeddingModel
from src.logger import Logger

config = Config()
logger = Logger().logger

embedding_ar_name = config.ARABIC_EMBEDDING
embedding_en_name = config.ENGLISH_EMBEDDING
logger.info(f"arabic embedding model name : {embedding_ar_name}")
arabic_embedding = EmbeddingModel(model_path= embedding_ar_name , 
                                  lang='arabic')
logger.info(f"english embedding model name : {embedding_en_name}")
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
    
    def __init__(self, host='qdrant', port=6333):
        
        self.client = QdrantClient(host=host, port = port)
        
        self.vectors_config = {
            "english" : models.VectorParams(size= english_embedding.model_size , distance=models.Distance.COSINE),
            "arabic" : models.VectorParams(size= arabic_embedding.model_size , distance=models.Distance.COSINE)
        }
        
        self.sparse_vectors_config = {
            "bm25_english": models.SparseVectorParams(modifier=models.Modifier.IDF),
            "bm25_arabic": models.SparseVectorParams(modifier=models.Modifier.IDF),
        }
        
        self.arabic_embedding = arabic_embedding
        
        self.english_embedding = english_embedding
        
    def create_collection(self, collection_name :str ):
        
        collections = self.client.get_collections()
        
        collection_exists = any(
            collection_name == collection.name
            for collection in collections.collections
        )
        
        if  collection_exists:
            logger.info(f"collection {collection_name} already exists.")
        
            self.client.delete_collection(collection_name=collection_name)
        
        self.client.create_collection(collection_name=collection_name , 
                                            vectors_config=self.vectors_config, 
                                            sparse_vectors_config=self.sparse_vectors_config)
        return True
        
        
    def delete_collection(self, collection_name):
        
        logger.info(f"Deleting collection: {collection_name}")
        return self.client.delete_collection(collection_name=collection_name)
    
    def create(self , collection_name:str, payload :Payload):
        
        logger.info(f"Creating point in collection: {collection_name}")
        response = self.client.count(collection_name=collection_name)
        logger.info(f"Current count of points in collection {collection_name}: {response.count}")
        if  payload.ar_text.strip() and payload.text_en.strip():
            
            #raise ValueError("Both ar_text and text_en are required to create a point")

            ar_sparse_text = normalize_arabic_for_sparse(payload.ar_text)
            ar_vector = self.arabic_embedding.encode(text=payload.ar_text)
            en_vector = self.english_embedding.encode(text=payload.text_en)
        
            logger.info(f"Creating point with ID: {response.count} in collection: {collection_name}")
            
            points = [models.PointStruct(id=response.count, 
                                        vector={"english":en_vector,
                                                "arabic":ar_vector,
                                                "bm25_english": models.Document(
                                                    text=payload.text_en,
                                                    model="Qdrant/bm25",
                                                ),
                                                "bm25_arabic": models.Document(
                                                    text=ar_sparse_text,
                                                    model="Qdrant/bm25",
                                                )},
                                        
                                        payload=payload.model_dump()
                                        
                                        )
            ]
            logger.info(f"Upserting point with ID: {response.count} into collection: {collection_name}")
            for attempt in range(3):
                try:
                    self.client.upsert(
                        collection_name=collection_name,
                        points=points,
                    )
                    break
                except ResponseHandlingException as exc:
                    if attempt == 2:
                        raise
                    delay = 2**attempt
                    logger.warning(
                        f"Qdrant upsert failed ({exc}); retrying in {delay}s "
                        f"({attempt + 1}/3)"
                    )
                    time.sleep(delay)
            logger.info(f"Point with ID: {response.count} upserted successfully into collection: {collection_name}")