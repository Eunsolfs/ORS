# ORS 数据库字段清单（建议版）

> 目标：字段能完整覆盖“交班纸表 + 卡片式浏览 + 导出打印 + 培训课程 + 账号权限”。
>
> 约定：
> - 全部表默认包含：`id`（bigint, PK）、`created_at`、`updated_at`
> - 需要保留历史归属：使用软禁用/软删除优先（Laravel `softDeletes`）
> - 金额类用 `decimal(10,2)`；年龄用 `tinyint unsigned`（或 `smallint unsigned`）

## 1. 用户与权限

## 0. 多科室（组织层）与三层角色模型（root / 科室管理员 / 科室成员）
> 你新增的需求是：未来可能多科室一起用，因此需要“系统 root 管理员 - 科室管理员 - 科室成员”三层。
>
> 建议做法：把“科室”作为一层组织实体（`departments`），用户通过“成员关系表”加入一个或多个科室，并在科室内拥有角色（管理员/成员）。
> - **root 管理员**：全局角色（不绑定科室），可管理所有科室与数据。
> - **科室管理员**：绑定某个科室，仅管理本 `department_id` 下的交班/课程/成员。
> - **科室成员**：绑定某个科室，仅查看/填报本 `department_id` 数据。

### 0.1 `departments`（科室）
- **name**: varchar(100) unique（科室名称）
- **code**: varchar(50) unique nullable（科室编码/简称，可用于登录名规则或导出）
- **is_active**: tinyint(1) default 1
- **created_by**: bigint FK -> users.id nullable（root 创建者）
- **deleted_at**: datetime nullable（可选：软删除）

索引建议
- unique(`name`)
- unique(`code`)

### 0.2 `department_members`（用户-科室关系与科室内角色）
> 作用：实现“一人多科室”（可选），并区分科室管理员/成员。

- **department_id**: bigint FK -> departments.id
- **user_id**: bigint FK -> users.id
- **role_in_department**: varchar(20)（`admin` / `member`）
- **is_active**: tinyint(1) default 1（离科/停用该科室权限）
- **joined_at**: datetime nullable
- **created_by**: bigint FK -> users.id nullable（由谁添加）

约束/索引建议
- unique(`department_id`, `user_id`)
- index(`user_id`)
- index(`department_id`)

### 1.1 `users`（Laravel 默认扩展）
- **id**: bigint PK
- **name**: varchar(100)（员工姓名/显示名）
- **username**: varchar(50) unique（建议：工号/拼音/自定义登录名）
- **password**: varchar(255)
- **phone**: varchar(30) nullable（可选）
- **email**: varchar(190) nullable unique（可选）
- **is_active**: tinyint(1) default 1（禁用账号用）
- **last_login_at**: datetime nullable（可选）
- **remember_token**: varchar(100) nullable（Laravel 默认）
- **deleted_at**: datetime nullable（可选：软删除；若你坚持“删除员工”就启用）

### 1.2 `roles` / `permissions` / 关联表（spatie/laravel-permission）
由包自动建表：
- `roles`, `permissions`, `model_has_roles`, `model_has_permissions`, `role_has_permissions`

## 2. 每日交班（纸表 + 卡片流）

### 2.1 `handover_sessions`（每日一场交班）
对应纸表顶部信息 + 底部勾选项（建议集中放这里，导出更方便）

- **department_id**: bigint FK -> departments.id（所属科室）
- **handover_date**: date unique（交班日期）
- **elective_count**: smallint unsigned nullable（择期：__台）
- **emergency_count**: smallint unsigned nullable（急诊：__台）
- **rescue_count**: smallint unsigned nullable（特殊情况/抢救：__台；若不是“台数”可改为 text）
- **notes**: text nullable（管理员备注）

纸表底部“勾选/检查项”（建议用布尔列，导出版式好控制）
- **specimen_handover_ok**: tinyint(1) default 0（标本交接）
- **laminar_flow_running_ok**: tinyint(1) default 0（层流运行）
- **bio_monitoring_ok**: tinyint(1) default 0（生物监测）
- **crash_cart_ok**: tinyint(1) default 0（急救车）
- **fire_safety_ok**: tinyint(1) default 0（消防安全）
- **key_management_ok**: tinyint(1) default 0（钥匙）
- **certs_in_place_ok**: tinyint(1) default 0（其它合格证放于占位点）
- **other_incidents**: text nullable（其它事件）

归属与审计（可选但很实用）
- **created_by**: bigint FK -> users.id nullable（创建/当班管理员）
- **locked_at**: datetime nullable（“交班已结束/归档”）

索引建议
- unique(`department_id`, `handover_date`)
- index(`department_id`)

### 2.2 `handover_items`（每台手术=一张交班卡片）
对应纸表表格主体每一行。

