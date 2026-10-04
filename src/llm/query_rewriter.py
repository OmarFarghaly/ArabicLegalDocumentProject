from src.schemas import ChatMessage

class QueryRewriter:

    def rewrite(
        self,
        current_query: str,
        chat_history: list[ChatMessage],
    ) -> str:
        ...