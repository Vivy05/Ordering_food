from dotenv import load_dotenv
import os
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def call_llm(query:str,system_instruction:str):
    """
    通用LLM处理
    :param query: 问题
    :param system_instruction: 提示词
    :return:
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    api_base_url = os.getenv("DASHSCOPE_BASE_URL")
    llm_model = os.getenv("LLM_MODE")
    if not api_key or not api_base_url or not llm_model:
        raise ValueError("模型配置不全")

    llm = ChatOpenAI(
        model=llm_model,
        api_key=api_key,
        base_url=api_base_url,
    )

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system","{system_instruction}"),
            ("human","{query}")
        ]
    )

    chain = chat_prompt | llm

    response = chain.invoke({"system_instruction":system_instruction,"query":query})
    return response

if __name__ == "__main__":
    print(call_llm("给我讲一个笑话","你是一个小黑大师").content)