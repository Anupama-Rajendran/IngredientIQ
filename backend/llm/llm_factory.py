"""Factory for creating LLM instances."""
from typing import Optional
from config import settings


class LLMFactory:
    """Factory for creating language model instances."""
    
    @staticmethod
    def create_llm(provider: Optional[str] = None, model: Optional[str] = None):
        """Create an LLM instance.
        
        Args:
            provider: LLM provider (anthropic, openai). Uses settings if None.
            model: Model name. Uses settings if None.
            
        Returns:
            LLM instance or None if API key not configured
        """
        provider = provider or settings.LLM_PROVIDER
        model = model or settings.LLM_MODEL
        
        # Check if API key is configured (not placeholder)
        if provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
                print("⚠️  Warning: ANTHROPIC_API_KEY not configured. Using fallback mode (knowledge base only).")
                return None
            return LLMFactory._create_anthropic_llm(model)
        elif provider == "openai":
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
                print("⚠️  Warning: OPENAI_API_KEY not configured. Using fallback mode (knowledge base only).")
                return None
            return LLMFactory._create_openai_llm(model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    @staticmethod
    def _create_anthropic_llm(model: str):
        """Create Anthropic Claude LLM.
        
        Args:
            model: Claude model name
            
        Returns:
            Claude LLM instance
        """
        try:
            from langchain_anthropic import ChatAnthropic
            
            return ChatAnthropic(
                model=model,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3,
                max_tokens=2000,
            )
        except ImportError:
            raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
    
    @staticmethod
    def _create_openai_llm(model: str):
        """Create OpenAI LLM.
        
        Args:
            model: OpenAI model name
            
        Returns:
            OpenAI LLM instance
        """
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=2000,
        )


class EmbeddingFactory:
    """Factory for creating embedding models."""
    
    @staticmethod
    def create_embeddings(model: Optional[str] = None):
        """Create an embedding model instance.
        
        Args:
            model: Embedding model name. Uses settings if None.
            
        Returns:
            Embeddings instance
        """
        model = model or settings.EMBEDDING_MODEL
        
        try:
            from langchain_openai import OpenAIEmbeddings
            
            return OpenAIEmbeddings(
                model=model,
                api_key=settings.OPENAI_API_KEY,
            )
        except ImportError:
            raise ImportError("langchain-openai not installed. Run: pip install langchain-openai")
