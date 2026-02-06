import logging

from config.settings import azure_config
from langchain_openai import AzureChatOpenAI

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, use_coder: bool = False):
        if use_coder:
            self.llm = AzureChatOpenAI(
                azure_endpoint=azure_config.endpoint,
                api_key=azure_config.api_key,
                api_version=azure_config.api_version,
                deployment_name=azure_config.coder_model,
            )
        else:
            self.llm = AzureChatOpenAI(
                azure_endpoint=azure_config.endpoint,
                api_key=azure_config.api_key,
                api_version=azure_config.api_version,
                deployment_name=azure_config.analyst_model,
            )
