from fastapi import APIRouter, Request
from src.schemas import InputRequest
from langdetect import detect
from src.config import Config
from src.schemas import Payload, OutputResponse

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
    
    
    
    return OutputResponse(outputs = reanked_payloads )
    
    
    
    


