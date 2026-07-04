"""共享内核：web 进程与 worker 进程共同依赖的基础设施装配。

web（FastAPI lifespan）和 worker（独立进程入口）都需要构造相同的
``gateway_service`` / ``retrieval_service``。本模块把这段装配逻辑集中成
可复用工厂函数，避免两个进程各自复制粘贴——这是"共享内核 + 进程边界只切
角色职责"的体现：基础设施装配是共享内核，进程边界只切 web/worker 各自的角色。
"""
