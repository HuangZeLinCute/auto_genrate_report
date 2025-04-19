import redis
import json
from typing import Optional, Dict, Any
from config.redis_config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

class RedisLoader:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,  # 设置套接字超时
                socket_connect_timeout=5,  # 设置连接超时
                retry_on_timeout=True,  # 超时时重试
                max_connections=10  # 最大连接数
            )
            # 测试连接
            self.client.ping()
        except redis.ConnectionError as e:
            print(f"Redis连接错误: {e}")
            print(f"请检查以下配置:")
            print(f"- Redis服务器是否运行")
            print(f"- IP地址 {REDIS_HOST} 是否正确")
            print(f"- 端口 {REDIS_PORT} 是否正确")
            print(f"- 防火墙是否允许该连接")
            raise
        except redis.AuthenticationError:
            print("Redis认证失败，请检查密码设置")
            raise
        except Exception as e:
            print(f"Redis初始化错误: {e}")
            raise

    def get_all_data(self) -> Dict[str, Any]:
        """从Redis读取所有类型的数据"""
        try:
            keys = self.client.keys()
            data = {}
            for key in keys:
                try:
                    key_type = self.client.type(key)
                    if key_type == 'string':
                        value = self.client.get(key)
                        try:
                            data[key] = json.loads(value)
                        except json.JSONDecodeError:
                            data[key] = value
                    elif key_type == 'hash':
                        value = self.client.hgetall(key)
                        data[key] = value
                    elif key_type == 'list':
                        value = self.client.lrange(key, 0, -1)
                        data[key] = value
                    elif key_type == 'zset':
                        value = self.client.zrange(key, 0, -1, withscores=True)
                        data[key] = value
                    else:
                        print(f"暂不支持的类型: {key}，类型是：{key_type}")
                except redis.RedisError as e:
                    print(f"处理键 {key} 时出错: {e}")
                    continue
            return data
        except redis.RedisError as e:
            print(f"获取数据时出错: {e}")
            raise

