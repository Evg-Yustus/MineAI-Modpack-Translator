import requests

from mineai.constants import KOBOLD_API
from mineai.engines.llm_common import BatchLlmEngine


class KoboldEngine(BatchLlmEngine):
    def __init__(self, mode: str = "safe", context: str = "", prompt_type: str = "mods", retries: int = 3) -> None:  # <--- ДОБАВИЛИ retries: int = 3
        super().__init__(
            mode=mode,
            context=context,
            prompt_type=prompt_type,
            call_api=self._request,
            label="KoboldCPP",
            retries=retries,  # <--- НОВАЯ СТРОКА
        )

    def _request(self, prompt: str, max_tokens: int) -> str | None:
        response = requests.post(
            KOBOLD_API,
            json={
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": max_tokens,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()