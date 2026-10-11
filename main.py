from fastapi import FastAPI
import torch
from contextlib import asynccontextmanager
from sentence_transformers import CrossEncoder
from src.embeddings import EmbeddingModel
from src.config import Config
from src.retrieval import Reterival
from src.reranker import Reranker
from src.api.versions.v1 import rag


@asynccontextmanager
async def lifespan(app:FastAPI):
    config = Config()
    
    app.state.arabic_embedding = EmbeddingModel(model_path=config.ARABIC_EMBEDDING ,
                                                lang="arabic")
    
    app.state.english_embedding = EmbeddingModel(model_path=config.ENGLISH_EMBEDDING,
                                                 lang="english")
    
    app.state.qdrant_reterival =  Reterival(arabic_embedding=app.state.arabic_embedding,
                                            english_embedding=app.state.english_embedding,
                                            host=config.QDRANT_HOST,
                                            port=config.QDRANT_PORT)
    if torch.cuda.is_available():
        
        cross_encoder = CrossEncoder(model_name_or_path=config.RERANKER_MODEL,
                                  trust_remote_code=True).bfloat16().cuda() 
    else :
        
        cross_encoder = CrossEncoder(model_name_or_path=config.RERANKER_MODEL,
                                          trust_remote_code=True).bfloat16()
        
    app.state.reranker = Reranker(reranker_model=cross_encoder)
    
    yield 
    
    await app.state.qdrant_reterival.client.close()
    del app.state.arabic_embedding
    del app.state.english_embedding
    del app.state.reranker
    
app = FastAPI(lifespan=lifespan)

app.include_router(rag.rag_router)

