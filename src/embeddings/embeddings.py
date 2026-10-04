from sentence_transformers import SentenceTransformer

from typing import List, Literal

class EmbeddingModel:
    
    def __init__(self , model_path:str , lang:Literal['english', 'arabic']):
        
        self.model_path = model_path
        
        self.encoder = SentenceTransformer(self.model_path)
        
        self.lang = lang
        
    def encode(self, text:str)->List[float]:
        
        if text:
            
            vector = self.encoder.encode(inputs=text).tolist()

            return vector
        else :
            
            raise ValueError("text is empty")
    
    @property
    
    def model_size(self)->int:
        
        return self.encoder.get_embedding_dimension()
    
    
            