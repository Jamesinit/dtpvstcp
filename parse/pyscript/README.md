# 解析脚本说明

将测试DTP和TCP生成的数据进行解析

## 使用方法

1. 直接使用成品容器`jake369/dtpvstcp_parse:latest`
2. 在上级目录通过`docker build`构建镜像
3. 将log文件和aitrans文件放在同一个文件夹中，将其映射到容器中。`docker run -it --rm -v $(pwd)/log:/app/data jake369/dtpvstcp_parse:latest /bin/bash`
4. 进入容器中的pyscript文件中，执行`python parse.py`,即可看到输出结果