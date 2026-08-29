import os
from typing import List

from dotenv import load_dotenv

load_dotenv()
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import dashscope
from http import HTTPStatus


class PineconeVectorDB:
    """pinecone向量数据库操作"""

    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        self.pinecone_env = os.getenv("PINECONE_ENV")

        #索引的名字，嵌入模型的名字，嵌入的维度
        self.index_name = "menu-item-index"
        self.embedding_model = "text-embedding-v4"
        self.dimension=1536
        #配置pinecone的客户端对象以及索引对象
        self.pc=None
        self.index = None

    def initialize_connection(self):
        """初始化pinecone向量库的客户端对象和索引对象"""
        try:
            if not self.pinecone_api_key:
                logger.error("不存在pinecone的api_key")
                return False
            #初始化客户端对象
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            #初始化索引
            if not self.pc.has_index(self.index_name):
                self.pc.create_index(
                    name=self.index_name,
                    vector_type="dense",
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=os.getenv("PINECONE_ENV"),
                    )
                )
            #获取并赋值
            self.index=self.pc.Index(self.index_name)
            logger.info("初始化向量数据库客户端对象和索引对象成功")
            return True

        except Exception as e:
            logging.error(f"初始化向量数据库pinecone客户端以及索引对象失败：{e}")
            return False

    def clear_index_vectors(self):
        """清空指定索引下的向量数据(不删除索引)"""
        if not self.index and not self.initialize_connection():
            logger.error("索引不存在")
            return False

        #判断索引下是否有向量数据，如果有，就删除数据
        vector_status = self.index.describe_index_stats()
        count = vector_status["total_vector_count"]
        if count == 0:
            logger.info("该索引下没有数据")
            return True
        try:
            self.index.delete(delete_all=True)
            logger.info(f"成功删除{self.index_name}下的所有数据")
            return True
        except Exception as e:
            logger.error(f"删除{self.index_name}下的所有数据失败：{e}")
            return False

    def _embedding_content(self,content:str) -> List[float] or None:
        """
        对文本进行向量化
        args:content:要向量化的文本
        :return:文本的向量化的结果
        """
        #发请求
        try:
            if not self.dashscope_api_key:
                logger.error(f"dashscope_api_key不存在")
                return False
            resp = dashscope.TextEmbedding.call(
                api_key=self.dashscope_api_key,
                model=self.embedding_model,
                input = content,
                dimension=self.dimension,
            )
            #解析响应结果，提取要的值
            if resp.status_code == HTTPStatus.OK:
                logger.info(f"文本{content}向量化成功")
                return resp.get("output").get("embeddings")[0].get("embedding")
            else:
                logger.error("发送文本嵌入模型的请求处理失败")
                return None
        except Exception as e:
            logger.error(f"发送文本嵌入模型的请求处理失败,{e}")
            return None

    def _validation_datasource(self,content:str)->bool:
        """校验数据源"""
        if not content:
            logger.error("数据源不存在")
            return False
        #判断字符串是否能使用
        result_str = ("当前无可用菜品","查询菜品信息失败")

        return not content.startswith(result_str)

    def _split_content(self,content:str):
        #定义文本切分器
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=100,chunk_overlap=0,separators=["\n"],length_function=len)
            docs = text_splitter.create_documents([content])
            #处理docs文档列表
            clearn_docs = []
            for doc in docs:
                page_count = doc.page_content.strip()
                clearn_docs.append(page_count)
            logger.info("文本切分成功")
            return clearn_docs
        except Exception as e:
            logger.error(f"文本切分失败：{e}")
            return False


    def upsert_menu_data(self,menu_data:str = None, batch_size: int = 30, clearn = True):
        """将文本向量存储到pinecone向量库"""
        try:
            if not menu_data:
                from tools.db_tool import get_all_menu_items
                menu_item_str = get_all_menu_items()
                #校验数据源
                if clearn:
                    self.clear_index_vectors()

                if not self._validation_datasource(menu_item_str):
                    logger.error("校验数据源失败，不能进行向量化")
                    return False
                #对数据进行切分
                embedding_chunks=self._split_content(menu_item_str)
                if not embedding_chunks:
                    logger.error("切片失败，不进行向量化")
                    return False
                batch = []
                for id,chunk in enumerate(embedding_chunks,1):
                    #进行向量操作
                    vectors = self._embedding_content(chunk)
                    if not vectors or len(vectors)!=self.dimension:
                        logger.error('向量值不存在或者向量维度不匹配')
                        return False
                    if not self.index and not self.initialize_connection():
                        logger.error("索引不存在")
                        return False
                    menu_medata = {
                        "content": chunk,
                        "line_number": id,
                        "type":"menu_item"
                    }
                    #准备向量数据的唯一标识
                    unique_vector_id = str(id)

                    batch.append((unique_vector_id,vectors,menu_medata))
                    if len(batch)>=batch_size:
                        #将向量插入到向量库中
                        self.index.upsert(vectors=batch)
                        batch = []
                if batch:
                    self.index.upsert(vectors=batch)
                logger.info("向量成功存储到向量库中")
                return True
            else:
                logger.info("数据处理")
                logger.info("向量化文本数据")
                logger.info("向量化数据存储到向量数据库")
                return False
        except Exception as e:
            logger.error(f"同步数据到向量数据库失败：{e}")
            return False


    def search_similar_menu_item(self,query:str,top_k:int = 2):
        """相似性检索"""
        try:
            if not self.index and not self.initialize_connection():
                logger.error("索引不存在")
                return []
            query_vector = self._embedding_content(query)
            if not query_vector or len(query_vector)!=self.dimension:
                logger.error("向量值不存在或者向量维度不匹配")
                return []
            #执行语义搜索
            similar_result = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            #提取相似的文档
            matches_result = similar_result["matches"]
            if not matches_result:
                logger.error("暂无查询到相似文档")
                return []
            final_matches_result = []
            for item in matches_result:
                menu_item = {
                    "id":item["id"],
                    "score":item["score"],
                    "content":item["metadata"]["content"],
                    "line_number":item["metadata"]["line_number"],
                }
                final_matches_result.append(menu_item)
            logger.info(f"查询到相似的文档:{len(final_matches_result)}条")
            return final_matches_result
        except Exception as e:
            logger.error(f"相似性检索失败：{e}")
            return []

