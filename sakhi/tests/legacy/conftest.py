import sys
import types

# Stub openai to avoid import errors during tests when the real package isn't installed.
if "openai" not in sys.modules:
    stub = types.SimpleNamespace(
        AsyncOpenAI=object,
        AuthenticationError=Exception,
        OpenAIError=Exception,
        RateLimitError=Exception,
        APIConnectionError=Exception,
    )
    sys.modules["openai"] = stub
