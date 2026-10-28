# 抱布记

抱布记正在从记账和健身小程序演进为私人“时间长河”：尽量自动收集用户授权的生活素材，供本人浏览和偶遇。前端旧模块入口已移除；旧后端接口和历史数据仍保留。

当前处于原型阶段。小程序无真实回忆时标明虚构示例；高驰自动同步、微信身份和安卓相册尚未完成真实部署或端到端验证。安卓的目标范围为用户选定相册。项目部署前仍须完成迁移、备份恢复、回退、授权和设备验证。

高驰同步控制仅代表本地任务允许或暂停，不代表已绑定或授权。worker 现在默认要求已有来源控制记录；真实高驰授权、账号映射、控制记录的安全创建及生产迁移均尚未实现。

## 文档

- [项目交接](docs/时间长河/项目交接.md)
- [审查与开发导航](docs/时间长河/审查与开发导航.md)
- [开发记录](docs/时间长河/开发记录.md)

历史设计放在 `designs/`；旧记录是历史背景，不能代替当前代码和最新开发记录。

## 本地运行与测试

后端依赖在 `backend/requirements.txt`。应用导入及启动不自动创建或迁移数据库：对**新的、绝对路径**的 SQLite 文件，可使用 `python backend/init_empty_db.py --database /absolute/path/to/new.db` 创建空库；目标文件已存在时工具拒绝操作。已有数据库的升级必须另行设计并演练迁移，不应使用此命令。

在单独虚拟环境安装依赖后，设置 `DATABASE_URL`、`JWT_SECRET_KEY` 等必要环境变量，再从 `backend` 目录运行服务。测试使用虚构数据；pytest 测试夹具在导入应用前强制设置临时数据库与测试密钥，不能用来检验真实服务环境。

```bash
python -m pytest backend/tests -q
node tests/wechatApi.test.js
node tests/wechatIdentity.test.js
node tests/wechatFlow.test.js
node tests/wechatSettings.test.js
node tests/river.test.js
node tests/login.test.js
```

小程序使用微信开发者工具打开项目根目录。仓库中只有原生小程序代码，无 npm 构建要求；测试结果不代表真机或真实微信联调。

## 运维边界

旧 `make deploy`、`deploy/deploy.sh` 和 `deploy/install-service.sh` 已暂停，不能作为发布方案。`make backup` 使用 SQLite 备份 API 创建一致性快照；照片文件及异地备份不在该快照内。恢复、迁移和切换服务须在隔离环境验证，不要将工具通过当成上线许可。

用户级“清空全部数据”接口暂时停用，直到来源暂停与在途同步保护完成；删除单条回忆仍可用。旧直接导入接口已停用，新导入接口要求先预览再确认，仍会替换明确提供的列表，不等同灾难恢复或完整的合并导入；见[数据导入预览与确认](docs/时间长河/数据导入预览与确认.md)。

这是公开仓库。不要提交真实回忆、账号、令牌、私钥、私人服务器配置或用户的 `project.private.config.json` 本地修改。
