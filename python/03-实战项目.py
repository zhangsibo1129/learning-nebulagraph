"""
03 · 实战项目：技术团队知识图谱（Python 版）
对应 nGQL/05-实战项目.ngql，演示如何用 Python 客户端完成：
  1. 建空间、建 Schema
  2. 批量导入数据
  3. 业务查询（同事、团队成员、技能匹配、多跳、聚合）
  4. 封装成可复用的数据访问层（DAO）

运行前提：集群已启动
运行方式：cd python && python 03-实战项目.py
"""
from nebula3.Config import Config
from nebula3.common.ttypes import Value
from nebula3.gclient.net import ConnectionPool

GRAPH_ADDR = "127.0.0.1"
GRAPH_PORT = 9669
USER = "root"
PASSWORD = "nebula"
SPACE = "team_graph"


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


class TeamGraphDAO:
    """技术团队知识图谱数据访问层"""

    def __init__(self, addr=GRAPH_ADDR, port=GRAPH_PORT, user=USER, password=PASSWORD):
        config = Config()
        config.max_connection_pool_size = 10
        config.timeout = 10000
        self._pool = ConnectionPool()
        ok = self._pool.init([(addr, port)], config)
        if not ok:
            raise RuntimeError("连接 NebulaGraph 失败，请确认集群已启动")
        self._session = self._pool.get_session(user, password)

    def close(self):
        self._session.release()
        self._pool.close()

    def _wait_space_ready(self, space, retries=12, interval=5):
        """等待图空间就绪（CREATE SPACE 是异步的，需要等待传播）"""
        import time
        for _ in range(retries):
            result = self._session.execute(f'USE {space};')
            if result.is_succeeded():
                return
            time.sleep(interval)
        raise RuntimeError(f"图空间 {space} 在 {retries * interval} 秒内未就绪")

    def _wait_schema_ready(self, tag, retries=12, interval=5):
        """等待 Schema 在存储层生效（CREATE TAG/EDGE 是异步的，需要等待传播）"""
        import time
        for _ in range(retries):
            # 用 FETCH 探测：Tag 未传播到存储层时会报错，传播后返回空结果（无错误）
            result = self._session.execute(f'FETCH PROP ON {tag} "probe" YIELD {tag}.name;')
            if result.is_succeeded():
                return
            time.sleep(interval)
        raise RuntimeError(f"Tag {tag} 在 {retries * interval} 秒内未生效")

    # ---------- 初始化 ----------
    def init_schema(self):
        """创建空间和 Schema（幂等）"""
        self._session.execute(
            f'CREATE SPACE IF NOT EXISTS {SPACE} (vid_type=FIXED_STRING(32));'
        )
        self._wait_space_ready(SPACE)
        self._session.execute(
            'CREATE TAG IF NOT EXISTS person (name string, age int, city string);'
        )
        self._session.execute(
            'CREATE TAG IF NOT EXISTS organization (name string, industry string);'
        )
        self._session.execute(
            'CREATE TAG IF NOT EXISTS project (name string, status string);'
        )
        self._session.execute('CREATE TAG IF NOT EXISTS skill (name string);')
        self._session.execute(
            'CREATE EDGE IF NOT EXISTS works_at (position string, start_year int);'
        )
        self._session.execute('CREATE EDGE IF NOT EXISTS works_on (role string);')
        self._session.execute('CREATE EDGE IF NOT EXISTS has_skill (level int);')
        self._session.execute('CREATE EDGE IF NOT EXISTS cooperates_with (since date);')
        self._session.execute('CREATE EDGE IF NOT EXISTS belongs_to ();')
        # MATCH 访问点属性需要索引（string 属性必须指定长度）
        self._session.execute(
            'CREATE TAG INDEX IF NOT EXISTS person_name_index ON person(name(32));'
        )
        self._session.execute(
            'CREATE TAG INDEX IF NOT EXISTS organization_name_index ON organization(name(32));'
        )
        self._session.execute(
            'CREATE TAG INDEX IF NOT EXISTS skill_name_index ON skill(name(32));'
        )
        self._session.execute(
            'CREATE TAG INDEX IF NOT EXISTS project_name_index ON project(name(32));'
        )
        # 等待 Schema 生效（CREATE TAG/EDGE 是异步的）
        self._wait_schema_ready('person')

    def load_data(self):
        """导入示例数据"""
        self._session.execute(
            'INSERT VERTEX organization (name, industry) VALUES '
            '"org1": ("NebulaTech", "Database"), '
            '"org2": ("GraphSoft", "Graph Computing"), '
            '"org3": ("DataWorks", "Big Data");'
        )
        self._session.execute(
            'INSERT VERTEX project (name, status) VALUES '
            '"proj1": ("NebulaGraph 3.8", "active"), '
            '"proj2": ("Graph Studio", "active"), '
            '"proj3": ("Data Pipeline", "finished"), '
            '"proj4": ("AI 推荐系统", "active");'
        )
        self._session.execute(
            'INSERT VERTEX skill (name) VALUES '
            '"sk1": ("Python"), "sk2": ("Go"), "sk3": ("Java"), '
            '"sk4": ("C++"), "sk5": ("SQL"), "sk6": ("机器学习");'
        )
        self._session.execute(
            'INSERT VERTEX person (name, age, city) VALUES '
            '"p1": ("Alice", 30, "北京"), "p2": ("Bob", 25, "上海"), '
            '"p3": ("Carol", 35, "北京"), "p4": ("Dave", 28, "深圳"), '
            '"p5": ("Eve", 32, "上海"), "p6": ("Frank", 29, "北京"), '
            '"p7": ("Grace", 27, "杭州");'
        )
        self._session.execute(
            'INSERT EDGE works_at (position, start_year) VALUES '
            '"p1" -> "org1": ("Engineer", 2019), '
            '"p2" -> "org1": ("Engineer", 2020), '
            '"p3" -> "org2": ("Manager", 2016), '
            '"p4" -> "org3": ("Analyst", 2021), '
            '"p5" -> "org2": ("Engineer", 2018), '
            '"p6" -> "org1": ("Architect", 2017), '
            '"p7" -> "org3": ("Engineer", 2022);'
        )
        self._session.execute(
            'INSERT EDGE works_on (role) VALUES '
            '"p1" -> "proj1": ("核心开发"), '
            '"p2" -> "proj1": ("测试"), '
            '"p6" -> "proj1": ("架构设计"), '
            '"p3" -> "proj2": ("产品经理"), '
            '"p5" -> "proj2": ("前端开发"), '
            '"p4" -> "proj3": ("数据开发"), '
            '"p7" -> "proj3": ("数据开发"), '
            '"p1" -> "proj4": ("算法工程师"), '
            '"p7" -> "proj4": ("算法工程师");'
        )
        self._session.execute(
            'INSERT EDGE has_skill (level) VALUES '
            '"p1" -> "sk1": (5), "p1" -> "sk6": (4), '
            '"p2" -> "sk2": (4), "p2" -> "sk5": (3), '
            '"p3" -> "sk3": (5), '
            '"p4" -> "sk5": (5), "p4" -> "sk1": (3), '
            '"p5" -> "sk1": (4), "p5" -> "sk3": (3), '
            '"p6" -> "sk4": (5), "p6" -> "sk2": (4), '
            '"p7" -> "sk1": (4), "p7" -> "sk6": (5);'
        )
        self._session.execute(
            'INSERT EDGE cooperates_with (since) VALUES '
            '"p1" -> "p2": (date("2020-03-01")), '
            '"p1" -> "p6": (date("2019-08-15")), '
            '"p2" -> "p6": (date("2020-05-20")), '
            '"p3" -> "p5": (date("2018-01-10")), '
            '"p4" -> "p7": (date("2022-02-14")), '
            '"p5" -> "p3": (date("2018-01-10")), '
            '"p6" -> "p1": (date("2019-08-15"));'
        )
        self._session.execute(
            'INSERT EDGE belongs_to () VALUES '
            '"proj1" -> "org1": (), "proj2" -> "org2": (), '
            '"proj3" -> "org3": (), "proj4" -> "org1": ();'
        )

    # ---------- 业务查询 ----------
    def _query_names(self, stmt, params=None):
        """执行查询并返回第一列字符串列表（execute_py 自动转换 Python 类型）"""
        if params:
            result = self._session.execute_py(stmt, params)
        else:
            result = self._session.execute(stmt)
        if not result.is_succeeded():
            raise RuntimeError(f"查询失败: {result.error_msg()}")
        return [value_to_py(row.values[0]) for row in result.rows()]

    def get_colleagues(self, person_vid):
        """某人的同事（同公司的人）"""
        return self._query_names(
            'MATCH (a:person)-[:works_at]->(o:organization)<-[:works_at]-(b:person) '
            'WHERE id(a) == $vid AND id(a) != id(b) '
            'RETURN b.person.name;',
            {'vid': person_vid},
        )

    def get_project_members(self, project_vid):
        """某项目的团队成员"""
        return self._query_names(
            'MATCH (p:project)<-[:works_on]-(a:person) '
            'WHERE id(p) == $vid RETURN a.person.name;',
            {'vid': project_vid},
        )

    def find_by_skill(self, skill_name):
        """按技能找人"""
        return self._query_names(
            'MATCH (a:person)-[:has_skill]->(s:skill) '
            'WHERE s.skill.name == $skill RETURN a.person.name;',
            {'skill': skill_name},
        )

    def find_by_skills(self, skill_names):
        """同时掌握多个技能的人"""
        clauses = ",\n".join(
            f'(a:person)-[:has_skill]->(s{i}:skill {{name: "{name}"}})'
            for i, name in enumerate(skill_names)
        )
        return self._query_names(f'MATCH {clauses} RETURN a.person.name;')

    def get_colleagues_of_colleagues(self, person_vid):
        """某人的同事的同事（2 跳）"""
        return self._query_names(
            'MATCH (a:person)-[:works_at]->(o:organization)<-[:works_at]-(b:person)'
            '-[:works_at]->(o2:organization)<-[:works_at]-(c:person) '
            'WHERE id(a) == $vid AND id(a) != id(c) AND id(b) != id(c) '
            'RETURN DISTINCT c.person.name;',
            {'vid': person_vid},
        )

    def get_company_headcount(self):
        """每家公司人数（聚合）"""
        result = self._session.execute(
            'MATCH (a:person)-[:works_at]->(o:organization) '
            'RETURN o.organization.name, count(*) AS cnt ORDER BY cnt DESC;'
        )
        if not result.is_succeeded():
            raise RuntimeError(f"查询失败: {result.error_msg()}")
        return [(value_to_py(row.values[0]), value_to_py(row.values[1])) for row in result.rows()]

    def find_in_company_with_skill(self, company_name, skill_name):
        """既在某公司工作又掌握某技能的人"""
        return self._query_names(
            'MATCH (a:person)-[:works_at]->(o:organization {name: $company}), '
            '(a:person)-[:has_skill]->(s:skill {name: $skill}) '
            'RETURN a.person.name;',
            {'company': company_name, 'skill': skill_name},
        )


