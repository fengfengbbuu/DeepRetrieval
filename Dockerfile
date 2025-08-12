# 指定基础镜像
FROM ubuntu:jammy-20240227

# 示例：更新软件包索引（若需要安装软件）
RUN apt update 

# 示例：安装必要工具（根据项目需求调整，比如安装 python3）
RUN apt install -y python=3.10

# 设置工作目录
WORKDIR /RL

# 定义容器启动时执行的命令
CMD /bin/bash
