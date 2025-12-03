
# MinerU部署

用conda部署minerU，并以web-api形式启动

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

# seekDB/oceanbase 部署
混合检索数据库支持-seekdb-docker部署

```
sudo docker run -d \
  --name seekdb \
  -p 2893:2881 \
  -v /data2/jproject/seekdbData:/var/lib/oceanbase/store \
  oceanbase/seekdb:latest
```


# evidence-paper-QA-conda环境部署

部署后端的python-conda环境：

conda create -n quest python=3.10

conda activate quest
pip install dspy==3.0.3  -i https://pypi.org/simple/
pip install PyMySQL==1.1.1   -i https://pypi.org/simple/
pip install SQLAlchemy==2.0.40  -i https://pypi.org/simple/
pip install pyobvector==0.2.16  -i https://pypi.org/simple/
pip install mlflow  -i https://pypi.org/simple/
pip install notebook -i https://pypi.org/simple/
pip install debugpy -i https://pypi.org/simple/