from tools.amap_tool import PathModeInput


def get_menu():
    """获取菜品区域数值的展示"""
    from tools.db_tool import get_menu_items
    return get_menu_items()

def check_delivery_range(address:str,path_model:PathModeInput):
    """获取配送范围的展示"""
    from tools.amap_tool import check_delivery_range
    return check_delivery_range(address,path_model)

def smart_chat(user_query:str):
    from agent.assistant import chat_with_assistant
    return chat_with_assistant(user_query)