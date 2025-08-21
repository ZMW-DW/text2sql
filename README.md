### 端口8080为数据库查询端口
### 先创建docker container
```sh
  git clone "my-project"
  cd "my-project"
  docker compose up -d
  docker exec -it text2sql bash
```
### 进行下面操作即可
```sh
  cd src/xiyan_mcp_server
  python app.py
```
