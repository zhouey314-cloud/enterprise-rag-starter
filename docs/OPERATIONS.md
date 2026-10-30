# 本地检索服务：运行、备份与恢复

这套实现适合验证文档版本、访问过滤、引用和拒答的完整流程。可信操作员管理入库与身份；查询客户端只发送问题。输入使用自有或明确授权的材料。公开静态页面独立运行。

## 从一份资料到可核查回答

按 [fresh-environment quickstart](local-quickstart.md) 创建私有数据库、身份和合成 MD/PDF/DOCX。然后运行：

```sh
python local_service.py --db .rag-data/index.sqlite3 doctor
python local_service.py --db .rag-data/index.sqlite3 serve --port 8767
```

doctor 只读检查 SQLite quick_check、关键表/列、外键及权限，并返回记录数；不返回正文、身份 token 或密钥。数据库不存在时失败，不会悄悄新建。除显式 init/restore 外，CLI 不再因路径拼错创建空数据库。

## 在线备份与独立恢复

先由操作员创建私有目录（Unix `mkdir -m 700 backup`），然后：

```sh
python local_service.py --db .rag-data/index.sqlite3 backup --out backup/snapshot.sqlite3
python local_service.py --db .rag-data/restored.sqlite3 restore --from-backup backup/snapshot.sqlite3
python local_service.py --db .rag-data/restored.sqlite3 doctor
```

使用 SQLite backup API，包含 WAL 中已提交的数据。目标必须不存在；拒绝覆盖文件、符号链接或原数据库。复制后检查完整性，输出 SHA256 和记录数；失败删除本次不完整副本。输出文件权限为 0600。恢复到新路径后，由操作员停止旧服务，再选择新数据库启动；没有自动切换线上数据。

备份包含文档正文和身份摘要，恢复也保留身份撤销状态。它是私有数据，不应提交 Git、附在公开 issue 或加入作品展示包。校验和说明完整性，不是加密或第三方认证。

## 回答边界与本轮修复

本地检索也复用已有 phone/email 值检查：仅仅提及“电话号码会变”或“稍后公布邮箱”不够。没有真实号码/邮箱时保留检索线索并拒答；ISO 时间戳不会充当电话。电话格式仍为已有保守英文启发式，不是完整国际号码校验。没有把静态页的 hours 格式限制施加到本地既有自然时间表达上。

原 62 条候选及期望原样保留：机械必需集合 60/60，完整 60/62，两个语义改写漏检仍可见。新增电话/邮箱正负与时间戳回归，以及真实 WAL 备份/恢复/撤销/CLI 检查。所有新增资料为 synthetic_unverified；生成模型和企业业务质量仍需独立验收。

本轮测试：55 Python、36 Node；固定候选与原 excerpt 回归均通过各自机械门槛。具体运行输出保存在本轮交付目录和对应 CI。
