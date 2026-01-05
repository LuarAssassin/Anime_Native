"""
Redis Client Service
提供 Redis 连接和基本操作功能
"""
import os
import redis
from typing import Optional, Any, cast
from django.conf import settings


class RedisClient:
    """Redis 客户端封装类"""
    
    def __init__(self, db: int = 0):
        """
        初始化 Redis 客户端
        :param db: Redis 数据库编号，默认为 0
        """
        raw_host = getattr(settings, 'REDIS_HOST', os.getenv('REDIS_HOST', '127.0.0.1'))
        host = str(raw_host).replace('http://', '').replace('https://', '').rstrip('/')
        raw_port = getattr(settings, 'REDIS_PORT', os.getenv('REDIS_PORT', 6379))
        port = int(raw_port)
        password = getattr(settings, 'REDIS_PASSWORD', os.getenv('REDIS_PASSWORD', None))
        
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,  # 自动解码响应为字符串
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置键值对
        :param key: 键
        :param value: 值
        :param ex: 过期时间（秒），可选
        :return: 是否设置成功
        """
        try:
            return bool(self.client.set(key, value, ex=ex))
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """
        获取键对应的值
        :param key: 键
        :return: 值或 None
        """
        try:
            result = self.client.get(key)
            return cast(Optional[str], result)
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    def delete(self, *keys: str) -> int:
        """
        删除一个或多个键
        :param keys: 要删除的键
        :return: 删除的键数量
        """
        try:
            result = self.client.delete(*keys)
            return cast(int, result)
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        :param key: 键
        :return: 是否存在
        """
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        :param key: 键
        :param seconds: 过期时间（秒）
        :return: 是否设置成功
        """
        try:
            return bool(self.client.expire(key, seconds))
        except Exception as e:
            print(f"Redis EXPIRE error: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        :param key: 键
        :return: 剩余时间（秒），-1 表示永久，-2 表示不存在
        """
        try:
            result = self.client.ttl(key)
            return cast(int, result)
        except Exception as e:
            print(f"Redis TTL error: {e}")
            return -2
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        递增计数器
        :param key: 键
        :param amount: 递增量，默认 1
        :return: 递增后的值
        """
        try:
            result = self.client.incr(key, amount)
            return cast(int, result)
        except Exception as e:
            print(f"Redis INCR error: {e}")
            return None
    
    def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置哈希表字段
        :param name: 哈希表名
        :param key: 字段名
        :param value: 值
        :return: 添加的字段数
        """
        try:
            result = self.client.hset(name, key, value)
            return cast(int, result)
        except Exception as e:
            print(f"Redis HSET error: {e}")
            return 0
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希表字段值
        :param name: 哈希表名
        :param key: 字段名
        :return: 字段值或 None
        """
        try:
            result = self.client.hget(name, key)
            return cast(Optional[str], result)
        except Exception as e:
            print(f"Redis HGET error: {e}")
            return None
    
    def hgetall(self, name: str) -> dict:
        """
        获取哈希表所有字段和值
        :param name: 哈希表名
        :return: 字段值字典
        """
        try:
            result = self.client.hgetall(name)
            return cast(dict, result)
        except Exception as e:
            print(f"Redis HGETALL error: {e}")
            return {}
    
    def ping(self) -> bool:
        """
        测试连接
        :return: 连接是否正常
        """
        try:
            return bool(self.client.ping())
        except Exception as e:
            print(f"Redis PING error: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        try:
            self.client.close()
        except Exception as e:
            print(f"Redis CLOSE error: {e}")


# 单例模式 - 默认数据库连接
_default_client = None


def get_redis_client(db: int = 0) -> RedisClient:
    """
    获取 Redis 客户端实例
    :param db: 数据库编号
    :return: RedisClient 实例
    """
    global _default_client
    if db == 0:
        if _default_client is None:
            _default_client = RedisClient(db=0)
        return _default_client
    return RedisClient(db=db)