基础信息（来自图片表头）
- **handover_session_id**: bigint FK -> handover_sessions.id（所属日期）
- **department**: varchar(100) nullable（科室）
- **patient_name**: varchar(100) nullable（姓名）
- **age**: smallint unsigned nullable（年龄）
- **surgery_name**: varchar(200) nullable（手术名称）

交接/评估/准备（来自图片表头）
- **special_handover**: text nullable（特殊病情交接）
- **blood_transfusion_checks**: json nullable（输血前九项：是否已执行）
- **pressure_ulcer_assessment**: varchar(200) nullable（压疮评估单：是否已执行）
- **skin_condition**: varchar(200) nullable（皮肤情况：破损？完好？其他？）
- **preop_visit**: varchar(200) nullable（术前访视：是否已执行）
- **special_instruments**: text nullable（特殊器械准备：是否已执行+note text）
- **other_notes**: text nullable（其它：可空）

交班卡片排序与状态（强烈建议）
- **display_order**: int default 0（卡片顺序：手动拖拽/自动排序）
- **status**: varchar(20) default 'active'（active/void 等；可选）

填报归属
- **reported_by**: bigint FK -> users.id nullable（谁填报的）
- **reported_at**: datetime nullable
- **updated_by**: bigint FK -> users.id nullable（最后修改人）

索引建议
- index(`handover_session_id`)
- index(`reported_by`)

## 3. 培训课程（二维码直达）

### 3.1 `courses`
- **department_id**: bigint FK -> departments.id（所属科室；root 可跨科室查看）
- **title**: varchar(200)
- **slug**: varchar(220) unique nullable（可选：友好链接）
- **content_html**: longtext（富文本内容：文字+图片）
- **cover_image_path**: varchar(500) nullable
- **video_provider**: varchar(30) nullable（bilibili/tencent/youtube/other）
- **video_url**: varchar(500) nullable（视频 URL）
- **video_embed_html**: longtext nullable（若直接保存 iframe 嵌入代码）
- **status**: varchar(20) default 'published'（draft/published/archived）
- **created_by**: bigint FK -> users.id nullable
- **published_at**: datetime nullable

索引建议
- unique(`slug`)
- index(`status`)
- index(`department_id`)

### 3.2 `course_assets`（可选：课程多图/附件）
若后续需要“多张图、文件附件”更规范，可加此表：
- **course_id**: bigint FK
- **type**: varchar(20)（image/file）
- **path**: varchar(500)
- **caption**: varchar(200) nullable
- **display_order**: int default 0

## 4. 二维码与入口（可选抽象层）
如果你希望“每个二维码都有后台记录/可停用/可统计扫码次数”，加表：

### 4.1 `qr_links`（可选）
- **name**: varchar(100)（如：今日交班码、某课程码）
- **type**: varchar(30)（handover_today/handover_date/course）
- **target**: varchar(500)（目标路由或完整 URL）
- **is_active**: tinyint(1) default 1
- **created_by**: bigint FK nullable

否则也可以不建表，直接运行时生成二维码即可（更快）。

## 4.2 固定不变的“交班填报二维码”（推荐做法）
> 你的需求是“二维码固定，不需要每天换新”。实现方式是：**二维码永远指向同一个固定 URL**，页面内部按“服务器当天日期”自动打开当天交班。

- **固定入口 URL（建议）**：`/m/handover/today`
- **页面逻辑**：
  - 取服务器日期 `today`（注意时区，建议统一 `Asia/Shanghai`）
  - 查询 `handover_sessions`：`handover_date = today`
    - **不存在**：自动创建一条（或仅管理员可创建，成员端提示“今日交班未创建”）
  - 加载该 session 下的 `handover_items`（卡片流展示 + 填报入口）
- **补录/查看历史（不通过换二维码实现）**：
  - 管理员后台按日期创建/管理 `handover_sessions`
  - 移动端可提供“选择日期”（仅管理员或仅内页入口）：`/m/handover/{date}`

> 结论：二维码只印一次，贴墙/投屏即可；每天交班自动进入当天数据。

## 5. 与纸表图片字段的映射（按列对照）
> 纸表主体表头（你附件） → `handover_items` 字段建议：
- **科室** → `department`
- **姓名** → `patient_name`（若这里其实是“患者姓名”；若是“员工姓名”，请改字段含义）
- **年龄** → `age`
- **手术名称** → `surgery_name`
- **特殊病情交接** → `special_handover`
- **输血前九项** → `blood_transfusion_checks`（JSON 或拆列）
- **压疮评估单** → `pressure_ulcer_assessment`
- **皮肤情况** → `skin_condition`
- **术前访视** → `preop_visit`
- **特殊器械准备** → `special_instruments`
- **其它** → `other_notes`

> 纸表顶部（择期/急诊/抢救/日期） → `handover_sessions`
> 纸表底部勾选项 → `handover_sessions`

