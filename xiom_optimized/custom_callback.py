from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List, Optional
from uuid import UUID
from typing import Any, Dict, List, Union
from langchain.schema import BaseMessage, LLMResult, AgentAction, AgentFinish
from dash import callback_context
from flask import request, make_response  # Import make_response



class CustomHandler(BaseCallbackHandler):
    """Custom callback handler for LangChain."""

    def __init__(self, app):
        """Initialize the handler."""
        self.parent_run_id: Optional[UUID] = None
        self.handlers = []  # Initialize handlers attribute
        self.app = app

    def on_agent_action(self, action, **kwargs: Any) -> Any:
        """Run on agent action."""
        if action.tool == "python_repl_ast":
            # Use the global callback_context directly
            if callback_context is not None:
                # Create a response object
                response = make_response()
                print(action.tool_input["query"])
                # Set the cookie
                response.set_cookie("response_code", action.tool_input["query"])
                return



    def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        """Run when LLM starts running."""
        

    def on_chat_model_start(
            self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any
    ) -> Any:
        """Run when Chat Model starts running."""
        

    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        """Run on new LLM token. Only available when streaming is enabled."""
        

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Run when LLM ends running."""
        

    def on_llm_error(
            self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when LLM errors."""
        

    def on_chain_start(
            self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> Any:
        """Run when chain starts running."""
        

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        """Run when chain ends running."""
        

    def on_chain_error(
            self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when chain errors."""
        

    def on_tool_start(
            self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Run when tool starts running."""
        

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        """Run when tool ends running."""
        

    def on_tool_error(
            self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when tool errors."""
        

    def on_text(self, text: str, **kwargs: Any) -> Any:
        """Run on arbitrary text."""
        

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """Run on agent end."""
        