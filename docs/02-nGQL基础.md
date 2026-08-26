# 02 · nGQL 基础

> 前置：集群已启动（见 [01-架构与部署.md](01-架构与部署.md)），并已进入 Console：
> `./scripts/console.sh`
>
> 本节的每条命令都可以在 [nGQL/01-空间与Schema.ngql](../nGQL/01-空间与Schema.ngql) 和
> [nGQL/02-数据写入.ngql](../nGQL/02-数据写入.ngql) 中找到，可直接执行。

## 1. 图空间（Space）

图空间是数据隔离单元，类似关系型数据库中的 database。所有操作都发生在某个 Space 内。

```sql
-- 创建图空间（VID 使用定长字符串，长度 32）
CREATE SPACE IF NOT EXISTS learning (vid_type=FIXED_STRING(32));

-- 查看所有图空间
SHOW SPACES;

-- 使用图空间（后续操作都在该空间内）
USE learning;

-- 查看当前空间
SHOW CURRENT SPACE;

-- 删除图空间（慎用，会删除所有数据）
-- DROP SPACE learning;
```

> **VID 类型**：`FIXED_STRING(n)` 适合业务 ID（如 UUID、名称）；`INT64` 适合数字 ID。
> VID 是点的唯一标识，创建后不可修改。

## 2. Schema：Tag 与 Edge Type

图模型由 **Tag（点类型）** 和 **Edge Type（边类型）** 构成，类似关系型数据库中的表。

### 2.1 创建 Tag（点类型）

```sql
-- 创建 person 标签，包含 name/age/email 三个属性
CREATE TAG IF NOT EXISTS person (
    name  string,
    age   int,
    email string
);

-- 查看所有 Tag
SHOW TAGS;

-- 查看 Tag 结构
DESC TAG person;
```

### 2.2 创建 Edge Type（边类型）

```sql
-- 创建 friend 边类型，表示"朋友"关系，带一个属性 since（认识时间）
CREATE EDGE IF NOT EXISTS friend (
    since date
);

-- 查看所有边类型
SHOW EDGES;

-- 查看边类型结构
DESC EDGE friend;
```

### 2.3 修改 Schema

```sql
-- 给 person 增加属性
ALTER TAG person ADD (gender string);

-- 删除属性
ALTER TAG person DROP (email);

-- 删除 Tag / Edge（慎用）
-- DROP TAG person;
-- DROP EDGE friend;
```

### 2.4 常用数据类型

| 类型 | 说明 | 示例 |
|------|------|------|
| bool | 布尔 | `true` / `false` |
| int / int64 | 整数 | `30` |
| float / double | 浮点数 | `3.14` |
| string | 字符串 | `"Alice"` |
| date | 日期 | `date("2020-01-01")` |
| datetime | 日期时间 | `datetime("2020-01-01 12:00:00")` |
| timestamp | 时间戳 | `timestamp()` |
| list | 列表 | `[1, 2, 3]` |
| set | 集合 | `{"a", "b"}` |
| map | 键值对 | `{"k": "v"}` |

## 3. 数据写入

### 3.1 插入点（INSERT VERTEX）

```sql
-- 插入一个 person 点，VID 为 "p1"
INSERT VERTEX person (name, age, email) VALUES "p1": ("Alice", 30, "alice@example.com");

-- 一次插入多个点
INSERT VERTEX person (name, age, email) VALUES
    "p2": ("Bob", 25, "bob@example.com"),
    "p3": ("Carol", 35, "carol@example.com");
```

### 3.2 插入边（INSERT EDGE）

```sql
-- 插入一条边：p1 -> p2 是朋友，2019 年认识
INSERT EDGE friend (since) VALUES "p1" -> "p2": (date("2019-06-01"));

-- 一次插入多条边
INSERT EDGE friend (since) VALUES
    "p1" -> "p3": (date("2020-01-15")),
    "p2" -> "p3": (date("2021-03-20"));
```

> **注意**：插入边时，两端的点必须已存在，否则报错。

## 4. 数据查询

### 4.1 按 VID 查询（FETCH）

> 注意：NebulaGraph 3.x 中 FETCH 必须带 `YIELD` 子句指定要返回的属性。

```sql
-- 查询单个点的属性
FETCH PROP ON person "p1" YIELD person.name, person.age, person.email;

-- 查询多个点
FETCH PROP ON person "p1", "p2" YIELD person.name, person.age;

-- 查询边的属性
FETCH PROP ON friend "p1" -> "p2" YIELD friend.since;
```

