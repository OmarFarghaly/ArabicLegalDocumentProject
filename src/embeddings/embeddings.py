from sentence_transformers import SentenceTransformer

from typing import List, Literal

from src.logger import Logger

logger = Logger().logger

class EmbeddingModel:
    
    def __init__(self , model_path:str , lang:Literal['english', 'arabic']):
        
        self.model_path = model_path
        logger.info(f"Initializing EmbeddingModel with model_path: {self.model_path} and lang: {lang}")
        self.encoder = SentenceTransformer(self.model_path,trust_remote_code=True)
        
        self.lang = lang
        
    def encode(self, text:str)->List[float]:
        logger.info(f"Encoding text: {text}")
        if text:
            logger.info(f"Text length: {len(text)}")
            vector = self.encoder.encode(inputs=text).tolist()

            return vector
        else :
            logger.error("Empty text provided for encoding")
            raise ValueError("text is empty")
    
    @property
    def model_size(self)->int:
        logger.info(f"Retrieving model size for {self.model_path}")
        return self.encoder.get_embedding_dimension()
    
    
            