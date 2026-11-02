import os
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from utils.config import load_env

load_env()

# Configuration defaults
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
DEFAULT_TIMEOUT_SECONDS = 30

# Short TTLs keep repeated UI reruns from issuing synchronous HTTP requests
# while still noticing a server that has been started/stopped.
STATUS_CACHE_TTL_SECONDS = 30
MODELS_CACHE_TTL_SECONDS = 60


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
        self._cached_status_at: float = 0.0
        self._cached_models: Optional[List[str]] = None
        self._cached_models_at: float = 0.0
        self._cached_model_details: Optional[List[Dict[str, Any]]] = None

    def set_model(self, model: str) -> None:
        """Select the model used by subsequent requests on this client.

        Only this client instance is updated; environment variables are never
        modified, so the selection stays scoped to the current application
        session.
        """
        if not model or not str(model).strip():
            raise ValueError("model must be a non-empty string")
        self.model = str(model).strip()

    def clear_cache(self) -> None:
        """Invalidate cached server status and installed-model information."""
        self._cached_status = None
        self._cached_status_at = 0.0
        self._cached_models = None
        self._cached_models_at = 0.0
        self._cached_model_details = None

    def check_availability(self, force_refresh: bool = False) -> Tuple[bool, str]:
        """Check whether the local Ollama server is running and reachable.

        Results are cached for ``STATUS_CACHE_TTL_SECONDS`` unless
        *force_refresh* is True. Call :meth:`clear_cache` to invalidate both
        this cache and the installed-model cache.
        """
        now = time.monotonic()
        if (
            not force_refresh
            and self._cached_status is not None
            and (now - self._cached_status_at) < STATUS_CACHE_TTL_SECONDS
        ):
            return self._cached_status

        tags_url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(tags_url, headers={"User-Agent": "MapMind/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                self._cached_status_at = time.monotonic()
                if response.status == 200:
                    self._cached_status = (True, "Ollama server is active and reachable.")
                    return self._cached_status
                self._cached_status = (False, f"Ollama returned HTTP status {response.status}.")
                return self._cached_status
        except urllib.error.URLError as e:
            self._cached_status_at = time.monotonic()
            self._cached_status = (
                False,
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is installed and running (`ollama serve`). "
                f"Error: {e.reason if hasattr(e, 'reason') else str(e)}"
            )
            return self._cached_status
        except Exception as e:
            self._cached_status_at = time.monotonic()
            self._cached_status = (False, f"Unexpected error connecting to Ollama: {str(e)}")
            return self._cached_status

    def list_model_details(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return installed model names plus safe metadata from Ollama.

        The Ollama ``/api/tags`` endpoint returns one entry per installed
        model. Only fields actually present in that response are forwarded
        (``name``, ``size``, ``modified_at`` and selected entries from
        ``details``); no capabilities or performance values are invented.

        Results are cached for ``MODELS_CACHE_TTL_SECONDS`` unless
        *force_refresh* is True.
        """
        now = time.monotonic()
        if (
            not force_refresh
            and self._cached_model_details is not None
            and (now - self._cached_models_at) < MODELS_CACHE_TTL_SECONDS
        ):
            return [dict(item) for item in self._cached_model_details]

        tags_url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(tags_url, headers={"User-Agent": "MapMind/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            message = (
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is installed and running (`ollama serve`). "
                f"Error: {e.reason if hasattr(e, 'reason') else str(e)}"
            )
            self._cached_status_at = time.monotonic()
            self._cached_status = (False, message)
            self._cached_model_details = None
            raise OllamaConnectionError(message) from e
        except Exception as e:
            message = f"Failed to fetch models from Ollama: {str(e)}"
            self._cached_status_at = time.monotonic()
            self._cached_status = (False, message)
            self._cached_model_details = None
            raise OllamaConnectionError(message) from e

        if not isinstance(data, dict):
            data = {}
        raw_models = data.get("models", [])
        if not isinstance(raw_models, list):
            raw_models = []

        details: List[Dict[str, Any]] = []
        for raw in raw_models:
            if not isinstance(raw, dict):
                continue
            name = raw.get("name") or raw.get("model")
            if not isinstance(name, str) or not name.strip():
                continue

            item: Dict[str, Any] = {"name": name.strip()}

            size = raw.get("size")
            if isinstance(size, (int, float)) and not isinstance(size, bool) and size >= 0:
                item["size"] = int(size)

            modified_at = raw.get("modified_at")
            if isinstance(modified_at, str) and modified_at.strip():
                item["modified_at"] = modified_at.strip()

            model_meta = raw.get("details")
            if isinstance(model_meta, dict):
                for key in ("parameter_size", "quantization_level", "family", "format"):
                    value = model_meta.get(key)
                    if isinstance(value, str) and value.strip():
                        item[key] = value.strip()

            details.append(item)

        self._cached_model_details = details
        self._cached_models = [item["name"] for item in details]
        self._cached_models_at = time.monotonic()
        # The same successful request also proves the server is reachable.
        self._cached_status_at = self._cached_models_at
        self._cached_status = (True, "Ollama server is active and reachable.")
        return [dict(item) for item in details]

    def list_models(self, force_refresh: bool = False) -> List[str]:
        """Query the list of installed model names from local Ollama.

        Results are cached for ``MODELS_CACHE_TTL_SECONDS`` unless
        *force_refresh* is True.

        Returns
        -------
        List[str]
            List of model names (e.g. ['llama3.2:latest', 'mistral:latest']).
        """
        return [
            item["name"]
            for item in self.list_model_details(force_refresh=force_refresh)
        ]

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
