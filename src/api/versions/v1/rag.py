from fastapi import APIRouter, Request
from src.schemas import InputRequest
from langdetect import detect
from src.config import Config
from src.schemas import Payload, OutputResponse

rag_router = APIRouter(prefix="/api/v1/rag")

lang_mapping = {"ar":"arabic" , "en":"english"}
config = Config()

@rag_router.post("/answer")
async def answer(input_question:InputRequest, request:Request):

    qdrant_reterival = request.app.state.qdrant_reterival
    
    lang = detect(text = input_question.question)
        
    lang = lang_mapping[lang]
    
    results = await qdrant_reterival.search(
        collection_name=config.COLLECTION_NAME ,
        text = input_question.question,
        lang=lang
    )
    
    outputs = [Payload(**result.payload)  for result in results]
    
    return OutputResponse(outputs = outputs )
    
    
    
    


