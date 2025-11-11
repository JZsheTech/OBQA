前后端的health_check方法:

# 后端
cd <PROJECT_ROOT>
>  比如PROJECT_ROOT = /data2/jproject/OBQA
conda activate quest
<!-- uvicorn EviQAsys.backend.app.main:app --reload --port 9075 -->
uvicorn  app.main:app --app-dir EviQAsys/backend --reload   --port 9075

找另一个终端启用：
curl http://127.0.0.1:9075/healthz
来检查后端api的状态。

# 前端

cd  EviQAsys/frontend
npm run dev -- --host --port 5273
