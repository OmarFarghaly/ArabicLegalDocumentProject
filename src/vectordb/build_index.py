from .vector_store import *
from src.vectordb.vector_store import QdrantVectorStore , Payload
from src.config import Config
import json
import tqdm
import asyncio
config = Config()

class IndexingStore:
    
    def __init__(self,  data_path:str, vector_store = QdrantVectorStore()):
        
        self.vector_store = vector_store
        
        self.data_path = data_path
        
    def read_data(self):
        
        with open(self.data_path , encoding="utf-8") as file:
            
            data = json.load(file)
            
        return data
    
    def build_index(self , collection_name = config.COLLECTION_NAME):
        
        #build collection 
        self.vector_store.delete_collection(collection_name=collection_name)
        self.vector_store.create_collection(collection_name=collection_name)
        
        #add data 
        for record in tqdm.tqdm(self.read_data()):
            
            text_en = (record.get("text_en") or "").strip()
            ar_text = (record.get("ar_text") or "").strip()
            if len(text_en) < 10 or len(ar_text) < 10:
                continue
            
            payload = Payload(**record)
            
            self.vector_store.create(collection_name=collection_name , 
                                        payload=payload)
            
        

        
        return True

def main():
    
    index_store = IndexingStore(data_path="./data/processed/articles.json")
    
    success = index_store.build_index()
    
    if success :
        
        print("Index created well")
        
    else :
        
        print("index not created")
            
if __name__ == '__main__':
    main()
        