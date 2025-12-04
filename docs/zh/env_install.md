
# 项目整体部署

请先完成后续几个组件部署后再进行项目的整体部署
```
git clone https://github.com/JZsheTech/OBQA
cd <Project_Root>
前端启动方式：
cd  EviQAsys/frontend
npm run dev -- --host --port 5273

后端启动方式：
cd <Project_Root>
conda activate quest
uvicorn  app.main:app --app-dir EviQAsys/backend --reload   --port 9075

vscode PORTS端口映射服务器 5273端口到本地5273端口，9075端口转发到本地9075端口，用浏览器打开

前端也可以单独在本地电脑上部署并打开，从而省去对前端5273端口的转发。
```

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
uv pip install "mineru[core,vllm]"
(这里只所以要装vllm，不是要给minerU用，是后面给jinaembeddingv4用的)

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

后端minerU api以 "pipeline"模式调用时, 大概只占用 3GB显存(jzMinerUVllm/bin/python3       2526MiB |)

# seekDB/oceanbase 部署
混合检索数据库支持-seekdb-docker部署

```
sudo docker run -d \
  --name seekdb \
  -p 2893:2881 \
  -v /data2/jproject/seekdbData:/var/lib/oceanbase/store \
  oceanbase/seekdb:latest
```

# jina-embedding-v4 统一多模态嵌入模型部署

由于之前的uv pip install "mineru[core,vllm]" 已经在jzMinerUVllm conda环境中安装了vllm的环境，所以直接在新的tmux终端中复用它来启动 jina-embedding-v4 服务

```
#!/bin/bash
# ==========================================================
# Launch vLLM server for Jina Embeddings v4 (multi-modal)
# ==========================================================

conda activate  jzMinerUVllm
# 指定显卡 (此处使用 GPU 2)
export CUDA_VISIBLE_DEVICES=0,1

# 启动服务
vllm serve  jinaai/jina-embeddings-v4-vllm-retrieval \
    --served-model-name jinaembeddingv4 \
    --task embed \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.95 \
    --port 7701 \
    --limit-mm-per-prompt '{"image":1}' \
    --dtype float16 \
    --trust-remote-code
    # 如果你想启用自定义池化，可取消下行注释（但通常无显著影响）
    # --override-pooler-config '{"pooling_type": "LAST", "normalize": true}'

预计显存需求：
2张 24GB显存的显卡，比如 2张RTX 3090

如果本地部署显存不够，后续我们会提供一种api调用方式，使用下面api服务商提供的版本，但调用接口会有微调。
https://aihubmix.com/model/jina-embeddings-v4

具体接口区别见下面：
dependency/multiModalEmbedding

```



# seekdb-paper-QA-conda环境部署

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