#!/usr/bin/env bash
# 停止 NebulaGraph 学习集群（保留数据）
cd "$(dirname "$0")/.."
docker compose down
echo "==> 集群已停止。如需彻底清理数据，请执行: rm -rf data logs"