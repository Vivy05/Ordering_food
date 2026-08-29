import os.path
from typing import Any, Dict
from langchain_core.tools import tool, ToolException
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from tools.llm_tool import call_llm
from tools.pinecone_tool import search_menu_items_with_ids
import re
from tools.amap_tool import check_delivery_range, PathModeInput


def load_prompt_template(prompt_file_name):
    try:
        """加载指定文件的提示词"""
        current_file_path = os.path.abspath(__file__)
        current_file_dir = os.path.dirname(current_file_path)
        project_dire = os.path.dirname( current_file_dir)

        #拼接提示词目录
        prompt_path = os.path.join(project_dire, "prompt",f"{prompt_file_name}.txt")
        with open(prompt_path,"r",encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"无法加载指定文件{prompt_file_name}的提示词内容")
        return "无法加载到指定的提示词内容，请根据用户的问题，直接提供帮助"


@tool
def general_inquiry(query: str) -> str:
    """
        常规问询工具

        处理用户的一般性问题，包括但不限于：
        - 餐厅介绍和服务信息
        - 营业时间和联系方式
        - 优惠活动和会员服务
        - 其他非菜品相关的咨询

        Args:
            query: 用户的问询内容
            context: 可选的上下文信息，用于提供更精准的回复

        Returns:
            str: 针对用户问询的智能回复

        Raises:
            ToolException: 当处理查询时发生错误
        """
    try:
        prompt_template = load_prompt_template("general_inquiry")

        #调用llm
        llm_response = call_llm(query=query,system_instruction=prompt_template)
        return llm_response.content
    except Exception as e:
        raise ToolException(f"常规问题失败：{e}")

@tool
def menu_inquiry(query: str) -> Dict[str, Any]:
    """
    智能菜品咨询工具

    专门处理与菜品相关的所有查询，包括：
    - 菜品介绍和详细信息
    - 价格和营养信息
    - 菜品推荐和搭配建议
    - 过敏原和饮食限制相关问题
    - 菜品可用性和特色介绍

    该工具会自动通过语义搜索找到最相关的菜品信息，然后基于这些信息回答用户问题。

    Args:
        query: 用户关于菜品的具体问题

    Returns:
        Dict[str, Any]: 包含推荐建议和菜品ID的字典
        {
            "recommendation": "基于菜品信息的推荐建议",
            "menu_ids": ["菜品ID1", "菜品ID2"]
        }

    Raises:
        ToolException: 当处理菜品查询时发生错误
    """
    prompt_template = load_prompt_template("menu_inquiry")

    similar_result = search_menu_items_with_ids(query)
    if similar_result and similar_result.get("content"):
         menu_contents_context = ["\n".join(f"-{item}") for item in similar_result["content"]]
         full_query = f"当前从向量数据库中检索到的菜品信息\n\n{menu_contents_context}\n当前用户问题:\n{query}\n\n,请基于以上的上下文信息来回答用户问题"
    else:
        full_query = f"暂无相关信息：\n\n当前用户问题：\n{query}\n\n,请基于一般的菜品知识信息，回答用户提出的问题"

    llm_response = call_llm(query=full_query,system_instruction=prompt_template)
    #获取菜品id,还没写完
    # get_re_ids = re.search(r"菜品ID(\d+)",llm_response)


    return {
        "recommendation": llm_response.content,
        "menu_ids": similar_result["ids"],
    }

@tool
def delivery_check_tool(address: str, travel_mode: PathModeInput) -> str:
    """
    配送范围检查工具

    检查指定地址是否在配送范围内，并提供距离信息。

    Args:
        address: 配送地址
        travel_mode: 距离计算方式 (1=步行距离, 2=骑行距离, 3=驾车距离)

    Returns:
        str: 配送检查结果的格式化信息

    Raises:
        ToolException: 当配送检查失败时
    """
    try:
        check_delivery_rage_result = check_delivery_range(address,travel_mode)

        if check_delivery_rage_result["status"] == "success":
            status_text = "✅ 可以配送" if check_delivery_rage_result["in_range"] else "❌ 超出配送范围"
            response = f"""
            配送信息查询结果：
        
            配送地址：{check_delivery_rage_result['formatted_address']}
            配送距离：{check_delivery_rage_result['distance']}公里 (骑电动车))
            配送状态：{status_text}
                        """.strip()
        else:
            response = f"❌ 配送查询失败：{check_delivery_rage_result['message']}"

        return response
    except Exception as e:
        raise ToolException(f"配送检查失败: {str(e)}")

if __name__ == "__main__":
    # print("常规工具的调用")
    # print(general_inquiry.invoke({"query":"请问你们餐厅的营业时间是什么时候"}))
    # print("菜品推送")
    # print(menu_inquiry.invoke({"query":"川菜有哪些"}))
    print("配送距离")
    print(delivery_check_tool.invoke({"address":"武汉市温都水城","travel_mode":'2'}))
