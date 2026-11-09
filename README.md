# 设备管理系统

面向工厂现场的设备台账、巡检、维修和保养系统。管理人员使用电脑浏览器；工人用手机扫描设备二维码，填写姓名后无需登录即可巡检或报修。维修人员接单、到场、登记维修日期与人工费、配件费和其他费用，试运行通过后由管理人员关单；系统保留设备履历。支持工单照片、故障代码、维修评价，以及可配置的钉钉群和邮箱通知。

## 技术栈

- 前端：Vue 3、Vite、Element Plus、Vue Router、Pinia、Axios；Nginx 提供静态页面及 API 反向代理。
- 后端：Java 17、Spring Boot 4.1、Spring Security、MyBatis、RuoYi、Maven；MySQL 8 存储业务数据，Redis 保存登录会话和缓存。
- Node.js 用于前端构建；运行时由 Nginx 托管静态文件，不需要 Node 服务或 SQLite。

## 设计与使用思路

设备编号关联二维码，现场页以设备为入口。异常可转工单，工单依次经历报修、接单、到场、维修、试运行和关单，费用分别记入对应类别。照片保存于服务端文件目录，数据库保存引用；备份时必须同时保存数据库和照片。钉钉及邮件通知由数据库队列异步处理，通知失败不应阻断业务。桌面端使用账号权限，手机公开现场入口记录自填姓名。公开二维码链接可被转发，姓名不是身份认证；如需严格控制访问，应结合厂区网络或独立身份方案。

建议先建少量真实设备、维护巡检模板和故障代码，再打印二维码、配置负责人及通知，试跑报修到关单并验收照片和费用。部门数据范围属于实验功能，默认关闭，启用前需完成角色及部门归属验收。

## 目录与文档

- `frontend/`：Vue 前端，`.env.production` 设置生产 API 前缀。
- `backend/`：Maven 多模块后端，主模块 `ruoyi-admin`，系统初始化脚本在 `backend/sql/`。
- `database/`：按编号排序的业务初始化/迁移脚本；已有库不要重复执行非幂等脚本。
- `deploy/`：Nginx、容器、备份恢复及验收工具。
- [Linux 部署指南](docs/linux-deployment.md)：MySQL、Redis、systemd、Nginx、备份及恢复。
- [AI 二次开发指南](docs/AI_DEVELOPMENT.md)：代码定位及修改注意事项。

运行前须设置新的管理员密码与独立的数据库、Redis 和 token 密钥。按实际部署的备份路径、权限和服务配置进行恢复演练；请勿把生产密码、机器人 Webhook、私钥或备份提交到仓库。


## 界面截图
<img width="3164" height="3658" alt="长截图_20261110_075527" src="https://github.com/user-attachments/assets/1e98b30f-bc7a-4d73-aa87-46d2c6a880bf" />

<img width="3202" height="1282" alt="局部截取_20261110_075600" src="https://github.com/user-attachments/assets/6ae1c762-4b65-40fc-a3f7-2a8187515ed9" />

<img width="3202" height="1644" alt="局部截取_20261110_075619" src="https://github.com/user-attachments/assets/10add37e-d5fb-4013-a632-c6a74d6eda57" />

<img width="3202" height="1020" alt="局部截取_20261110_075640" src="https://github.com/user-attachments/assets/e17815e6-d352-473f-b01f-25920a794820" />


<img width="3200" height="1194" alt="局部截取_20261110_075649" src="https://github.com/user-attachments/assets/b187d79b-77da-409e-ac21-238c456491ac" />





