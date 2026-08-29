"""数据库查询功能"""
import mysql.connector
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
import os
from typing import Dict, List, Any

load_dotenv()
class DataBaseConnection:
    """数据库管理相关的操作"""
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST")
        self.port = os.getenv("MYSQL_PORT")
        self.user = os.getenv("MYSQL_USER_NAME")
        self.password = os.getenv("MYSQL_USER_PASSWORD")
        self.db_name = os.getenv("MYSQL_DB_NAME")
        print(f"host={self.host}, user={self.user}, db={self.db_name}, port={self.port}")
        self.connection = None
        self.cursor = None

    def initialize_connection(self):
        """初始化数据库连接对象和游标对象"""
        try:
            #初始化连接对象
            self.connection = mysql.connector.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                database=self.db_name,
                charset="utf8"
            )
            #初始化游标对象
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except mysql.connector.Error as err:
            logger.error(f"数据库连接初始化失败：{err}")
            return False

    def disconnect_connection(self):
        """关闭游标和连接"""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection and self.connection.is_connected():
                self.connection.close()
                self.connection = None
            logger.info(f"数据库关闭成功")
            return True
        except mysql.connector.Error as err:
            logger.error(f"数据库关闭失败：{err}")
            return False

    def __enter__(self):
        """
        上下文管理器对象入口
        返回值：一定是一个上下文管理对象，一般就是自己
        """
        if self.initialize_connection():
            logger.info("数据库连接成功")
            return self
        else:
            raise Exception

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理对象出口
        exc_type:出异常时，异常的类型
        exc_val:异常的具体说明
        exc_tb:哪里出来异常
        """
        self.disconnect_connection()
        if exc_type:
            logger.error(f"执行with代码是出现异常：{exc_type}")

        return False # False代表有问题不会处理，继续向上抛出问题，如果是True:则不会向上抛出


def get_all_menu_items()->str:
    """
    作用：查询menu_items中所有菜品信息，并对每一个菜品信息用\n连接，最终返回一个大字符串(向量化)
    :return: str
    """
    try:
        with DataBaseConnection() as db:
            query_sql = """
              SELECT 
                    id, dish_name, price, description, category, 
                    spice_level, flavor, main_ingredients, cooking_method, 
                    is_vegetarian, allergens, is_available
                FROM menu_items 
                WHERE is_available = 1
                ORDER BY category, dish_name
            """
            db.cursor.execute(query_sql)
            menu_items = db.cursor.fetchall()
            if not menu_items:
                logger.info("当前无可用菜品")
                return "当前无可用菜品"
            menu_strings = []
            spice_level_mapping = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}
            for menu_item in menu_items:
                spice_text = spice_level_mapping[menu_item.get("spice_level","暂无辣度级别")]
                vegetarian_text = "是" if menu_item.get("is_available") else '否'
                format_description=menu_item.get("description") if menu_item.get("description","").strip() else "暂无描述"
                main_ingredients_text = menu_item.get("main_ingredients") if menu_item.get("main_ingredients","").strip() else "暂无主要食材"
                allergens_text = menu_item.get("allergens") if menu_item.get("allergens","").strip() else "暂无过敏源"
                menu_string = f"菜品ID:{menu_item['id']}|菜品名称:{menu_item['dish_name']}|价格:¥{menu_item['price']:.2f}|菜品描述:{format_description}|分类:{menu_item['category']}|辣度:{spice_text}|口味:{menu_item['flavor']}|主要食材:{main_ingredients_text}|烹饪方法:{menu_item['cooking_method']}|素食:{vegetarian_text}|过敏原:{allergens_text}"
                menu_strings.append(menu_string)
            all_menu_info = "\n".join(menu_strings)
            logger.info(f"已成功查询到菜品信息，菜品数量: {len(menu_strings)}个")
            return all_menu_info
    except Exception as e:
        logger.error(f"查询所有菜品信息结果失败:{e}")
        return "查询菜品信息失败"

def get_menu_items()->List[Dict[str,Any]]:
    """
    前端菜品展示
    :return: 字典列表（菜品列表）
    """
    try:
        with DataBaseConnection() as db:
            query_sql = """
                        SELECT 
                            id, dish_name, price, description, category, 
                            spice_level, flavor, main_ingredients, cooking_method, 
                            is_vegetarian, allergens, is_available
                        FROM menu_items 
                        WHERE is_available = 1
                        ORDER BY category, dish_name
                        """
            db.cursor.execute(query_sql)
            menu_items_result = db.cursor.fetchall()
            if not menu_items_result:
                logger.error(f"查询菜品信息失败: 没有找到任何菜品信息")
                return []
                # 4. 格式化输出
            menu_items = []
            for item in menu_items_result:
                # 辣度等级转换
                spice_levels = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}
                spice_text = spice_levels.get(item['spice_level'], "未知")

                # 处理数据
                processed_item = {
                    "id": item['id'],
                    "dish_name": item['dish_name'],
                    "price": float(item['price']),
                    "formatted_price": f"¥{item['price']:.2f}",
                    "description": item['description'] or "暂无描述",
                    "category": item['category'],
                    "spice_level": item['spice_level'],
                    "spice_text": spice_text,
                    "flavor": item['flavor'] or "暂无口味",
                    "main_ingredients": item['main_ingredients'] or "暂无主要食材",
                    "cooking_method": item['cooking_method'] or "暂无烹饪方法",
                    "is_vegetarian": bool(item['is_vegetarian']),
                    "vegetarian_text": "是" if item['is_vegetarian'] else "否",
                    "allergens": item['allergens'] if item['allergens'] and item['allergens'].strip() else "暂无过敏原",
                    "is_available": bool(item['is_available'])
                }
                menu_items.append(processed_item)

            logger.info(f"已成功查询到菜品信息，菜品数量: {len(menu_items)}个,并结构化菜品信息")
            return menu_items
    except Exception as e:
        logger.error(f"查询菜品列表失败，原因：{e}")
        return []


def text_connection():
    with DataBaseConnection() as db:
        db.cursor.execute("select 1")
        test_res = db.cursor.fetchall() #获取sql语句的结果
        if test_res:
            print(f"测试成功，结果是：{test_res}")
        else:
            print("测试失败")

if __name__ == '__main__':
    print("测试所有菜品信息的字符串")
    print(get_menu_items())
