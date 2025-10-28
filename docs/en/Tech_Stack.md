# Tech Stack:

**Laptop:** Developer’s local machine
**Server:** Machine for deploying both frontend and backend applications

**Frontend:** ReAct (runs directly in the Chrome browser on the laptop)
**Backend:** Python FastAPI (runs in the server’s Conda environment `quest`)
**Database:** OceanBase (deployed in a Docker container on the server)
**Document Preprocessing:** MinerU (runs in a separate Conda environment `jzMinerUVllm` on the server, launches a local FastAPI service for access; independent of the main development environment)
**Agent Orchestration and LLM Invocation:** DsPy (runs in the server’s Conda environment `quest`)
