import time
import random
import json
from google import genai
from google.genai import types
from modules.utils.async_buffer import AsyncBuffer
def load_api_keys():
    config_file = 'config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

api_keys = load_api_keys()
gemini_api_keys = api_keys.get("gemini_api_keys", [])

MODELS = {
    "gemini": {
        "model_id": "gemini-2.0-flash",
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_tokens": 8192,
    },
    "gemini_academic": {  # New preset for academic queries
        "model_id": "gemini-2.0-flash",
        "temperature": 0.4,  # Lower temperature for more focused results
        "top_p": 0.9,
        "top_k": 40,
        "max_tokens": 8192,
    }
}

class GeminiClient:
    def __init__(self):
        self.api_key = random.choice(gemini_api_keys) if gemini_api_keys else None
        self.client = genai.Client(api_key=self.api_key)
    
    async def query_gemini(self, query: str, buffer: AsyncBuffer, academic_context: bool = False) -> str:
        start_time = time.time()
        try:
            model_preset = "gemini_academic" if academic_context else "gemini"
            model = MODELS[model_preset]["model_id"]
            
            if buffer.verbose:
                buffer.add_log(f"Querying OrcaStatLLM with model: OrcaStatLLMv1.0" + 
                               (f" (academic context)" if academic_context else ""))
            
            gen_config = types.GenerateContentConfig(
                temperature=MODELS[model_preset]["temperature"],
                top_p=MODELS[model_preset]["top_p"],
                top_k=MODELS[model_preset]["top_k"],
                max_output_tokens=MODELS[model_preset]["max_tokens"],
                response_mime_type="text/plain",
            )
            
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=query)],
                )
            ]
            
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=gen_config
            ):
                if chunk.text:
                    response_text += chunk.text
                    buffer.add_chunk(chunk.text)
            
            elapsed_time = time.time() - start_time
            if buffer.verbose:
                buffer.add_log(f"OrcaStatLLM response completed in {elapsed_time:.2f} seconds")
            
            return response_text
        except Exception as e:
            error_msg = f"Error querying Gemini: {str(e)}"
            buffer.add_log(error_msg, high_level=True)
            buffer.add_chunk(error_msg)
            return error_msg
    
    async def query_academic(self, query: str, buffer: AsyncBuffer) -> str:

        return await self.query_gemini(query, buffer, academic_context=True)
