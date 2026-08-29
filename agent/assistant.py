from typing import Dict,Any
from tools.llm_tool import call_llm
import json
from agent.mcp import general_inquiry, menu_inquiry, delivery_check_tool

class SmartRestaurantAssistant:
    """小助手【agent】"""

    def __init__(self):
        self.tools = {
            "general_inquiry":general_inquiry,
            "menu_inquiry":menu_inquiry,
            "delivery_check_tool":delivery_check_tool,
        }
        self.instruction="""你是一个智能餐厅助手的意图分析器。
        请分析用户问题意图，并且选择最合适的工具来处理：

        工具说明：
        1. general_inquiry: 处理餐厅常规咨询（营业时间、地址、电话、优惠活动、预约等）
        2. menu_inquiry: 处理智能菜品推荐和咨询（推荐菜品、介绍菜品、询问菜品信息、点餐等）
        3. delivery_check_tool: 处理配送范围检查（查询某个地址是否在配送范围内、能否送达等）

        你必须严格按照以下JSON格式返回，不要包含任何其他文字：
        {
            "tool_name": "工具名称",
             "format_query": "处理后的用户问题"
        }

        正确示例：
        用户："你们几点营业？" -> {"tool_name": "general_inquiry", "format_query": "营业时间"}
        用户："推荐川菜系列的菜品" -> {"tool_name": "menu_inquiry", "format_query": "推荐川菜"}
        用户："能送到武汉大学吗？" -> {"tool_name": "delivery_check_tool", "format_query": "武汉大学"}

        重要规则：
        - 只返回纯JSON，不要有任何额外字符和解释
        - 确保JSON格式完全正确
        - tool_name必须是以下之一：general_inquiry, menu_inquiry, delivery_check_tool
        - format_query要简洁明了地概括用户问题

        记住：如果你错误的选择工具，系统将会出现崩溃。"""

    def _analyze_intention(self,suer_query:str)->Dict[str,Any]:
        """意图分析"""
        llm_response_str = call_llm(suer_query,self.instruction)

        #反序列化
        llm_response_dict = json.loads(llm_response_str.content)
        return llm_response_dict

    def execute_tool(self,tool_name:str,tool_param:str):
        """执行工具"""
        try:
            tool_obj = self.tools[tool_name]
            if tool_obj is None:
                raise ValueError(f"工具{tool_name}不可用")

            if tool_name == "general_inquiry":
                tool_result = tool_obj.invoke({"query":tool_param})
            elif tool_name == "menu_inquiry":
                tool_result = tool_obj.invoke({"query":tool_param})
            else:
                tool_result = tool_obj.invoke({"address":tool_param,"travel_mode":"2"})
            return tool_result
        except Exception as e:
            raise Exception(f"查询功能不可用：{e}")

    def chat(self,user_query:str):
        """和小助手聊天"""
        structured_tool = self._analyze_intention(user_query)
        tool_name = structured_tool["tool_name"]
        tool_param = structured_tool["format_query"]
        #工具调用
        tool_result = self.execute_tool(tool_name,tool_param)

        return tool_result

def chat_with_assistant(user_query:str):
    """和智能小助手对话"""
    try:
        assistant = SmartRestaurantAssistant()

        assistant_response = assistant.chat(user_query)
        print(f"小助手的回复：{assistant_response}")

        return assistant_response
    except Exception as e:
        raise Exception(f"服务内部出现故障，暂不可以{str(e)}")

if __name__=="__main__":
    print(chat_with_assistant("能不能配送到武汉市温都水城"))