pinecone_db = PineconeVectorDB()
#数据同步
def pinecone_input(menv_data:str = None, batch_size:int = 30 ,clearn_content:bool = True):
    return pinecone_db.upsert_menu_data(menu_data=menv_data,batch_size=batch_size,clearn=clearn_content)

#相似的匹配
def search_menu_items(query:str,top_k:int = 2):
    match_result = pinecone_db.search_similar_menu_item(query=query, top_k=top_k)
    if not match_result:
        return []
    return [item.get("content") for item in match_result]

import re
def search_menu_items_with_ids(query:str,top_k:int = 2):
    match_result = pinecone_db.search_similar_menu_item(query=query, top_k=top_k)
    if not match_result:
        return {}
    ids = []
    for item in match_result:
        content = item["content"]
        re_match = re.search(f"菜品ID:(\d+)",content)
        id = re_match.group(1) if re_match else item["id"]
        ids.append(id)
    return {
        "content":[item["content"] for item in match_result],
        "ids":[id for id in ids],
        "score":[item["score"] for item in match_result]
    }

if __name__ == "__main__":

    # print("测试pinecone连接")
    # pinecone_db.initialize_connection()
    # print("上传菜品信息")
    # pinecone_db.upsert_menu_data(menu_data=None, batch_size=10)
    print("相似性检索")
    match_result = pinecone_db.search_similar_menu_item("请给推荐我川菜")
    for match in match_result:
        print(match)