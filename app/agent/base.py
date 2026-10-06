import os
from abc import ABC
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    def __init__(self, default_openai_model: str = "gpt-4o-mini", default_gemini_model: str = "gemini-2.5-flash"):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        # Prioritize Gemini if GEMINI_API_KEY is configured
        if self.gemini_key:
            from google import genai
            self.provider = "gemini"
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            self.model = os.getenv("GEMINI_MODEL", default_gemini_model)
        elif self.openai_key:
            from openai import OpenAI
            self.provider = "openai"
            self.openai_client = OpenAI(api_key=self.openai_key)
            self.model = default_openai_model
        else:
            self.provider = "none"
            self.model = default_gemini_model

    def parse_structured(
        self,
        user_prompt: str,
        system_prompt: str,
        output_class: Type[T],
        temperature: float = 0.5,
    ) -> Optional[T]:
        if self.provider == "gemini":
            from google.genai import types
            models_to_try = [self.model, "gemini-2.0-flash", "gemini-1.5-flash"]
            # Deduplicate while preserving order
            models_to_try = list(dict.fromkeys(models_to_try))

            last_error = None
            for model_candidate in models_to_try:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_candidate,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            response_mime_type="application/json",
                            response_schema=output_class,
                            temperature=temperature,
                        ),
                    )
                    if hasattr(response, "parsed") and isinstance(response.parsed, output_class):
                        return response.parsed
                    if response.text:
                        return output_class.model_validate_json(response.text)
                except Exception as e:
                    last_error = e
                    if "503" in str(e) or "high demand" in str(e).lower():
                        continue  # Try next model candidate
                    else:
                        break

            print(f"[Gemini Error]: {last_error}")
            return None

        elif self.provider == "openai":
            try:
                response = self.openai_client.responses.parse(
                    model=self.model,
                    instructions=system_prompt,
                    temperature=temperature,
                    input=user_prompt,
                    text_format=output_class,
                )
                return response.output_parsed
            except Exception as e:
                print(f"[OpenAI Error]: {e}")
                return None
        else:
            raise ValueError(
                "Neither GEMINI_API_KEY nor OPENAI_API_KEY is configured in your .env file. "
                "Please add GEMINI_API_KEY=your_key to your .env file."
            )
