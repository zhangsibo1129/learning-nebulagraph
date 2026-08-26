# 05 · Python 客户端

> 使用官方 Python 客户端 `nebula3-python` 连接和操作 NebulaGraph。

## 1. 安装

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依赖：`nebula3-python>=3.8.0`

## 2. 连接池与 Session

nebula3-python 的核心概念：

| 概念 | 说明 |
|------|------|
| `ConnectionPool` | 连接池，管理到 graphd 的底层连接 |
| `Session` | 会话，从连接池获取，执行 nGQL 语句 |
| `ResultSet` | 查询结果集 |

```python
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

# 1. 配置连接池
config = Config()
config.max_connection_pool_size = 10
config.timeout = 10000  # 毫秒

# 2. 初始化连接池（可指定多个 graphd 地址做负载均衡）
pool = ConnectionPool()
ok = pool.init([('127.0.0.1', 9669)], config)
assert ok, "连接失败"

# 3. 获取会话
session = pool.get_session('root', 'nebula')

# 4. 执行语句
result = session.execute('SHOW SPACES;')

# 5. 释放会话（归还连接池）
session.release()
# 程序退出时关闭连接池
pool.close()
```

## 3. 读取查询结果

nebula3-python 3.8 中，查询结果的值是 thrift `Value` 对象，需要用 `get_sVal()` / `get_iVal()` 等方法读取。
建议封装一个转换函数：

```python
from nebula3.common.ttypes import Value

def value_to_py(value):
    """将 nebula Value 转换为 Python 原生类型"""
    if value.field == Value.SVAL:
        return value.get_sVal().decode('utf-8')  # 字符串是 bytes，需解码
    if value.field == Value.IVAL:
        return value.get_iVal()
    if value.field == Value.FVAL:
        return value.get_fVal()
    if value.field == Value.BVAL:
        return value.get_bVal()
    return value

result = session.execute('MATCH (v:person) RETURN v.person.name, v.person.age;')

# 判断是否成功
if result.is_succeeded():
    # 遍历行
    for row in result.rows():
        name = value_to_py(row.values[0])
        age = value_to_py(row.values[1])
        print(name, age)
else:
    print("错误:", result.error_msg())
```

> **注意**：与 Console 一致，MATCH 访问点属性必须带 Tag 名（`v.person.name`），
> 且需要先创建索引（string 属性索引必须指定长度，如 `name(32)`）。

## 4. 参数化查询

使用 `execute_py` 做参数化查询（自动转换 Python 类型，避免拼接字符串）：

```python
stmt = 'MATCH (v:person) WHERE v.person.age > $age RETURN v.person.name;'
result = session.execute_py(stmt, {'age': 28})
```

> 注意：`execute_parameter` 需要手动构造 thrift `Value` 对象，推荐使用 `execute_py`。

## 5. 事务与批量操作

NebulaGraph 支持多语句一次提交（用分号分隔），但**不支持跨语句事务**：

```python
# 一次执行多条语句（注意：不是原子事务）
stmt = """
INSERT VERTEX person (name, age) VALUES "p1": ("Alice", 30);
INSERT VERTEX person (name, age) VALUES "p2": ("Bob", 25);
"""
session.execute(stmt)
```

> 需要原子性时，建议在应用层实现补偿逻辑，或使用单条语句完成操作。

## 6. 完整示例

- [python/01-连接与基础操作.py](../python/01-连接与基础操作.py)：连接、建空间、建 Schema、增删改查
- [python/02-数据写入与查询.py](../python/02-数据写入与查询.py)：批量写入、图遍历查询
- [python/03-实战项目.py](../python/03-实战项目.py)：技术团队知识图谱完整案例

> 示例中的 `wait_space_ready` / `wait_schema_ready` 用于等待图空间和 Schema 异步传播生效，
> 这是 NebulaGraph 分布式架构的特性（创建后约 20 秒生效）。

## 7. 常见问题

| 问题 | 解决 |
|------|------|
| `Connection refused` | 确认集群已启动，graphd 端口 9669 已映射 |
| `Auth failed` | 确认用户名密码（默认 root/nebula） |
| `SpaceNotFound` / `Unknown tag` | 图空间/Schema 创建是异步的，等待约 20 秒后重试 |
| 字符串返回 `b'xxx'` | 用 `value.get_sVal().decode('utf-8')` 解码 |
| 中文乱码 | 确保文件编码为 UTF-8，连接参数无需特殊设置 |
| 连接池耗尽 | 增大 `max_connection_pool_size`，或及时 `session.release()` |

## 8. 下一步

运行 [python/03-实战项目.py](../python/03-实战项目.py)，完成整个学习闭环。