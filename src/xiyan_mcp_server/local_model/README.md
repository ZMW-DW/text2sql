## Local Model Configuration
Note: the local model is slow (about 12 seconds per query on my macbook).
If you need a stable and fast service, we still recommend to use the modelscope version.

To run xiyan_mcp_server in local mode, you need 
1) a PC/Mac/Machine with at least 16GB RAM
2) 6GB disk space

The above setting is for model of size 3B. You can adjust the settings to run a 32B model on a server.

### Step 1: Install additional Python packages
```bash
pip install flask modelscope torch==2.2.2 accelerate>=0.26.0 numpy=2.2.3
```

### Step 2: (optional) manually download the model
We recommend [xiyansql-qwencoder-3b](https://www.modelscope.cn/models/XGenerationLab/XiYanSQL-QwenCoder-3B-2502/).
You can manually download the model by
```bash
modelscope download --model XGenerationLab/XiYanSQL-QwenCoder-3B-2502
```
It will take you 6GB disk space.

### Step 3: download the script and run server. 

Script is located at `src/xiyan_mcp_server/local_model/local_xiyan_server.py`

```bash
python local_xiyan_server.py
```
The server will be running on http://localhost:5090/

### Step 4: prepare config and run xiyan_mcp_server
the config.yml should be like:
```yml
model:
  name: "xiyansql-qwencoder-3b"
  key: "KEY"
  url: "http://127.0.0.1:5090"
```

Till now the local model is ready.