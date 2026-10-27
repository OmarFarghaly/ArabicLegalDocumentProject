from .vector_store import *
from src.vectordb.vector_store import QdrantVectorStore , Payload
from src.config import Config
from src.logger import Logger
import json
import tqdm
config = Config()
logger = Logger().logger

class IndexingStore:
    
    def __init__(
        self,
        data_path: str,
        vector_store: QdrantVectorStore | None = None,
    ):
        if vector_store is None:
            vector_store = QdrantVectorStore(
                host=config.QDRANT_HOST,
                port=config.QDRANT_PORT,
            )
        self.vector_store = vector_store
        
        self.data_path = data_path
        
    def read_data(self):
        logger.info("Reading data from file: {}".format(self.data_path))  
              
        with open(self.data_path , encoding="utf-8") as file:
            
            data = json.load(file)
        
        logger.info("Data read successfully from file: {}".format(self.data_path))
        
        return data
    
    def build_index(self , collection_name = config.COLLECTION_NAME):
        
        #build collection 
        logger.info("Building index for collection: {}".format(collection_name))
        self.vector_store.delete_collection(collection_name=collection_name)
        self.vector_store.create_collection(collection_name=collection_name)
        
        #add data 
        logger.info("Adding data to collection: {}".format(collection_name))
        failed_records = 0
        try:
            for record in tqdm.tqdm(self.read_data()):
                try:
                    
                    text_en = (record.get("text_en") or "").strip()
                    ar_text = (record.get("ar_text") or "").strip()
                    if len(text_en) < 10 or len(ar_text) < 10:
                        continue
                    
                    payload = Payload(**record)
                    
                    logger.info("Adding record to collection: {}".format(collection_name))
                    
                    self.vector_store.create(collection_name=collection_name , 
                                                payload=payload)
                    
                    logger.info("Record added successfully to collection: {}".format(collection_name))
                except Exception as e:
                    failed_records += 1
                    logger.error("Error adding record to collection: {}".format(collection_name))
                    logger.error(e)
                    continue
                
            if failed_records:
                logger.error(
                    f"Index build failed for {failed_records} record(s)"
                )
                return False

            logger.info("Data added successfully to collection: {}".format(collection_name))
        except Exception as e:
            logger.error("Error adding data to collection: {}".format(collection_name))
            logger.error(e)
            return False

        
        return True

def main():
    
    logger.info("Starting index creation process")
    
    index_store = IndexingStore(data_path="./data/processed/articles.json")
    
    success = index_store.build_index()
    
    logger.info("Index creation process completed")
    
    if success :
        
        logger.info("Index created well")
        
    else :
        
        logger.error("Index not created")
        raise SystemExit(1)
            
if __name__ == '__main__':
    main()
        