"""
01 · 连接与基础操作
演示：连接 NebulaGraph、创建图空间、定义 Schema、增删改查。

运行前提：集群已启动（./scripts/start.sh）
运行方式：cd python && python 01-连接与基础操作.py
"""
from nebula3.Config import Config
from nebula3.common.ttypes import Value
from nebula3.gclient.net import ConnectionPool

GRAPH_ADDR = "127.0.0.1"
GRAPH_PORT = 9669
USER = "root"
PASSWORD = "nebula"


def value_to_py(value):
    """将 nebula Value 转换为 Python 原生类型"""
    if value.field == Value.SVAL:
        return value.get_sVal().decode('utf-8')
    if value.field == Value.IVAL:
        return value.get_iVal()
    if value.field == Value.FVAL:
        return value.get_fVal()
    if value.field == Value.BVAL:
        return value.get_bVal()
    return value


def get_session():
    """创建连接池并返回一个会话"""
    config = Config()
    config.max_connection_pool_size = 10
    config.timeout = 10000

    pool = ConnectionPool()
    ok = pool.init([(GRAPH_ADDR, GRAPH_PORT)], config)
    if not ok:
        raise RuntimeError("连接 NebulaGraph 失败，请确认集群已启动")
    return pool, pool.get_session(USER, PASSWORD)


def wait_space_ready(session, space, retries=12, interval=5):
    """等待图空间就绪（CREATE SPACE 是异步的，需要等待传播）"""
    import time
    for _ in range(retries):
        result = session.execute(f'USE {space};')
        if result.is_succeeded():
            return
        time.sleep(interval)
    raise RuntimeError(f"图空间 {space} 在 {retries * interval} 秒内未就绪")


def wait_schema_ready(session, tag, retries=12, interval=5):
    """等待 Schema 在存储层生效（CREATE TAG/EDGE 是异步的，需要等待传播）"""
    import time
    for _ in range(retries):
        # 用 FETCH 探测：Tag 未传播到存储层时会报错，传播后返回空结果（无错误）
        result = session.execute(f'FETCH PROP ON {tag} "probe" YIELD {tag}.name;')
        if result.is_succeeded():
            return
        time.sleep(interval)
    raise RuntimeError(f"Tag {tag} 在 {retries * interval} 秒内未生效")


def main():
    pool, session = get_session()
    try:
        # 1. 创建图空间并等待就绪
        session.execute(
            'CREATE SPACE IF NOT EXISTS py_demo (vid_type=FIXED_STRING(32));'
        )
        wait_space_ready(session, 'py_demo')

        # 2. 定义 Schema
        session.execute(
            'CREATE TAG IF NOT EXISTS person (name string, age int);'
        )
        session.execute(
            'CREATE EDGE IF NOT EXISTS friend (since date);'
        )
        # MATCH 访问点属性需要索引（string 属性必须指定长度）
        session.execute(
            'CREATE TAG INDEX IF NOT EXISTS person_name_age_index ON person(name(32), age);'
        )
        # 等待 Schema 生效（CREATE TAG/EDGE 是异步的）
        wait_schema_ready(session, 'person')

        # 3. 插入数据
        session.execute(
            'INSERT VERTEX person (name, age) VALUES '
            '"p1": ("Alice", 30), "p2": ("Bob", 25), "p3": ("Carol", 35);'
        )
        session.execute(
            'INSERT EDGE friend (since) VALUES '
            '"p1" -> "p2": (date("2019-06-01")), '
            '"p1" -> "p3": (date("2020-01-15"));'
        )

        # 4. 查询：所有 person（注意：MATCH 访问点属性必须带 Tag 名）
        result = session.execute('MATCH (v:person) RETURN v.person.name, v.person.age;')
        if result.is_succeeded():
            print("== 所有 person ==")
            for row in result.rows():
                name = value_to_py(row.values[0])
                age = value_to_py(row.values[1])
                print(f"  {name}, {age}岁")
        else:
            print("查询失败:", result.error_msg())

        # 5. 查询：p1 的朋友（图遍历）
        result = session.execute(
            'MATCH (v:person)-[:friend]->(f:person) '
            'WHERE id(v) == "p1" RETURN f.person.name;'
        )
        if result.is_succeeded():
            print("== p1 的朋友 ==")
            for row in result.rows():
                print(f"  {value_to_py(row.values[0])}")

        # 6. 参数化查询：按年龄过滤（execute_py 自动转换 Python 类型）
        result = session.execute_py(
            'MATCH (v:person) WHERE v.person.age > $age RETURN v.person.name;',
            {'age': 28},
        )
        if result.is_succeeded():
            print("== 年龄大于 28 的人 ==")
            for row in result.rows():
                print(f"  {value_to_py(row.values[0])}")

        # 7. 更新
        session.execute('UPDATE VERTEX "p1" SET person.age = 31;')
        result = session.execute('FETCH PROP ON person "p1" YIELD person.name, person.age;')
        if result.is_succeeded():
            print("== 更新后 p1 ==")
            for row in result.rows():
                print(f"  {value_to_py(row.values[0])}: {value_to_py(row.values[1])}岁")

        # 8. 清理（删除空间）
        session.execute('DROP SPACE py_demo;')
        print("== 已清理演示空间 py_demo ==")

    finally:
        session.release()
        pool.close()


if __name__ == "__main__":
    main()