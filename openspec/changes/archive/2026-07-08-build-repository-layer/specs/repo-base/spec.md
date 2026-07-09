## ADDED Requirements

### Requirement: 泛型基类 BaseRepo
系统 SHALL 提供 `BaseRepo[T]` 泛型基类，封装通用 CRUD 操作。所有具体 Repository 必须继承此基类并指定 `model` 类变量。

基类 SHALL 通过构造函数接收 `sqlalchemy.orm.Session` 实例。

#### Scenario: 定义具体 Repository
- **WHEN** 开发者定义一个 `class FooRepo(BaseRepo[Foo]): model = Foo`
- **THEN** `FooRepo` 自动获得 `get`/`all`/`create`/`delete`/`count`/`exists`/`paginate` 全部方法

### Requirement: get — 按主键查询
系统 SHALL 提供 `get(id: int) -> T | None` 方法，通过主键查询单条记录。

#### Scenario: 查询存在的记录
- **WHEN** 调用 `repo.get(1)` 且对应记录存在
- **THEN** 返回模型实例

#### Scenario: 查询不存在的记录
- **WHEN** 调用 `repo.get(999)` 且对应记录不存在
- **THEN** 返回 `None`

### Requirement: all — 全表查询
系统 SHALL 提供 `all(*, offset=0, limit=100) -> list[T]` 方法，支持分页偏移的全表查询。

#### Scenario: 查询前 10 条
- **WHEN** 调用 `repo.all(limit=10)`
- **THEN** 返回最多 10 条记录

#### Scenario: 分页查询第二页
- **WHEN** 调用 `repo.all(offset=20, limit=20)`
- **THEN** 返回第 21-40 条记录

### Requirement: create — 创建记录
系统 SHALL 提供 `create(**kwargs) -> T` 方法，创建并 flush 新记录。

#### Scenario: 创建记录
- **WHEN** 调用 `repo.create(name="foo", value=42)`
- **THEN** 数据库插入新记录并 flush，返回模型实例（含自增主键）

### Requirement: delete — 删除记录
系统 SHALL 提供 `delete(id: int) -> bool` 方法，按主键删除记录。返回 `True` 表示删除成功，`False` 表示记录不存在。

#### Scenario: 删除存在的记录
- **WHEN** 调用 `repo.delete(1)` 且记录存在
- **THEN** 记录被删除并 flush，返回 `True`

#### Scenario: 删除不存在的记录
- **WHEN** 调用 `repo.delete(999)` 且记录不存在
- **THEN** 无操作，返回 `False`

### Requirement: count — 计数
系统 SHALL 提供 `count() -> int` 方法，返回表中记录总数。

#### Scenario: 统计记录数
- **WHEN** 调用 `repo.count()`
- **THEN** 返回表中总记录数

### Requirement: exists — 存在性检查
系统 SHALL 提供 `exists(id: int) -> bool` 方法，检查指定主键的记录是否存在。

#### Scenario: 记录存在
- **WHEN** 调用 `repo.exists(1)` 且记录存在
- **THEN** 返回 `True`

#### Scenario: 记录不存在
- **WHEN** 调用 `repo.exists(999)` 且记录不存在
- **THEN** 返回 `False`

### Requirement: paginate — 分页查询
系统 SHALL 提供 `paginate(page=1, page_size=20) -> tuple[list[T], int]` 方法，返回 `(当前页数据, 总记录数)`。

#### Scenario: 查询第一页
- **WHEN** 调用 `repo.paginate(page=1, page_size=10)` 且表中有 25 条记录
- **THEN** 返回 `(前10条, 25)`
