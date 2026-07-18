from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.2,
)
