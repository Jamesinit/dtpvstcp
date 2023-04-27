# 仓库介绍

这个仓库是为了将两个独立的测试代码仓库整合到一起，方便集成到docker中去方便后续测试。

## docker 使用方法

1. 通过Dockerfile 重新build一个镜像或者下载`jake369/dtpvstcp:latest`
2. `docker run $(pwd)/log:/home/aitrans-server -p 5555:5555/udp jake369/dtpvstcp:latest /bin/bash`
3. 这里的端口根据需要变化；这里的映射路径是为了将生成的log的可以在宿主机上看到
