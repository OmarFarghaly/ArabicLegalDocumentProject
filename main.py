from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.embeddings import EmbeddingModel
from src.config import Config
from src.retrieval import Reterival
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
    
    yield 
    
    await app.state.qdrant_reterival.client.close()
    del app.state.arabic_embedding
    del app.state.english_embedding
    
app = FastAPI(lifespan=lifespan)

app.include_router(rag.rag_router)