### 4.2 条件查询（LOOKUP）

```sql
-- 按属性条件查询（需要先建索引，见 04-索引与查询优化.md）
LOOKUP ON person WHERE person.age > 28 YIELD person.name, person.age;
```

### 4.3 图遍历查询（GO）

```sql
-- 从 p1 出发，沿 friend 边走 1 步，找到 p1 的朋友
GO FROM "p1" OVER friend YIELD friend._dst AS friend_id;

-- 走 1~2 步（朋友的朋友）
GO 1 TO 2 STEPS FROM "p1" OVER friend YIELD friend._dst AS friend_id;
```

### 4.4 模式匹配查询（MATCH，推荐）

MATCH 是 nGQL 中最常用的查询方式，语法类似 Cypher。

> **重要**：从 NebulaGraph 3.0 开始，MATCH 中访问**点属性**必须带 Tag 名，
> 即 `v.person.name` 而不是 `v.name`（否则返回 NULL）。边属性不受此限制。

```sql
-- 查询所有 person 点
MATCH (v:person) RETURN v LIMIT 10;

-- 查询指定属性（注意：必须带 Tag 名）
MATCH (v:person) RETURN v.person.name, v.person.age;

-- 带条件过滤
MATCH (v:person) WHERE v.person.age > 28 RETURN v.person.name, v.person.age;

-- 查询朋友关系（p1 的朋友）
MATCH (v:person)-[:friend]->(f:person) WHERE id(v) == "p1" RETURN f.person.name;

-- 查询朋友的朋友（2 跳）
MATCH (v:person)-[:friend*2]->(f:person) WHERE id(v) == "p1" RETURN DISTINCT f.person.name;

-- 查询路径
MATCH p = (v:person)-[:friend*1..2]->(f:person) WHERE id(v) == "p1" RETURN p;
```

> **MATCH vs GO**：MATCH 语法更简洁、可读性更好，是官方推荐方式；GO 性能更高但语法繁琐，适合复杂遍历场景。
> **注意**：MATCH 访问点属性需要索引（见 [04-索引与查询优化.md](04-索引与查询优化.md)），
> 本项目的练习脚本已在 01 中提前创建了基础索引。

## 5. 数据更新与删除

```sql
-- 更新点属性（UPDATE，不存在则报错）
UPDATE VERTEX "p1" SET person.age = 31;

-- UPSERT（存在则更新，不存在则插入）
UPSERT VERTEX "p1" SET person.age = 32;

-- 删除点（会级联删除关联的边）
DELETE VERTEX "p1";

-- 删除边
DELETE EDGE friend "p1" -> "p2";
```

## 6. 聚合与排序

```sql
-- 统计 person 数量
MATCH (v:person) RETURN count(*) AS cnt;

-- 按年龄排序（注意：ORDER BY 只能使用列别名）
MATCH (v:person) RETURN v.person.name AS name, v.person.age AS age ORDER BY age DESC;

-- 限制返回数量（MATCH 不支持 OFFSET 分页）
MATCH (v:person) RETURN v.person.name AS name, v.person.age AS age ORDER BY age DESC LIMIT 2;
```

## 7. 练习

按顺序执行以下脚本（首次使用先执行 00 创建空间，等待约 20 秒再继续）：

```bash
# 在 Console 中执行（./scripts/console.sh），或使用 -f 文件模式：
docker compose exec console nebula-console -addr graphd -port 9669 -u root -p nebula -f /tmp/ngql/01-空间与Schema.ngql
```

- [nGQL/00-创建空间.ngql](../nGQL/00-创建空间.ngql)：创建图空间（执行后等待约 20 秒）
- [nGQL/01-空间与Schema.ngql](../nGQL/01-空间与Schema.ngql)：定义 Schema 和基础索引（执行后等待约 20 秒）
- [nGQL/02-数据写入.ngql](../nGQL/02-数据写入.ngql)：插入数据并验证

**思考题：**
1. 为什么插入边之前必须保证两端点存在？
2. `FIXED_STRING(32)` 和 `INT64` 两种 VID 类型各适合什么场景？
3. MATCH 和 GO 的适用场景有什么区别？
4. 为什么 MATCH 访问点属性必须写 `v.person.name` 而不是 `v.name`？

## 8. 下一步

掌握基础增删改查后，进入 [03-数据建模.md](03-数据建模.md) 学习如何设计图模型。