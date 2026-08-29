from typing import Dict, Any, Optional, Literal, Union
import requests
from requests import RequestException, JSONDecodeError
from urllib3 import Retry
from requests.adapters import HTTPAdapter
import logging
import json
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()
import os
from dataclasses import dataclass

PathModeInput=Literal['1','2','3'] #外部
PathModel = Literal["walking","electrobike","driving"] #内部

#路径转换器
class PathModeConverter:
    """路径转换器"""
    MOOE_MAPPING = {
        "1": "walking",
        "2": "electrobike",
        "3": "driving",
    }
    @classmethod
    def to_mode(cls,mode_input:Union[PathModeInput])->PathModel:
        """将输入的模式转换为内部使用的模式"""
        if mode_input in cls.MOOE_MAPPING:
            return cls.MOOE_MAPPING[mode_input]
        else:
            raise ValueError(f"不支持的路径模式{mode_input},支持的路径模式{list(cls.MOOE_MAPPING.keys())}")

@dataclass
class AmapConfig:
    AMAP_API_KEY:str = os.getenv("AMAP_API_KEY")
    MERCHANT_LONGITUDE:str = os.getenv("MERCHANT_LONGITUDE")
    MERCHANT_LATITUDE:str = os.getenv("MERCHANT_LATITUDE")
    DELIVERY_RADIUS:int = int(os.getenv("DELIVERY_RADIUS"))
    DEFAULT_PATH_MODE=os.getenv("DEFAULT_PATH_MODE")

    def __post_init__(self):
        """自动调用（需要dataclass装饰器）"""
        if self.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY不存在")

def creat_session_with_retries():
    """重试机制"""
    #创建session对象
    session = requests.Session()
    #定义重试规则
    retry_rule = Retry(
        total=3,#重试次数，不包括第一次发送
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],#在哪些情况下重试
    )
    #创建HttpAdapter(自定义http行为)
    adapter = HTTPAdapter(max_retries=retry_rule)

    #将适配器挂载到session中
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def safe_request(base_url:str, params:dict) -> Optional[Dict]:
    """发送HTTP请求或HTTPS请求"""
    session = creat_session_with_retries()
    #发送请求
    try:
        response = session.get(url=base_url, params=params)
        response.raise_for_status() #遇到400到600的状态码，都会抛出异常
        return response.json()#将网络传输的字节反序列化成字典对象
    except requests.exceptions.HTTPError as e:
        try:
            http_request_url = base_url.replace("https://", "http://")
            response = session.get(url=http_request_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求发送失败:{e}")
            raise RequestException("HTTP请求发送失败")
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTPS协议的请求发送失败，原因：{e}")
        raise RequestException("HTTPS协议的请求发送失败")
    except json.decoder.JSONDecodeError as e:
        logger.error(f"解析响应结果失败，原因：{e}")
        raise JSONDecodeError("反序列化失败")


def geocode_address(address: str) -> Dict[str, Any]:
    try:
        #构建请求的url
        request_url = "https://restapi.amap.com/v3/geocode/geo"
        #构建请求的参数
        parameters = {
            "address": address,
            "key": os.getenv("AMAP_API_KEY"),
        }
        #发送请求
        response = safe_request(request_url, parameters)
        #解析结果
        if response["status"] != "1":
            return {
                "success": False,
                "message": response["info"]
            }
        geocodes = response["geocodes"][0] #地址编码信息列表,response的具体结构看高德文档
        return {
            "formatted_address": geocodes["formatted_address"],
            "location": geocodes["location"],
            "success": True,
        }
    except Exception as e:
        logger.error(f"地理位置编码失败：{e}")
        raise e

config = AmapConfig()
def calculate_distance(origin_location:str, destination_location:str,path_mode_input:PathModeInput = "2") -> Dict[str, Any]:
    try:
        if config.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY不存在")
        inner_model = PathModeConverter.to_mode(path_mode_input)
        path_endpoint={
            "walking":"https://restapi.amap.com/v5/direction/walking",
            "electrobike": "https://restapi.amap.com/v5/direction/electrobike",
            "driving": "https://restapi.amap.com/v5/direction/driving",
        }
        params={
            "key": config.AMAP_API_KEY,
            "origin": origin_location,
            "destination": destination_location,
        }
        if inner_model == "driving":
            params["show_fields"] = "cost"
        response = safe_request(path_endpoint[inner_model], params)
        if response["status"] != "1":
            return {
                "success": False,
                "message": response["info"]
            }
        path = response["route"]["paths"][0]
        duration = path["duration"]  if inner_model == "electrobike" else path["cost"]["duration"]
        return {
            "distance": path["distance"],
            "duration": duration,
            "success": True,
        }
    except Exception as e:
        logger.error(f"调用高德地图进行路径规划失败：{e}")
        raise e

def check_delivery_range(address:str,path_mode_input:PathModeInput = None) -> Dict[str, Any]:
    """检查地址是否在配送范围内"""
    try:
        geocode_result = geocode_address(address)
        if not geocode_result["success"]:
            return {
                "status": "fail",
                "message": geocode_result["message"]
            }
        #起点坐标
        origin_location = f"{config.MERCHANT_LONGITUDE},{config.MERCHANT_LATITUDE}"
        calculate_distance_result = calculate_distance(origin_location,geocode_result["location"],path_mode_input=path_mode_input or config.DEFAULT_PATH_MODE)
        if not calculate_distance_result["success"]:
            return{
                "status": "fail",
                "message": calculate_distance_result["message"]
            }
        distance = int(calculate_distance_result["distance"])
        in_range = distance <= int(config.DELIVERY_RADIUS)
        return {
            "status": "success",
            "in_range": in_range,
            "distance": round(distance/1000,2),
            "duration": int(calculate_distance_result["duration"]),
            "formatted_address": geocode_result["formatted_address"],
            "message": (
                f"配送地址：{geocode_result["formatted_address"]}\n"
                f"配送距离：{distance/1000:.2f}公里\n"
                f"配送状态：{"在配送范围内" if in_range else "超出配送范围"}"
            )
        }
    except Exception as e:
        logger.error(f"配送服务查询失败：{e}")
        raise e

if __name__ == "__main__":
    # print(geocode_address("武汉大学"))
    # print(calculate_distance(origin_location="116.466485,39.995197",destination_location="116.46424,40.020642"))
    print(check_delivery_range("武汉市温都水城",'2'))