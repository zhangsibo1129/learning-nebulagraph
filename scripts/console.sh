#!/usr/bin/env bash
# 进入 NebulaGraph Console 交互模式
cd "$(dirname "$0")/.."
docker compose exec console nebula-console -addr graphd -port 9669 -u root -p nebula