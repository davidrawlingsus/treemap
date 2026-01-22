"""
Unified LLM service for routing to OpenAI or Anthropic based on model selection.
Used for prompt engineering feature.
"""

import logging
from typing import Dict, Optional, Generator, Tuple
import httpx
import json

logger = logging.getLogger(__name__)


class LLMService:
    """Unified service for executing prompts with OpenAI or Anthropic"""
    
    # Map deprecated Anthropic model names to current ones
    ANTHROPIC_MODEL_MAPPING = {
        "claude-3-sonnet": "claude-3-opus-20240229",  # Short name fallback
    }
    
    # List of Anthropic models to try in order if the requested model is not found
    # These are commonly available models, including the newer format
    ANTHROPIC_FALLBACK_MODELS = [
        "claude-sonnet-4-5-20250929",  # Newer model format (from Anthropic sandbox)
        "claude-3-opus-20240229",
        "claude-3-5-sonnet-20241022", 
        "claude-3-haiku-20240307",
    ]
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
    
    def _is_anthropic_model(self, model: str) -> bool:
        """Check if model is an Anthropic model"""
        return model.lower().startswith("claude-")
    
    def _normalize_anthropic_model(self, model: str) -> str:
        """Normalize Anthropic model name, mapping deprecated names to current ones"""
        normalized = self.ANTHROPIC_MODEL_MAPPING.get(model, model)
        if normalized != model:
            logger.info(f"Mapping deprecated model '{model}' to '{normalized}'")
        return normalized
    
    def _is_openai_model(self, model: str) -> bool:
        """Check if model is an OpenAI model"""
        model_lower = model.lower()
        return model_lower.startswith("gpt-") or model_lower.startswith("o1-")
    
    def execute_prompt(
        self,
        system_message: str,
        user_message: str,
        model: str
    ) -> Dict:
        """
        Execute a prompt with system and user messages.
        Routes to appropriate provider based on model name.
        
        Args:
            system_message: The system prompt message
            user_message: The user input message
            model: LLM model identifier (e.g., "gpt-4o-mini" or "claude-3-5-sonnet-20241022")
        
        Returns:
            Dict with content, tokens_used, and model
        """
        logger.info(f"Routing prompt execution. Model: {model}, is_anthropic: {self._is_anthropic_model(model)}, is_openai: {self._is_openai_model(model)}")
        
        if self._is_anthropic_model(model):
            # Normalize model name (handle deprecated names)
            normalized_model = self._normalize_anthropic_model(model)
            logger.info(f"Routing to Anthropic API for model: {model} (normalized: {normalized_model})")
            return self._execute_anthropic(system_message, user_message, normalized_model)
        elif self._is_openai_model(model):
            logger.info(f"Routing to OpenAI API for model: {model}")
            return self._execute_openai(system_message, user_message, model)
        else:
            # Default to OpenAI if model pattern doesn't match
            logger.warning(f"Unknown model pattern '{model}', defaulting to OpenAI")
            return self._execute_openai(system_message, user_message, model)
    
    def execute_prompt_stream(
        self,
        system_message: str,
        user_message: str,
        model: str
    ) -> Generator[Tuple[str, Optional[Dict]], None, None]:
        """
        Execute a prompt with streaming support.
        Yields (chunk, metadata) tuples where chunk is content and metadata is None until final chunk.
        Final chunk will have metadata dict with tokens_used and model.
        
        Args:
            system_message: The system prompt message
            user_message: The user input message
            model: LLM model identifier
        
        Yields:
            Tuple of (content_chunk, metadata) where metadata is None for content chunks
            and a dict with tokens_used and model for the final chunk
        """
        logger.info(f"Streaming prompt execution. Model: {model}")
        
        if self._is_anthropic_model(model):
            normalized_model = self._normalize_anthropic_model(model)
            yield from self._execute_anthropic_stream(system_message, user_message, normalized_model)
        elif self._is_openai_model(model):
            yield from self._execute_openai_stream(system_message, user_message, model)
        else:
            logger.warning(f"Unknown model pattern '{model}', defaulting to OpenAI")
            yield from self._execute_openai_stream(system_message, user_message, model)
    
    def _execute_openai(
        self,
        system_message: str,
        user_message: str,
        model: str
    ) -> Dict:
        """Execute prompt using OpenAI API"""
        if not self.openai_api_key:
            raise RuntimeError("OpenAI service is not configured. Set OPENAI_API_KEY.")
        
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.openai_api_key,
                http_client=httpx.Client(timeout=60.0)
            )
            
            # Build request parameters
            request_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
            
            # Some models don't support certain parameters
            model_lower = model.lower()
            models_without_params = ['o1', 'o1-preview', 'o1-mini']
            models_without_temperature = ['gpt-4o', 'gpt-4o-mini'] + models_without_params
            models_without_max_tokens = ['gpt-4o', 'gpt-4o-mini'] + models_without_params
            
            # Add temperature for models that support it
            if not any(model_lower.startswith(m) for m in models_without_temperature):
                request_params["temperature"] = 0.7
            
            # Add max_tokens for models that support it
            if not any(model_lower.startswith(m) for m in models_without_max_tokens):
                request_params["max_tokens"] = 4000
            
            # Try the request, and if we get unsupported parameter errors, retry without them
            max_retries = 2
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(**request_params)
                    break  # Success, exit retry loop
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # Check for unsupported parameter errors
                    if 'unsupported_parameter' in error_str or 'unsupported_value' in error_str:
                        logger.warning(f"Model {model} returned unsupported parameter error (attempt {attempt + 1}): {e}")
                        
                        # Remove problematic parameters and retry
                        removed_any = False
                        if 'max_tokens' in error_str and 'max_tokens' in request_params:
                            logger.info(f"Removing max_tokens parameter for model {model}")
                            request_params.pop("max_tokens", None)
                            removed_any = True
                        if 'temperature' in error_str and 'temperature' in request_params:
                            logger.info(f"Removing temperature parameter for model {model}")
                            request_params.pop("temperature", None)
                            removed_any = True
                        
                        # If we couldn't identify the specific parameter but got an unsupported error,
                        # remove all optional parameters
                        if not removed_any:
                            logger.info(f"Removing all optional parameters for model {model} due to unsupported parameter error")
                            request_params.pop("max_tokens", None)
                            request_params.pop("temperature", None)
                        
                        # Continue to next iteration to retry (if not last attempt)
                        if attempt < max_retries - 1:
                            continue
                        else:
                            # Last attempt failed, raise the error
                            raise
                    else:
                        # Not an unsupported parameter error, don't retry
                        raise
            
            # If we exhausted retries, raise the last error
            if 'response' not in locals():
                raise last_error
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "model": model
            }
            
        except Exception as e:
            logger.error(f"Failed to execute prompt with OpenAI: {e}")
            raise RuntimeError(f"Failed to execute prompt: {str(e)}")
    
    def _execute_openai_stream(
        self,
        system_message: str,
        user_message: str,
        model: str
    ) -> Generator[Tuple[str, Optional[Dict]], None, None]:
        """Execute prompt using OpenAI API with streaming"""
        if not self.openai_api_key:
            raise RuntimeError("OpenAI service is not configured. Set OPENAI_API_KEY.")
        
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.openai_api_key,
                http_client=httpx.Client(timeout=180.0)  # Increased from 60s to 180s for long streams
            )
            
            # Build request parameters
            request_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "stream": True
            }
            
            # Some models don't support certain parameters
            model_lower = model.lower()
            models_without_params = ['o1', 'o1-preview', 'o1-mini']
            models_without_temperature = ['gpt-4o', 'gpt-4o-mini'] + models_without_params
            models_without_max_tokens = ['gpt-4o', 'gpt-4o-mini'] + models_without_params
            
            # Add temperature for models that support it
            if not any(model_lower.startswith(m) for m in models_without_temperature):
                request_params["temperature"] = 0.7
            
            # Add max_tokens for models that support it
            if not any(model_lower.startswith(m) for m in models_without_max_tokens):
                request_params["max_tokens"] = 4000
            
            # Try the request, and if we get unsupported parameter errors, retry without them
            max_retries = 2
            last_error = None
            stream = None
            
            for attempt in range(max_retries):
                try:
                    stream = client.chat.completions.create(**request_params)
                    break  # Success, exit retry loop
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # Check for unsupported parameter errors
                    if 'unsupported_parameter' in error_str or 'unsupported_value' in error_str:
                        logger.warning(f"Model {model} returned unsupported parameter error (attempt {attempt + 1}): {e}")
                        
                        # Remove problematic parameters and retry
                        removed_any = False
                        if 'max_tokens' in error_str and 'max_tokens' in request_params:
                            logger.info(f"Removing max_tokens parameter for model {model}")
                            request_params.pop("max_tokens", None)
                            removed_any = True
                        if 'temperature' in error_str and 'temperature' in request_params:
                            logger.info(f"Removing temperature parameter for model {model}")
                            request_params.pop("temperature", None)
                            removed_any = True
                        
                        # If we couldn't identify the specific parameter but got an unsupported error,
                        # remove all optional parameters
                        if not removed_any:
                            logger.info(f"Removing all optional parameters for model {model} due to unsupported parameter error")
                            request_params.pop("max_tokens", None)
                            request_params.pop("temperature", None)
                        
                        # Continue to next iteration to retry (if not last attempt)
                        if attempt < max_retries - 1:
                            continue
                        else:
                            # Last attempt failed, raise the error
                            raise
                    else:
                        # Not an unsupported parameter error, don't retry
                        raise
            
            # If we exhausted retries, raise the last error
            if stream is None:
                raise last_error
            
            # Stream chunks and accumulate content
            accumulated_content = ""
            tokens_used = 0
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content_chunk = delta.content
                        accumulated_content += content_chunk
                        # Yield content chunk with no metadata
                        yield (content_chunk, None)
                
                # Check for usage information in the chunk
                if hasattr(chunk, 'usage') and chunk.usage:
                    tokens_used = chunk.usage.total_tokens
            
            # If we didn't get tokens from chunks, we'll need to estimate or get from final response
            # For now, yield final metadata
            yield ("", {
                "tokens_used": tokens_used if tokens_used > 0 else None,  # May be None if not provided
                "model": model,
                "content": accumulated_content  # Include full content for storage
            })
            
        except Exception as e:
            logger.error(f"Failed to execute streaming prompt with OpenAI: {e}")
            raise RuntimeError(f"Failed to execute prompt: {str(e)}")
    
    def _execute_anthropic(
        self,
        system_message: str,
        user_message: str,
        model: str
    ) -> Dict:
        """Execute prompt using Anthropic API"""
        if not self.anthropic_api_key:
            raise RuntimeError("Anthropic service is not configured. Set ANTHROPIC_API_KEY.")
        
        try:
            from anthropic import Anthropic
            
            logger.info(f"Executing Anthropic prompt with model: {model}, system_message length: {len(system_message)}, user_message length: {len(user_message)}")
            
            # Validate API key format (Anthropic keys typically start with 'sk-')
            if not self.anthropic_api_key.startswith('sk-'):
                logger.warning(f"Anthropic API key doesn't start with 'sk-'. Key format: {self.anthropic_api_key[:10]}...")
            
            client = Anthropic(
                api_key=self.anthropic_api_key,
                http_client=httpx.Client(timeout=60.0)
            )
            
            # Anthropic API uses messages.create with system parameter
            # Anthropic requires non-empty user content - if user_message is empty, use a placeholder
            # Empty strings are not allowed in Anthropic messages
            # Ensure user_message is a string and not None
            if not user_message or not isinstance(user_message, str):
                user_content = "Please proceed."
            else:
                user_content = user_message.strip() if user_message.strip() else "Please proceed."
            
            # Validate model name format (should start with 'claude-')
            if not model.lower().startswith('claude-'):
                logger.warning(f"Model name '{model}' doesn't start with 'claude-'. This might cause an API error.")
            
            # Ensure system_message is a string and handle empty case
            # Anthropic allows empty system, but it's better to have content
            if not system_message or not isinstance(system_message, str):
                system_content = ""
            else:
                system_content = system_message.strip() if system_message.strip() else ""
            
            logger.debug(f"Anthropic API call parameters: model={model}, system_message length={len(system_content)}, user_content length={len(user_content)}")
            
            # Build messages list - Anthropic requires at least one user message with non-empty content
            # Anthropic API accepts content as either a string or a list of content blocks
            # Using the list format with type "text" for consistency with Anthropic's recommended format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_content
                        }
                    ]
                }
            ]
            
            # Build request parameters
            request_params = {
                "model": model,
                "max_tokens": 4096,
                "temperature": 1,  # Default temperature for Anthropic (can be adjusted)
                "messages": messages
            }
            
            # Only include system parameter if it's not empty
            # Some Anthropic models/versions might have issues with empty system messages
            if system_content:
                request_params["system"] = system_content
            
            # Try the requested model first, then fallback models if it's not found
            models_to_try = [model] + [m for m in self.ANTHROPIC_FALLBACK_MODELS if m != model]
            last_error = None
            response = None
            successful_model = None
            
            for model_to_try in models_to_try:
                try:
                    request_params["model"] = model_to_try
                    logger.info(f"Attempting Anthropic API call with model: {model_to_try}")
                    response = client.messages.create(**request_params)
                    # Success! Remember which model worked
                    successful_model = model_to_try
                    break
                except Exception as api_error:
                    error_str = str(api_error).lower()
                    # Check if it's a "not found" error
                    is_not_found = (
                        'not_found' in error_str or 
                        'not found' in error_str or
                        (hasattr(api_error, 'status_code') and api_error.status_code == 404)
                    )
                    
                    if is_not_found and model_to_try != models_to_try[-1]:
                        # Model not found, try next fallback
                        logger.warning(f"Model '{model_to_try}' not found, trying fallback models...")
                        last_error = api_error
                        continue
                    else:
                        # Different error or last model, raise it
                        logger.error(f"Anthropic API call failed with model {model_to_try}: {type(api_error).__name__}: {api_error}")
                        raise
            
            # If we exhausted all models without success
            if response is None:
                logger.error(f"All Anthropic model attempts failed. Last error: {last_error}")
                raise last_error if last_error else RuntimeError("Failed to execute prompt with any Anthropic model")
            
            # Use the successful model for the result
            model = successful_model
            
            logger.debug(f"Anthropic API call completed successfully")
            
            logger.debug(f"Anthropic response received: type={type(response)}, has_content={hasattr(response, 'content')}")
            
            # Extract content from Anthropic response
            # Anthropic returns content as a list of content blocks
            # Each block is a TextBlock object with type='text' and text attribute
            content = ""
            if hasattr(response, 'content') and response.content:
                logger.debug(f"Anthropic response.content type: {type(response.content)}, length: {len(response.content)}")
                for i, block in enumerate(response.content):
                    logger.debug(f"Content block {i}: type={type(block)}, dir={[attr for attr in dir(block) if not attr.startswith('_')]}")
                    # Anthropic SDK returns TextBlock objects with .text attribute
                    # Try multiple ways to access the text
                    block_text = None
                    if hasattr(block, 'text'):
                        block_text = block.text
                    elif hasattr(block, 'type') and hasattr(block, 'text'):
                        if block.type == 'text':
                            block_text = block.text
                    elif isinstance(block, dict):
                        block_text = block.get('text', '')
                    elif isinstance(block, str):
                        block_text = block
                    
                    if block_text:
                        content += str(block_text)
                    else:
                        # Log unexpected block structure for debugging
                        logger.warning(f"Could not extract text from content block {i}: {block}")
            
            if not content:
                logger.error(f"Anthropic response has no extractable content. Response type: {type(response)}, Response: {response}")
                # Try to get raw response for debugging
                try:
                    logger.error(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                except:
                    pass
            
            # Anthropic provides input_tokens and output_tokens separately
            # The usage object has input_tokens and output_tokens attributes
            if hasattr(response, 'usage') and response.usage:
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                tokens_used = input_tokens + output_tokens
                logger.info(f"Anthropic tokens used: {tokens_used} (input: {input_tokens}, output: {output_tokens})")
            else:
                tokens_used = 0
                logger.warning("Anthropic response has no usage information")
            
            result = {
                "content": content,
                "tokens_used": tokens_used,
                "model": model
            }
            
            logger.info(f"Anthropic prompt execution successful. Content length: {len(content)}")
            return result
            
        except Exception as e:
            # Extract detailed error information from Anthropic API errors
            error_details = str(e)
            error_type = type(e).__name__
            is_model_not_found = False
            
            # Try to extract additional details from Anthropic API errors
            if hasattr(e, 'status_code'):
                error_details += f" (Status: {e.status_code})"
            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                request_id = e.response.headers.get('x-anthropic-request-id') or e.response.headers.get('anthropic-request-id')
                if request_id:
                    error_details += f" (Request ID: {request_id})"
            if hasattr(e, 'body'):
                try:
                    import json
                    body = json.loads(e.body) if isinstance(e.body, str) else e.body
                    if isinstance(body, dict):
                        if 'error' in body:
                            error_info = body['error']
                            if isinstance(error_info, dict):
                                if 'message' in error_info:
                                    error_details = f"{error_info['message']}"
                                if 'type' in error_info:
                                    error_type_str = error_info['type']
                                    error_details += f" (Type: {error_type_str})"
                                    if error_type_str == 'not_found_error' or 'not_found' in error_details.lower():
                                        is_model_not_found = True
                except:
                    pass
            
            # Check if it's a model not found error
            if 'not_found' in error_details.lower() or 'not_found_error' in error_details.lower():
                is_model_not_found = True
            
            # Provide helpful suggestions for model not found errors
            if is_model_not_found:
                suggested_models = [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-haiku-20240307"
                ]
                error_details += f". Suggested alternative models: {', '.join(suggested_models)}"
            
            logger.error(f"Failed to execute prompt with Anthropic: {error_type}: {error_details}", exc_info=True)
            raise RuntimeError(f"Failed to execute prompt with Anthropic: {error_details}")
    
    def _execute_anthropic_stream(
        self,
        system_message: str,
        user_message: str,
        model: str
    ) -> Generator[Tuple[str, Optional[Dict]], None, None]:
        """Execute prompt using Anthropic API with streaming"""
        if not self.anthropic_api_key:
            raise RuntimeError("Anthropic service is not configured. Set ANTHROPIC_API_KEY.")
        
        try:
            from anthropic import Anthropic
            
            logger.info(f"Executing Anthropic streaming prompt with model: {model}")
            
            # Validate API key format
            if not self.anthropic_api_key.startswith('sk-'):
                logger.warning(f"Anthropic API key doesn't start with 'sk-'. Key format: {self.anthropic_api_key[:10]}...")
            
            client = Anthropic(
                api_key=self.anthropic_api_key,
                http_client=httpx.Client(timeout=180.0)  # Increased from 60s to 180s for long streams
            )
            
            # Handle empty user message
            if not user_message or not isinstance(user_message, str):
                user_content = "Please proceed."
            else:
                user_content = user_message.strip() if user_message.strip() else "Please proceed."
            
            # Handle empty system message
            if not system_message or not isinstance(system_message, str):
                system_content = ""
            else:
                system_content = system_message.strip() if system_message.strip() else "Please proceed."
            
            # Build messages list
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_content
                        }
                    ]
                }
            ]
            
            # Build request parameters
            request_params = {
                "model": model,
                "max_tokens": 64000,  # Maximum for Anthropic API
                "temperature": 1,
                "messages": messages,
                "stream": True
            }
            
            # Only include system parameter if it's not empty
            if system_content:
                request_params["system"] = system_content
            
            # Try the requested model first, then fallback models if it's not found
            models_to_try = [model] + [m for m in self.ANTHROPIC_FALLBACK_MODELS if m != model]
            last_error = None
            stream = None
            successful_model = None
            
            for model_to_try in models_to_try:
                try:
                    request_params["model"] = model_to_try
                    logger.info(f"Attempting Anthropic streaming API call with model: {model_to_try}")
                    stream = client.messages.create(**request_params)
                    successful_model = model_to_try
                    break
                except Exception as api_error:
                    error_str = str(api_error).lower()
                    is_not_found = (
                        'not_found' in error_str or 
                        'not found' in error_str or
                        (hasattr(api_error, 'status_code') and api_error.status_code == 404)
                    )
                    
                    if is_not_found and model_to_try != models_to_try[-1]:
                        logger.warning(f"Model '{model_to_try}' not found, trying fallback models...")
                        last_error = api_error
                        continue
                    else:
                        logger.error(f"Anthropic streaming API call failed with model {model_to_try}: {type(api_error).__name__}: {api_error}")
                        raise
            
            if stream is None:
                logger.error(f"All Anthropic model attempts failed. Last error: {last_error}")
                raise last_error if last_error else RuntimeError("Failed to execute prompt with any Anthropic model")
            
            # Stream chunks and accumulate
            accumulated_content = ""
            tokens_used = 0
            input_tokens = 0
            output_tokens = 0
            
            for event in stream:
                # Anthropic streaming events have different types
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text') and event.delta.text:
                        content_chunk = event.delta.text
                        accumulated_content += content_chunk
                        yield (content_chunk, None)
                elif event.type == "message_delta":
                    # This event contains usage information
                    if hasattr(event.usage, 'input_tokens'):
                        input_tokens = event.usage.input_tokens
                    if hasattr(event.usage, 'output_tokens'):
                        output_tokens = event.usage.output_tokens
                elif event.type == "message_stop":
                    # Final event - usage should be available
                    if hasattr(event, 'usage'):
                        if hasattr(event.usage, 'input_tokens'):
                            input_tokens = event.usage.input_tokens
                        if hasattr(event.usage, 'output_tokens'):
                            output_tokens = event.usage.output_tokens
            
            tokens_used = input_tokens + output_tokens
            
            # Yield final metadata
            yield ("", {
                "tokens_used": tokens_used if tokens_used > 0 else None,
                "model": successful_model or model,
                "content": accumulated_content
            })
            
        except Exception as e:
            logger.error(f"Failed to execute streaming prompt with Anthropic: {e}")
            raise RuntimeError(f"Failed to execute prompt with Anthropic: {str(e)}")

