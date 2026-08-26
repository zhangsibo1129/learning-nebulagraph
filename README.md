# NebulaGraph 从 0 到实战学习项目

> 目标：从零学会 NebulaGraph 的**部署**与**使用**，能够在实际项目中落地。
> 技术栈：Docker Compose 部署 + nGQL + Python 客户端（nebula3-python）

## 为什么学 NebulaGraph？

NebulaGraph 是一款开源的**分布式图数据库**，擅长处理海量点、边及其多跳关系查询。
相比关系型数据库（如 PostgreSQL）和知识图谱标准（如 SPARQL），它在以下场景有明显优势：

- **多跳关系查询**：如"朋友的朋友"、"A 到 B 的最短路径"，SQL 需要多次 JOIN，图数据库一次遍历即可
- **本体/知识图谱存储**：对象（Tag）、关系（Edge）、属性天然对应图模型
- **海量数据扩展**：存算分离架构，支持水平扩展

## 学习路线

| 阶段 | 内容 | 对应文件 |
|------|------|----------|
| 0. 准备 | 创建图空间（执行后等待约 20 秒） | [nGQL/00-创建空间.ngql](nGQL/00-创建空间.ngql) |
| 1. 部署 | 理解架构（metad/storaged/graphd），Docker Compose 启动集群 | [docs/01-架构与部署.md](docs/01-架构与部署.md) |
| 2. nGQL 基础 | 图空间、Tag/Edge 定义、增删改查 | [docs/02-nGQL基础.md](docs/02-nGQL基础.md) + [nGQL/](nGQL/) |
| 3. 数据建模 | 图建模原则、本体场景建模 | [docs/03-数据建模.md](docs/03-数据建模.md) |
| 4. 索引与优化 | 索引类型、查询计划分析 | [docs/04-索引与查询优化.md](docs/04-索引与查询优化.md) |
| 5. Python 客户端 | nebula3-python 连接与操作 | [docs/05-Python客户端.md](docs/05-Python客户端.md) + [python/](python/) |
| 6. 实战项目 | 技术团队知识图谱完整案例 | [nGQL/05-实战项目.ngql](nGQL/05-实战项目.ngql) + [python/03-实战项目.py](python/03-实战项目.py) |

## 快速开始

```bash
# 1. 启动集群（首次需拉取镜像，约几分钟）
./scripts/start.sh

# 2. 进入 Console 交互模式
./scripts/console.sh

# 3. 首次使用：创建图空间，然后等待约 20 秒（空间初始化）
#    在 Console 中执行 00-创建空间.ngql 的内容，或：
docker compose exec console nebula-console -addr graphd -port 9669 -u root -p nebula -f /tmp/ngql/00-创建空间.ngql

# 4. 依次执行练习脚本（01 执行后也需等待约 20 秒，让索引生效）
```

> **重要**：NebulaGraph 的图空间、Schema、索引创建都是**异步**的，
> 创建后需要等待约 20 秒（2 个心跳周期）才能使用。脚本都是幂等的（IF NOT EXISTS），
> 如果遇到 `SpaceNotFound` / `Index not found` 等错误，等待后重新执行即可。

连接信息：

| 项 | 值 |
|----|----|
| 地址 | 127.0.0.1:9669 |
| 用户名 | root |
| 密码 | nebula |

## 目录结构

```
learning-nebulagraph/
├── docker-compose.yml      # 集群部署配置（含详细注释）
├── docs/                   # 学习文档（按阶段组织）
├── nGQL/                   # nGQL 练习脚本（可直接在 Console 执行）
├── python/                 # Python 客户端示例
├── scripts/                # 辅助脚本（启动/停止/连接）
├── data/                   # 集群数据（自动生成，勿手动修改）
└── logs/                   # 集群日志（自动生成）
```

## 常用命令速查

```bash
./scripts/start.sh     # 启动集群
./scripts/stop.sh      # 停止集群（保留数据）
./scripts/console.sh   # 进入 Console
docker compose ps      # 查看服务状态
docker compose logs -f graphd   # 查看 graphd 日志
```

## 术语对照（结合你的本体项目）

| NebulaGraph 术语 | 本体/OWL 概念 | 说明 |
|------------------|---------------|------|
| Tag（点类型） | 对象（Object/Class） | 定义一类点的属性结构 |
| Edge Type（边类型） | 关系（Relation/Object Property） | 定义点与点之间的有向关系 |
| 属性（Property） | 属性（Data Property） | 点或边上的字段 |
| VID（点 ID） | 实例标识 | 点的唯一标识，类似主键 |
| 图空间（Space） | 命名空间 | 隔离不同数据集，类似数据库 |

## 官方资源

- 官方文档：<https://docs.nebula-graph.com.cn/>
- GitHub：<https://github.com/vesoft-inc/nebula>
- nGQL 手册：<https://docs.nebula-graph.com.cn/3.8.0/3.ngql-guide/>