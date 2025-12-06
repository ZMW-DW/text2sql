import aioredis


class Redis_Client:
    def __init__(self, redis_url="redis://localhost:12345"):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self.persistent = aioredis.from_url(redis_url, db=1, decode_responses=True)
    
    async def add(self, user_id: str, seasion_id: str, task_id: str, message: str):
        if message != "end":
            await self.redis.rpush(
                f"user_id:{user_id}:seasion_id:{seasion_id}:task_id:{task_id}", 
                message
            )

    async def get(self, user_id: str, seasion_id: str, task_id: str):
        """从 Redis 队列获取消息，阻塞式等待"""
        # 阻塞获取数据
        key = f"user_id:{user_id}:seasion_id:{seasion_id}:task_id:{task_id}"
        temp = await self.redis.blpop(key)
        if temp:
            message = temp[1]  # 获取消息部分
            # print(message)
            if message != "end":
                # 将消息持久化到另一个数据库
                await self.persistent.rpush(key, message)
                return message
            else:
                return None
            
    async def get_all(self, user_id: str, seasion_id: str, task_id: str):
        key = f"user_id:{user_id}:seasion_id:{seasion_id}:task_id:{task_id}"
        temp = await self.redis.lrange(key , 0, -1)
        return temp