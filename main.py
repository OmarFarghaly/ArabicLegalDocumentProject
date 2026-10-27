from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import torch
from contextlib import asynccontextmanager
from sentence_transformers import CrossEncoder
from src.embeddings import EmbeddingModel
from src.config import Config
from src.retrieval import Retrieval
from src.reranker import Reranker
from src.api.versions.v1 import rag
from src.llm.factory import get_llm
from src.logger import Logger
from uuid import uuid4
import time
from datetime import datetime, timezone
from src.cache import SemanticCache
from redis.asyncio import Redis
logger = Logger().logger


@asynccontextmanager
async def lifespan(app:FastAPI):
    config = Config()
    app.state.config = config
    
    logger.info("Initializing Embedding Models for Arabic Language.")
    
    app.state.arabic_embedding = EmbeddingModel(model_path=config.ARABIC_EMBEDDING ,
                                                lang="arabic")
    logger.info("Initializing Embedding Models for English Language.")
    
    app.state.english_embedding = EmbeddingModel(model_path=config.ENGLISH_EMBEDDING,
                                                 lang="english")
    logger.info("Initializing Qdrant Retrieval instance.")
    app.state.qdrant_retrieval =  Retrieval(arabic_embedding=app.state.arabic_embedding,
                                            english_embedding=app.state.english_embedding,
                                            host=config.QDRANT_HOST,
                                            port=config.QDRANT_PORT)
    hf_token = os.getenv("HF_TOKEN") or None
    if torch.cuda.is_available():
        logger.info("CUDA is available. Initializing CrossEncoder on GPU.")
        logger.info(f"Loading reranker model: {config.RERANKER_MODEL}")
        cross_encoder = CrossEncoder(model_name_or_path=config.RERANKER_MODEL,
                                  trust_remote_code=True,
                                  token=hf_token,
                                  device="cuda",
                                  model_kwargs={"dtype": torch.float16}).eval()
        logger.info("CrossEncoder loaded successfully on GPU.")
    else :
        logger.info("CUDA is not available. Initializing CrossEncoder on CPU.")
        logger.info(f"Loading reranker model: {config.RERANKER_MODEL}")
        cross_encoder = CrossEncoder(model_name_or_path=config.RERANKER_MODEL,
                                          trust_remote_code=True,
                                          token=hf_token,
                                          model_kwargs={"dtype": torch.float16}).eval()
        logger.info("CrossEncoder loaded successfully on CPU.")
    logger.info("Initializing Reranker instance.")    
    app.state.reranker = Reranker(reranker_model=cross_encoder)
    logger.info("Initializing LLM instance.")
    app.state.llm = get_llm(config) 
    if config.CACHE_ENABLED:
        app.state.semantic_cache = SemanticCache(
            Redis(host=config.REDIS_HOST,
                  port=config.REDIS_PORT,
                  socket_timeout=0.5,
                  socket_connect_timeout=0.5),
            ttl=config.CACHE_TTL_SECONDS,
            threshold=config.SEMANTIC_CACHE_THRESHOLD,
        )
    else:
        app.state.semantic_cache = None
    
    yield 

    logger.info("Shutting down application and closing resources.")
    if app.state.semantic_cache is not None:
        await app.state.semantic_cache.client.aclose()
    await app.state.qdrant_retrieval.client.close()
    await app.state.llm.close()
    logger.info("Resources closed successfully.")
    del app.state.arabic_embedding
    del app.state.english_embedding
    del app.state.reranker
    logger.info("Application shutdown complete.")
    
app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(request: Request):
    checks = {}
    config = request.app.state.config

    try:
        point_count = await request.app.state.qdrant_reterival.client.count(
            collection_name=config.COLLECTION_NAME,
            exact=False,
        )
        checks["qdrant"] = "healthy" if point_count.count > 0 else "unhealthy"
        if point_count.count == 0:
            logger.error("Health check failed: Qdrant collection has no points")
    except Exception as exc:
        logger.error(f"Health check failed for Qdrant: {exc}")
        checks["qdrant"] = "unhealthy"

    semantic_cache = request.app.state.semantic_cache
    if semantic_cache is None:
        checks["redis"] = "disabled"
    else:
        try:
            await semantic_cache.client.ping()
            checks["redis"] = "healthy"
        except Exception as exc:
            logger.error(f"Health check failed for Redis: {exc}")
            checks["redis"] = "unhealthy"

    try:
        checks["vllm"] = (
            "healthy"
            if await request.app.state.llm.health_check()
            else "unhealthy"
        )
    except Exception as exc:
        logger.error(f"Health check failed for vLLM: {exc}")
        checks["vllm"] = "unhealthy"

    if any(status == "unhealthy" for status in checks.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "checks": checks},
        )

    return {"status": "healthy", "checks": checks}


@app.middleware("http")
async def add_security_headers(request, call_next):
    request_id = str(uuid4())
    requested_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"Processing request {request_id} for path: {request.url.path}")
    logger.info(f"Request {request_id} received at: {requested_at}")
    start_time = time.perf_counter()
    response = await call_next(request)
    end_time = time.perf_counter()
    requested_dt = datetime.now(timezone.utc).isoformat()
    logger.info(f"Request {request_id} processed in {end_time - start_time:.2f} seconds")
    logger.info(f"Request {request_id} completed at: {requested_dt}")
    return response

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],    
)
app.include_router(rag.rag_router)
