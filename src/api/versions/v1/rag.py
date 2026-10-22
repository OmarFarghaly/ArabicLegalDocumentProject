from fastapi import APIRouter, Request
from src.schemas import InputRequest
from langdetect import detect
from src.config import Config
from src.schemas import Payload, OutputResponse
from src.cache import make_key

rag_router = APIRouter(prefix="/api/v1/rag")

lang_mapping = {"ar":"arabic" , "en":"english"}
config = Config()

def get_payload_from_points(points):
    
    if points:
        return [Payload(**point.payload) for point in points]
    return None

@rag_router.post("/answer")
async def answer(input_question:InputRequest, request:Request):

    qdrant_reterival = request.app.state.qdrant_reterival
    
    reranker = request.app.state.reranker

    cache = getattr(request.app.state, "cache", None)
    cache_key = None
    if cache is not None:
        cache_key = make_key(
            "rag:retrieval",
            input_question.question,
            collection=config.COLLECTION_NAME,
            limit=config.RETERIVAL_LIMIT,
            rrf=config.RETERIVAL_RRF_LIMIT,
            reranked=config.RETERIVAL_RERANKED_LIMIT,
            reranker=config.RERANKER_MODEL,
            arabic_embedding=config.ARABIC_EMBEDDING,
            english_embedding=config.ENGLISH_EMBEDDING,
            index_version=config.CACHE_INDEX_VERSION,
        )
        cached = await cache.get(cache_key)
        if cached is not None:
            return OutputResponse(**cached)
    
    lang = detect(text = input_question.question)
        
    lang = lang_mapping[lang]
    
    points = await qdrant_reterival.search(
        collection_name=config.COLLECTION_NAME ,
        text = input_question.question,
        lang=lang,
        reterival_limit = config.RETERIVAL_LIMIT,
        reterival_renkad_limit = config.RETERIVAL_RRF_LIMIT
    )
    
    payloads = get_payload_from_points(points)
    
    reanked_payloads = reranker.rerank(query=input_question.question, 
                                       payloads=payloads,
                                       lang=lang,
                                       limit=config.RETERIVAL_RERANKED_LIMIT)
    
    
    
    response = OutputResponse(outputs = reanked_payloads )

    if cache is not None and reanked_payloads:
        await cache.set(cache_key, response.model_dump())

    return response