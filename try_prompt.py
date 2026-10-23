"""Try the prompt template by hand.

Usage (from the project root):
    uv run python try_prompt.py "هل العقد ملزم؟" 147 148

Prints the exact messages VLLMClient would send. If LLM_MODEL_NAME (and
optionally LLM_BASE_URL) are set in .env, it also sends them to the server.
"""

import json
import os
import sys

from dotenv import load_dotenv
from langdetect import detect

from src.prompt_template import build_llm_request

load_dotenv()


def build_messages(request) -> list[dict]:
    """Same layout as VLLMClient.generate (without chat history)."""
    user = ""
    if request.context_documents:
        user += "Legal context:\n"
        for i, document in enumerate(request.context_documents, start=1):
            user += f"[Document {i}]\n{document}\n\n"
    user += f"Current question:\n{request.query}"
    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": user},
    ]


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "هل العقد ملزم؟"
    detected_language = detect(question)
    language = {"ar": "arabic", "en": "english"}.get(detected_language)
    if language is None:
        raise ValueError(f"Unsupported question language: {detected_language}")

    numbers = [int(n) for n in sys.argv[2:]] or [147]
    with open("data/processed/articles.json", encoding="utf-8") as file:
        articles = json.load(file)
    payloads = [a for a in articles if a["article_number"] in numbers]

    messages = build_messages(
        build_llm_request(question, payloads, language=language)
    )
    for message in messages:
        print(f"===== {message['role']} =====\n{message['content']}\n")

    model = os.getenv("LLM_MODEL_NAME")
    if not model:
        print("LLM_MODEL_NAME is not set, so nothing was sent to a model.")
        return

    from openai import OpenAI

    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("LLM_API_KEY", "EMPTY"),
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=512,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": os.getenv(
                    "LLM_ENABLE_THINKING", "false"
                ).lower() == "true",
            },
        },
    )
    print("===== answer =====")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()