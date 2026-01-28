import os
from dotenv import load_dotenv

from utils.config_loader import load_config
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

# Prefer the new langchain-huggingface package, fall back to community embeddings
try:  # pragma: no cover - import-time behavior
    from langchain_huggingface import (
        HuggingFaceEmbeddings as LCHuggingFaceEmbeddings,
    )
except ImportError:  # Fallback for environments without langchain-huggingface installed yet
    from langchain_community.embeddings import (
        HuggingFaceEmbeddings as LCHuggingFaceEmbeddings,
    )
    


log = CustomLogger().get_logger(__name__)


class ModelLoader:
    """
    Loads embedding model and LLM based on configuration and environment variables.
    """

    def __init__(self):
        try:   
            load_dotenv()
            self._validate_env()
            self.config = load_config()
            log.info("configuration_loaded",config_keys=list(self.config.keys()))

        except Exception as e:
            raise DocumentPortalException("Failed to initialize ModelLoader",e) from e

    def _validate_env(self):
        """
        Validate required environment variables.
        """
        required_vars = ["GROQ_API_KEY","GOOGLE_API_KEY","HF_TOKEN"]

        self.api_keys = {key: os.getenv(key) for key in required_vars}
        missing = [key for key, value in self.api_keys.items() if not value]

        if missing:
            log.error("missing_environment_variables", missing_vars=missing)
            raise DocumentPortalException(f"Missing required environment variables: {missing}")

        log.info(
            "environment_variables_validated",
            available_keys=list(self.api_keys.keys())
        )

    def load_embeddings(self):
        """
        Load and return HuggingFace embedding model.
        """
        try:
            model_name = self.config["embedding_model"]["model_name"]

            log.info("loading_embedding_model", model=model_name)

            # Use the non-deprecated langchain-huggingface class when available,
            # otherwise fall back to the community implementation.
            return LCHuggingFaceEmbeddings(model_name=model_name)

        except Exception as e:
            log.error("embedding_model_load_failed",error=str(e))
            raise DocumentPortalException("Failed to load embedding model",e) from e

    def load_llm(self):
        """
        Load and return the configured LLM.
        """
        try:
            llm_block = self.config["llm"]
            provider_key = os.getenv("LLM_PROVIDER", "groq")

            if provider_key not in llm_block:
                raise ValueError(
                    f"LLM provider '{provider_key}' not found in config"
                )

            llm_config = llm_block[provider_key]
            provider = llm_config["provider"]
            model_name = llm_config["model_name"]
            temperature = llm_config.get("temperature", 0)
            max_tokens = llm_config.get("max_output_tokens", 2048)

            log.info("loading_llm",provider=provider,model=model_name
            )

            if provider == "groq":
                return ChatGroq(
                    model=model_name,
                    api_key=self.api_keys["GROQ_API_KEY"],
                    temperature=temperature
                )

            elif provider == "google":
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=self.api_keys["GOOGLE_API_KEY"],
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )

            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            log.error("llm_load_failed",error=str(e))
            raise DocumentPortalException("Failed to load LLM",e) from e



if __name__ == "__main__":
    loader = ModelLoader()

    embeddings = loader.load_embeddings()
    print("Embedding model loaded successfully")
    print("Embedding sample:", embeddings.embed_query("Hello world")[:5])

    llm = loader.load_llm()
    response = llm.invoke("Hello, how are you?")
    print("LLM response:", response.content)