def main():
    dao = TeamGraphDAO()
    try:
        print("== 初始化 Schema ==")
        dao.init_schema()
        print("== 导入数据 ==")
        dao.load_data()

        print("\n== 1. Alice 的同事 ==")
        for name in dao.get_colleagues("p1"):
            print(f"   {name}")

        print("\n== 2. NebulaGraph 3.8 项目成员 ==")
        for name in dao.get_project_members("proj1"):
            print(f"   {name}")

        print("\n== 3. 会 Python 的人 ==")
        for name in dao.find_by_skill("Python"):
            print(f"   {name}")

        print("\n== 4. 同时会 Python 和机器学习的人 ==")
        for name in dao.find_by_skills(["Python", "机器学习"]):
            print(f"   {name}")

        print("\n== 5. Alice 的同事的同事 ==")
        for name in dao.get_colleagues_of_colleagues("p1"):
            print(f"   {name}")

        print("\n== 6. 每家公司人数 ==")
        for company, cnt in dao.get_company_headcount():
            print(f"   {company}: {cnt}人")

        print("\n== 7. 在 NebulaTech 工作且会 Python 的人 ==")
        for name in dao.find_in_company_with_skill("NebulaTech", "Python"):
            print(f"   {name}")

    finally:
        dao.close()


if __name__ == "__main__":
    main()