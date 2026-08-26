"""
02 · 数据写入与查询
演示：批量写入、图遍历（多跳）、聚合统计。

运行前提：集群已启动
运行方式：cd python && python 02-数据写入与查询.py
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


def format_path(value):
    """将路径 Value 格式化为 'vid -> vid -> vid' 字符串"""
    path = value.get_pVal()
    vids = [path.src.vid.get_sVal().decode('utf-8')]
    for step in path.steps:
        vids.append(step.dst.vid.get_sVal().decode('utf-8'))
    return ' -> '.join(vids)


def get_session():
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
        session.execute('CREATE SPACE IF NOT EXISTS py_demo (vid_type=FIXED_STRING(32));')
        wait_space_ready(session, 'py_demo')

        # 1. 定义 Schema
        session.execute('CREATE TAG IF NOT EXISTS person (name string, age int);')
        session.execute('CREATE EDGE IF NOT EXISTS friend (since date);')
        # MATCH 访问点属性需要索引（string 属性必须指定长度）
        session.execute(
            'CREATE TAG INDEX IF NOT EXISTS person_name_age_index ON person(name(32), age);'
        )
        # 等待 Schema 生效（CREATE TAG/EDGE 是异步的）
        wait_schema_ready(session, 'person')

        # 2. 批量写入（一条语句插入多个点/边）
        session.execute(
            'INSERT VERTEX person (name, age) VALUES '
            '"p1": ("Alice", 30), "p2": ("Bob", 25), "p3": ("Carol", 35), '
            '"p4": ("Dave", 28), "p5": ("Eve", 32);'
        )
        session.execute(
            'INSERT EDGE friend (since) VALUES '
            '"p1" -> "p2": (date("2019-06-01")), '
            '"p1" -> "p3": (date("2020-01-15")), '
            '"p2" -> "p3": (date("2021-03-20")), '
            '"p2" -> "p4": (date("2018-11-05")), '
            '"p3" -> "p5": (date("2022-07-30")), '
            '"p4" -> "p5": (date("2020-09-12"));'
        )

        # 3. 多跳查询：p1 的朋友的朋友（2 跳）
        result = session.execute(
            'MATCH (v:person)-[:friend*2]->(f:person) '
            'WHERE id(v) == "p1" RETURN DISTINCT f.person.name;'
        )
        if result.is_succeeded():
            print("== p1 的朋友的朋友（2 跳）==")
            for row in result.rows():
                print(f"  {value_to_py(row.values[0])}")
        else:
            print("2 跳查询失败:", result.error_msg())

        # 4. 路径查询
        result = session.execute(
            'MATCH p = (v:person)-[:friend*1..2]->(f:person) '
            'WHERE id(v) == "p1" RETURN p;'
        )
        if result.is_succeeded():
            print("== p1 出发的路径（1~2 跳）==")
            for row in result.rows():
                print(f"  {format_path(row.values[0])}")
        else:
            print("路径查询失败:", result.error_msg())

        # 5. 聚合统计
        result = session.execute('MATCH (v:person) RETURN count(*) AS cnt;')
        if result.is_succeeded():
            cnt = value_to_py(result.rows()[0].values[0])
            print(f"== person 总数: {cnt} ==")

        # 6. 按年龄排序
        result = session.execute(
            'MATCH (v:person) RETURN v.person.name AS name, v.person.age AS age ORDER BY age DESC;'
        )
        if result.is_succeeded():
            print("== 按年龄降序 ==")
            for row in result.rows():
                print(f"  {value_to_py(row.values[0])}: {value_to_py(row.values[1])}岁")

        # 7. 清理
        session.execute('DROP SPACE py_demo;')
        print("== 已清理演示空间 py_demo ==")

    finally:
        session.release()
        pool.close()


if __name__ == "__main__":
    main()