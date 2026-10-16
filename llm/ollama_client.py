import os
import json
import urllib.request
import urllib.error
from typing import List, Optional, Tuple, Dict, Any

from utils.config import load_env

load_env()

# Configuration defaults
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
DEFAULT_TIMEOUT_SECONDS = 30


class OllamaError(Exception):
    """Base exception for Ollama client errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when connecting to the local Ollama server fails."""
    pass


class OllamaModelNotFoundError(OllamaError):
    """Raised when the specified model is not installed locally in Ollama."""
    pass


class OllamaClient:
    """Lightweight local Ollama client using standard library HTTP requests."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.timeout = int(timeout or os.getenv("OLLAMA_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
        self._cached_status: Optional[Tuple[bool, str]] = None

    def check_availability(self, force_refresh: bool = False) -> Tuple[bool, str]:
        """Check whether the local Ollama server is running and reachable."""
        if not force_refresh and self._cached_status is not None:
            return self._cached_status

        tags_url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(tags_url, headers={"User-Agent": "MapMind/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    self._cached_status = (True, "Ollama server is active and reachable.")
                    return self._cached_status
                self._cached_status = (False, f"Ollama returned HTTP status {response.status}.")
                return self._cached_status
        except urllib.error.URLError as e:
            self._cached_status = (
                False,
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is installed and running (`ollama serve`). "
                f"Error: {e.reason if hasattr(e, 'reason') else str(e)}"
            )
            return self._cached_status
        except Exception as e:
            self._cached_status = (False, f"Unexpected error connecting to Ollama: {str(e)}")
            return self._cached_status

    def list_models(self) -> List[str]:
        """Query the list of installed models from local Ollama.

        Returns
        -------
        List[str]
            List of model names (e.g. ['llama3.2:latest', 'mistral:latest']).
        """
        tags_url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(tags_url, headers={"User-Agent": "MapMind/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                return [m for m in models if m]
        except Exception as e:
            raise OllamaConnectionError(f"Failed to fetch models from Ollama: {str(e)}") from e

    def is_model_installed(self, model_name: Optional[str] = None) -> bool:
        """Check whether a specific model is installed locally.

        Matches exact name or base name (e.g. 'llama3.2' matches 'llama3.2:latest').
        """
        target = (model_name or self.model).strip().lower()
        try:
            installed_models = [m.lower() for m in self.list_models()]
            for m in installed_models:
                if m == target or m.split(":")[0] == target or target.split(":")[0] == m.split(":")[0]:
                    return True
            return False
        except OllamaConnectionError:
            return False

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate a text response from the local Ollama LLM.

        Parameters
        ----------
        prompt : str
            The input prompt for the model.
        system : Optional[str]
            Optional system prompt instructions.
        model : Optional[str]
            Target model name. If None, uses client's configured model.
        timeout : Optional[int]
            Request timeout in seconds.
        temperature : float
            Sampling temperature (default 0.2 for deterministic adherence).

        Returns
        -------
        str
            The model's generated response string.

        Raises
        ------
        OllamaConnectionError
            If connection to local Ollama fails or times out.
        OllamaModelNotFoundError
            If the requested model is not downloaded in Ollama.
        """
        target_model = model or self.model
        req_timeout = timeout or self.timeout

        # Check connectivity
        is_up, msg = self.check_availability()
        if not is_up:
            raise OllamaConnectionError(msg)

        # Check model installation
        if not self.is_model_installed(target_model):
            available = self.list_models()
            raise OllamaModelNotFoundError(
                f"Model '{target_model}' is not installed in local Ollama. "
                f"Available models: {available if available else 'None'}. "
                f"Run `ollama pull {target_model}` to download it, or configure OLLAMA_MODEL."
            )

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "think": False,  # Disable extended thinking for Qwen3/thinking models
            "options": {
                "temperature": temperature,
            },
        }
        if system:
            payload["system"] = system

        req_data = json.dumps(payload).encode("utf-8")
        gen_url = f"{self.base_url}/api/generate"

        req = urllib.request.Request(
            gen_url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MapMind/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                # qwen3 thinking models may return content in 'thinking' with empty 'response'
                text = resp_data.get("response", "").strip()
                if not text:
                    text = resp_data.get("thinking", "").strip()
                return text
        except urllib.error.URLError as e:
            raise OllamaConnectionError(f"Ollama request error during generation: {str(e)}") from e
        except Exception as e:
            raise OllamaError(f"Unexpected error calling Ollama generate API: {str(e)}") from e
