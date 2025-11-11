
已知我写在这里的环境都已经部署好了。

# 用conda部署minerU，并以web-api形式启动

```
conda create -n jzMinerUVllm python=3.12

conda activate jzMinerUVllm

export UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/
(临时环境变量)

pip install --upgrade pip
pip install uv
或者
pip install uv -i https://pypi.org/simple/
uv pip install -U "mineru[core]"

# 首次运行时指定镜像站下载必要的模型文件，然后转换一个文件触发所有模型的下载
export MINERU_MODEL_SOURCE=modelscope
# <input_path>是pdf文件路径+文件名， <output_path>是转换后文件保存路径
mineru -p <input_path> -o <output_path>

比如:
export MINERU_MODEL_SOURCE=modelscope # 用之前一定要加上这一个，否则又会去hugging face下载模型。
mineru -p  "sample_data/pdf_doc/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples.pdf"  -o  "sample_data/test_convert"

建议把大文件用符号链接链接到本地的另一个数据盘中，方便迁移。
ln -s  /home/jzshe/project/bigData/sample_data     ./sample_data 
cd sample_data/minerUtemp

# 上述测试文件转换成功后在服务器上启动web服务，可以通过内网穿透等方法转发端口到公网或者用vscode把端口转发到本机。
# demo的测试和开发都在服务器端，所以不用转发
mineru-api --host 0.0.0.0 --port 18543
```

# 用docker部署oceanbase

OceanBase持久化存储路径：
/oceanBaseData

test 租户的passwd 
12345678

```
sudo docker pull oceanbase/oceanbase-ce:4.3.5-lts
国内如果不行可以尝试下面的镜像：
sudo docker pull quay.io/oceanbase/oceanbase-ce:4.3.5-lts


对于高性能服务器：具有大内存
```
sudo docker run -p 2881:2881 -v /oceanBaseData/ob:/root/ob   --name obstandalone  --restart=always  -e MODE=NORMAL -e OB_TENANT_PASSWORD=12345678 -e OB_MEMORY_LIMIT=32G -d  oceanbase/oceanbase-ce:4.3.5-lts
```

对于本地单机测试：只有32GB内存。
```
sudo    docker run   --name obstandalone -e MINI_MODE=1 -d    -e OB_MEMORY_LIMIT=8G -e OB_DATAFILE_SIZE=10G  --restart=always  -e OB_CLUSTER_NAME=ailab2024 -e OB_SERVER_IP=127.0.0.1 -p 127.0.0.1:2881:2881  -e OB_TENANT_PASSWORD=12345678     quay.io/oceanbase/oceanbase-ce:4.3.5-lts

```

> sudo docker logs obstandalone | tail -50
# 出现下面的输出表示启动成功,并且前面几行没有Error出现。
< boot success!

sudo docker exec -it obstandalone /bin/bash
obclient -h127.0.0.1 -P2881 -uroot@test -p
# 密码输入 12345678
```

进入了test租户的root用户界面
之后可以在数据库中创建用户和DataBase：

我们实际开发demo时,按下面的方法创建用户即可：
```
# Create a database user 'paperQA' and database schema 'default1' within the tenant. Replace <password> with the actual password of your choice.
CREATE USER paperQA IDENTIFIED BY '12345678';
CREATE DATABASE default1;
GRANT ALL ON default1.* TO paperQA;
```

为test租户的paperQA用户授予建表权限和远程访问权限
```

GRANT CREATE ON *.* TO paperQA;
-- 给 paperQA@test 授予数据库 obqademo 的常规数据操作权限
GRANT SELECT, INSERT, UPDATE, DELETE, DROP ON *.* TO paperQA;
GRANT ALL PRIVILEGES ON *.* TO paperQA WITH GRANT OPTION;
```

执行下面的命令开启向量数据库的检索功能
ALTER SYSTEM SET ob_vector_memory_limit_percentage = 30;

# 部署后端的python-conda环境：

conda create -n quest python=3.10


conda activate quest
pip install dspy==3.0.3  -i https://pypi.org/simple/
pip install PyMySQL==1.1.1   -i https://pypi.org/simple/
pip install SQLAlchemy==2.0.40  -i https://pypi.org/simple/
pip install pyobvector==0.2.16  -i https://pypi.org/simple/
pip install mlflow  -i https://pypi.org/simple/
pip install notebook -i https://pypi.org/simple/
pip install debugpy -i https://pypi.org/simple/