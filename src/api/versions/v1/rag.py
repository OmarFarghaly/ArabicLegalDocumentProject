from fastapi import APIRouter, Request
from langdetect import detect

from src.config import Config
from src.prompt_template import build_llm_request, ensure_article_citations
from src.schemas import InputRequest, LLMResponse, Payload
from src.reranker.reranker import Reranker
from src.logger import Logger

logger = Logger().logger

rag_router = APIRouter(prefix="/api/v1/rag")

lang_mapping = {"ar": "arabic", "en": "english"}

config = Config()


def get_payload_from_points(points):

    if points:
        return [Payload(**point.payload) for point in points]
    return None


# embeds the question with the same model used for retrieval
def embed_question(request: Request, text: str, lang: str):
    embedding = getattr(request.app.state, f"{lang}_embedding")
    return embedding.embed_query(text)  # change to the real method name


@rag_router.post("/answer", response_model=LLMResponse)
async def answer(input_question: InputRequest, request: Request):

    qdrant_reterival = request.app.state.qdrant_reterival
    logger.info("Retrieved QdrantReterival instance")
    reranker = request.app.state.reranker

    lang = detect(text=input_question.question)
    try:
        lang = lang_mapping[lang]
    except KeyError:
        logger.error(f"Unsupported language detected: {lang}")
        raise ValueError(f"Unsupported language detected: {lang}")

    logger.info(f"Detected language: {lang}")
    logger.info(f"Input question: {input_question.question}")

    # semantic cache lookup, before any retrieval work
    semantic_cache = request.app.state.semantic_cache
    vec = None
    if semantic_cache is not None:
        vec = embed_question(request, input_question.question, lang)
        cached = await semantic_cache.get(lang, vec)
        if cached is not None:
            try:
                return LLMResponse.model_validate_json(cached)
            except ValueError:
                logger.warning("Invalid cached entry, ignoring it")

    points = await qdrant_reterival.search(
        collection_name=config.COLLECTION_NAME,
        text=input_question.question,
        lang=lang,
        reterival_limit=config.RETERIVAL_LIMIT,
        reterival_renkad_limit=config.RETERIVAL_RRF_LIMIT,
    )
    logger.info(f"Retrieved {len(points)} points from Qdrant for the query: {input_question.question}")

    payloads = get_payload_from_points(points)

    reanked_payloads = reranker.rerank(
        query=input_question.question,
        payloads=payloads,
        lang=lang,
        limit=config.RETERIVAL_RERANKED_LIMIT,
    )

    llm_request = build_llm_request(
        query=input_question.question,
        payloads=reanked_payloads,
        language=lang,
        max_docs=config.RETERIVAL_RERANKED_LIMIT,
        max_chars=24000,
    )
    response = await request.app.state.llm.generate(llm_request)
    response.answer = ensure_article_citations(
        response.answer,
        reanked_payloads,
        lang,
    )
    logger.info(f"Generated answer for question: {input_question.question}")
    logger.info(f"Answer: {response.answer}")

    #  store the final response (after citations) in the cache
    if semantic_cache is not None:
        await semantic_cache.set(
            lang,
            input_question.question,
            vec,
            response.model_dump_json(),
        )

    return response