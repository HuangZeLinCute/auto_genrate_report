from data_loader.redis_loader import RedisLoader
import socket

def test_redis_connection():
    """测试Redis连接"""
    print("开始测试Redis连接...")
    
    # 首先测试网络连通性
    try:
        from config.redis_config import REDIS_HOST, REDIS_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((REDIS_HOST, REDIS_PORT))
        if result != 0:
            print(f"无法连接到 {REDIS_HOST}:{REDIS_PORT}")
            print("可能的原因：")
            print("1. Redis服务器未运行")
            print("2. IP地址或端口不正确")
            print("3. 防火墙阻止了连接")
            return
        print(f"网络连通性测试成功: {REDIS_HOST}:{REDIS_PORT} 可访问")
    except Exception as e:
        print(f"网络测试失败: {e}")
        return
    finally:
        sock.close()
    
    # 测试Redis连接
    try:
        loader = RedisLoader()
        print("Redis连接成功！")
        
        # 测试数据读取
        try:
            data = loader.get_all_data()
            print(f"成功读取数据，共有 {len(data)} 个键")
            print("数据类型分布：")
            type_count = {}
            for key, value in data.items():
                type_name = type(value).__name__
                type_count[type_name] = type_count.get(type_name, 0) + 1
            for type_name, count in type_count.items():
                print(f"- {type_name}: {count}个")
        except Exception as e:
            print(f"读取数据时出错: {e}")
    except Exception as e:
        print(f"Redis连接测试失败: {e}")

if __name__ == "__main__":
    test_redis_connection() 