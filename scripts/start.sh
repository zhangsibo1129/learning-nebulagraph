#!/usr/bin/env bash
# 启动 NebulaGraph 学习集群
set -e
cd "$(dirname "$0")/.."

echo "==> 启动 NebulaGraph 集群（首次启动需拉取镜像，请耐心等待）..."
docker compose up -d

echo "==> 等待服务就绪（约 60 秒）..."
sleep 60

echo "==> 检查服务状态..."
docker compose ps

echo ""
echo "==> 连接测试："
docker compose exec console nebula-console -addr graphd -port 9669 -u root -p nebula -e "SHOW HOSTS;"