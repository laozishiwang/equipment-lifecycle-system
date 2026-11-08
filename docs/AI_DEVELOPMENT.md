# AI 二次开发交接

此文档面向接手本仓库的开发者和 AI。先读本文件、根目录 README 及 `BACKLOG.md`（若仓库提供），以实际代码和运行环境为准。不要读取、打印或提交真实密码、令牌、机器人 Webhook、数据库备份、私钥或生产配置。

## 项目定位与边界

工厂设备管理：设备台账、二维码现场巡检与报修、维修接单及费用、试运行、关单、评价、保养、故障代码和通知。管理端登录使用；现场二维码 `/field/:id` 为免登录入口，工人每次填写姓名。匿名姓名是自填信息，不是身份认证；公网可访问时不能假定只有厂区用户能使用。设备二维码地址由服务端 `EMS_PUBLIC_BASE_URL` 决定，应按部署地址配置。

## 代码地图

- `frontend/`：Vue 3、Vite、Element Plus、Pinia。`src/views/equipment/` 是设备业务；`field/PublicField.vue` 是免登录现场页；`orders/` 是维修工单；`src/views/monitor/` 包含监控及通知配置；`src/router/` 和 `src/permission.js` 控制路由。
- `backend/`：若依多模块 Maven 项目。启动模块 `ruoyi-admin`，公共设施 `ruoyi-common`、认证与框架 `ruoyi-framework`、系统管理 `ruoyi-system`、任务调度 `ruoyi-quartz`。设备业务主要位于 `ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/`。先核对根 `pom.xml` 和配置再选择 Java 与依赖版本。
- `database/`：设备业务增量 SQL，另有 `backend/sql/` 中若依基础 SQL。必须按 Compose 文件中列出的顺序应用；同编号文件不是任选一份。`028` 包含 ALTER，不可盲目重复执行。MySQL 初始化目录仅对新数据卷首次启动生效，不会自动升级已有数据库。
- `deploy/`：Nginx、容器和运维材料及隔离测试。实际发布须使用与当前环境一致的配置，不能假定历史覆盖文件可在另一台机器直接使用。

## 业务调用路径

- 台账：`EquipmentController`；二维码现场：前端 `field/PublicField.vue` → `PublicFieldController`；巡检项目、模板、快照及照片：`InspectionController`、`InspectionTemplateController`、`InspectionPhotoController`。改动时保留模板校验、数值规则及异常照片要求。
- 报修：`PublicFieldController`、`WorkOrderController`，巡检也可以转工单。工单状态与操作请查 `WorkOrderController`，不要只根据页面按钮推断状态。费用分人工、配件和其他；试运行、关单及评价均与状态有关。
- 图片：`PrivatePhotoStorage`、`PhotoRollbackCleanup`、`StagePhotoCommitCleanup` 和清理任务处理私有文件与数据库记录；数据库备份不包含上传目录，恢复必须同时覆盖两者。不要直接公开私有图片目录。
- 通知：`DingTalkEvents` 在工单事务内登记事件，`DingTalkSender` 与 `MailSender` 消费各自队列；配置接口不应回显密钥。外部发送失败不应阻止工单保存。模拟服务测试，不要向真实群或邮箱发送测试，除非用户明确指定。
- 部门范围：`DepartmentScope*`、`OrderScopeSql`、`InspectionScopeSql`。该能力有独立实验开关，是否启用以运行配置为准；不能仅凭列表过滤认定权限隔离已完成。检查详情、附件、导出及变更入口。

## 本地开发与验证

1. 先核对 `git status`、实际运行的源码版本和现有未提交工作，不覆盖其他人改动；阅读与任务相关的代码、SQL 和配置。
2. 根据 README 启动隔离 MySQL 8、Redis 和后端；前端在 `frontend/` 下按 `package.json` 安装依赖并构建。Node 用于前端开发和构建，运行时可由 Nginx 提供静态文件。
3. 先复现具体问题，按实际改动执行最小必要测试。`deploy/` 中包含 HTTP 和脚本测试；先阅读每个脚本的目标地址、账号和写入操作，只能对隔离数据运行。
4. 改表时写新迁移，核对线上现状、备份与 MySQL DDL 特性，不随意编辑已执行的历史迁移。若新增初始化文件，同时更新 Compose 的初始化挂载，并验证空库初始化及现有库升级。
5. 改扫码页时同时验证手机窄屏、登录返回、匿名提交、照片上传等待和错误提示；真实微信/手机行为不能由模拟测试替代。新权限要检查后端，不仅隐藏前端按钮。
6. 发布前冻结源码和构建产物，确认数据库迁移、前后端镜像与配置对应，保留可用备份与回滚路径；记录具体验证范围。不要在生产创建测试工单或测试通知，除非得到明确授权。

## 建议交给 AI 的任务模板

```text
请先阅读 docs/AI_DEVELOPMENT.md 和 README，检查当前仓库及已有修改。
目标：[具体功能与用户场景]
约束：[PC/手机、权限、数据、部署要求]
验收：[给出可观察的结果]
请定位现有实现，复用项目约定，在隔离环境完成必要验证；不要泄露凭据，不要改动无关数据。汇报变更、测试、未完成事项及上线影响。
```
