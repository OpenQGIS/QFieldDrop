# QField LAN Drop 项目工程结构与资产四维归类文?(Project Structure Guide)

> **定位说明**：本文档针对当前工作区所有文件与衍生制品进行全量扫描与四维归类，明晰**开发代?*?*仓库推?*?*打包内容**?**[Releases] 制品**的边界，作为工程化分发与版本治理的唯一基准结构规范?

---

## 🧬 双轨独立版本演进架构 (Dual-Track Independent Versioning Architecture)

本项目在工程与发布架构层面确立并践行 **「双轨独立版本治理体系?*，彻底解耦桌面端与移动端的演进生命周期：

`plaintext
                    ┌────────────────────────────────────────────────────────?
                    ?    QField LAN Drop 全生命周期双轨版本治理架?        ?
                    └────────────────────────────────────────────────────────?
                                      ?
                 ┌────────────────────┴────────────────────?
                 ?                                        ?
   🖥?【Track A: 桌面?QGIS 插件?             📱 【Track B: 移动?QField 伴侣?
   ──────────────────────────────────         ──────────────────────────────────
   ?宿主环境: QGIS Desktop (PyQt5/PyQt6)       ?宿主环境: QField Mobile (QML/QtQuick)
   ?元数据源: ./metadata.txt                  ?元数据源: ./mobile/metadata.txt
   ?当前版本: v1.1.1                         ?当前版本: v1.0.1
   ?演进节拍: 敏捷高频（协议迭?异步重构?   ?演进节拍: 克制稳健（现场外业稳定性优先）
   ?官方门户: plugins.qgis.org               ?分发形式: QField 压缩包直?/ 沙盒解压
   ?制品产出: QFieldDrop_V-1.2.0-beta.zip          ?制品产出: QFieldDropMobile_V-1.0.4.zip
`

### 架构设计原则与治理约束：
1. **宿主环境与技术栈物理隔离**：桌面端基于 Python / QGIS C++ API 构建，承担重度网络监听、多网卡路由优选与异步多线程打包；移动端基?QML / JavaScript 运行于移动端受限沙盒，二者不存在物理二进制依赖?
2. **免除移动端无谓重复升?*：桌面端的性能调优、跨版本垫片升级或多线程重构（如本次 1.0.1 ?1.1.1 全异步多线程重构），**严禁无谓抬升手机端版本号**，避免迫使外业人员频繁重复扫码重装手机插件?
3. **构建流水线独立寻?*：构建脚?uild_clean_release.py 严格基于两份独立?metadata.txt 动态解析各自版本，分别构建、分别校验、分别归档?
4. **更新日志显式双轨拆分**：在 CHANGELOG.md 与元数据中，强制区隔 [桌面端] ?[移动端] 的变更明细?

---

## 🧭 一、四维核心概念与对比矩阵

?QGIS / QField 插件工程全生命周期中，资产依据使用场景与生命周期划分为四个维度：

| 资产维度 | 核心定义与受?| 物理路径 / 载体 | 包含原则与过滤机?|
| :--- | :--- | :--- | :--- |
| 🛠?**1. 开发代?(Dev Code)** | 面向核心开发者、测试套件与自动化构建工具；包含调试脚本、测试样本、中间矢量稿及本地运行时缓存 | 当前开发插件目录：<br>`.../profiles/ForTest/python/plugins/QFieldDrop/` | **仅本地保?*；严禁打入官方分发包；缓存类文件严禁推入 Git |
| 📦 **2. 仓库推?(Git Repo)** | 面向开源协作者、代码审?(PR) ?GitHub CI/CD 流水线；沉淀版本演进、工程规范与完整源代?| 远程 Git 仓库?br>`https://github.com/OpenQGIS/QFieldDrop` | **?Git 跟踪**；包含完整源码、文档、测试用例与构建脚本；排除运行时临时缓存 |
| 🚀 **3. 打包内容 (Package Content)** | 面向 QGIS 官方插件门户（plugins.qgis.org）与终端用户的纯净运行时插件包 | 编译生成的临?目标 ZIP 内部结构（如 `QFieldDrop/` 与移动端根结构） | **绝对纯净**?00% 剔除开发依赖、测试数据、未编译翻译与过程稿，通过官方安全合规扫描 |
| 🏷?**4. [Releases] 发布资产** | 面向 GitHub Releases、外业现场离线分发及历史版本基线归档的最终发布制?| 物理脱离测试目录的专属归档库?br>`E:\...\OpenQGIS_Lab\...\QFieldDrop\` | **标准化制?*；包含正式命?ZIP、通用别名 ZIP、SHA256 校验清单及镜像源?|

---

## 📂 二、当前项目全量文件四维归类清?

下表为对当前插件工作区内所有目录与文件逐一扫描后的归类对照（按目录层级展开）：

| 文件 / 目录路径 | 文件类型与作?| 1. 开发代?| 2. 仓库推?| 3. 打包内容 | 4. [Releases] | 备注说明 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`__init__.py`** | 桌面端插件入口工厂函?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | QGIS 插件必备入口 (`classFactory`) |
| **`plugin.py`** | 插件核心调度?UI 注册逻辑 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 工具栏按钮、菜单动作与对话框生命周?|
| **`metadata.txt`** | 桌面?QGIS 插件元数据配?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 索引 `icon=icon/QFieldDrop_logo.svg` |
| **`README.md`** | 项目首页架构与图文使用说?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 用户离线查看?GitHub 主页 |
| **`LICENSE`** | GNU AGPL v3.0 开源许可证文本 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 官方审核与开源分发强制必?|
| **`CHANGELOG.md`** | 语义化版本更新日?(中英双语) | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 每次发布记录更新?|
| **`i18n_strings.py`** | 国际化静态字符串表与保底字典 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 双保?i18n 机制核心 |
| **`i18n_helper.py`** | 多语言加载与动态切换辅助模?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 动态识别当前系统与 QGIS Locale |
| **`build_clean_release.py`** | 桌面端与移动端双轨纯净打包脚本 | ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 本地构建发布流水线工?|
| **`build_mobile_release.py`** | 移动?QField 插件独立打包脚本 | ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 自动化生成移动端各格式安装包与校验码 |
| **`build_icons_component.py`** | Inkscape 矢量图标母稿拼装脚本 | ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 图标切图与组件库构建脚本 |
| **`ROADMAP.md`** | 开发迭代计划与敏捷路线?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 协作者参考，官方分发严禁携带 |
| **`DISTRIBUTION_GUIDE.md`**| 插件发布规范与分发指引文?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 团队发布规范指导文档 |
| **`PROJECT_STRUCTURE.md`** | 本项目工程结构与四维归类文档 | ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 本结构规范文?|
| **`.gitignore`** | Git 版本管理排除规则配置 | ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 过滤临时文件与字节码 |
| **`.pytest_cache/`** | pytest 测试运行状态缓?| ?**开发代?* | ?**严禁** | ?**排除** | ?不打?| 本地临时缓存，严禁污染仓库与发布?|
| **`__pycache__/` (各级)** | Python 编译生成的字节码 (`*.pyc`) | ?**开发代?* | ?**严禁** | ?**排除** | ?不打?| 运行时生成，严禁打入分发?|
| **`core/` (全部模块)** | 核心协议与网络服务层 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 纯底层算法：packager, net_server, qr, localsend, adb ?|
| **`ui/` (全部模块)** | 原生 Qt 对话框与面板组件 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 界面交互与控制台面板 |
| **`i18n/*.qm`** | 编译后的二进制多语言?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 运行时直接加载的二进制翻译包 |
| **`i18n/*.ts`** | Linguist 源码翻译源文?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 仅用于编译，分发包剔除以减小体积 |
| **`i18n/build_i18n.py`** | 提取与编?QM 文件的工具脚?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 仅构建期使用 |
| **`icon/QFieldDrop_logo.svg`**| 插件主入?Logo 图标 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | metadata.txt 索引的官方图?|
| **`icon/icon_*.svg`** | 顶层三大动作按钮矢量图标 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 投送、接收、安装助手的工具栏图?|
| **`icon/0_icons.svg`** | 基础图标母稿设计源文?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| Inkscape 原始过程工程?|
| **`icons/*.svg` (21?** | 界面各控件使用的标准 SVG 图标 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | refresh, smartphone, zap, link ?|
| **`icons/0_icons_Component.svg`**| 组件库母稿源文件 | ?**开发代?* | ?**推?* | ?**排除** | ?不打?| Inkscape 组件库母?|
| **`mobile/main.qml`** | 移动?QField 助手界面与回传逻辑 | ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 手机端核?QML 源码 |
| **`mobile/metadata.txt`** | 移动?QField 插件元数?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 手机 QField 插件描述配置 |
| **`mobile/icon.svg`** | 移动?QField 助手工具栏图?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 手机端最新矢量图?(已同? |
| **`mobile/LICENSE` & `README`**| 移动端开源许可证与说?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 手机端独立插件说?|
| **`companion/`** | 伴侣拉取插件源码与工程资?| ?仅开?| ?**推?* | ?**打包** | ?(在ZIP? | 辅助配套移动端资?|
| **`tests/` (全部模块)** | 单元测试脚本与测试固?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 自动化回归测试套?|
| **`testdata/`** | 测试样本工程与脱敏数?| ?**开发代?* | ?**推?* | ?**排除** | ?不打?| 测试运行输入数据 |

---

## 🏷?三、[Releases] 发布资产制品库结?(`OpenQGIS_LAB`)

根据团队发布流水线规范，所有面向最终用户与 GitHub Releases 的打包制品物理脱离开发工作区，统一输出并归档于专用仓库?

> **物理基准路径**：`E:\QGIS文章\OpenQGIS_Lab\OpenQGIS_QGISPlugins_LAB\QFieldDrop\`

```plaintext
E:\...\OpenQGIS_Lab\OpenQGIS_QGISPlugins_LAB\QFieldDrop/
├── QFieldDrop-4QGIS/                        # 【A. 桌面?QGIS 官方分发区?
?  ├── QFieldDrop_V-1.2.0-beta.zip               # ⭐️ 官方纯净分发?(上传 plugins.qgis.org 或离线安?
?  └── QFieldDrop/                          # 纯净源码镜像 (脱敏剔除所有测?构建脚本后的运行时源?
?
├── QFieldDropMobile/                        # 【B. 移动?QField 助手独立发布区?
?  ├── QFieldDropMobile_V-1.0.4.zip         # ⭐️ QField 原生标准根目录安装包 (从压缩包安装)
?  ├── qfield_drop_mobile.zip               # 通用直链别名?(用于局域网扫码与静态下?
?  ├── QFieldDropMobile_folder_V-1.0.4.zip  # 沙盒解压专用?(内置 qfield_drop/ 包裹文件?
?  ├── README.md                            # 移动端发布说明与官方 SHA-256 校验清单?
?  └── QFieldDropMobile/                    # 移动端纯净源码镜像
?
└── QFieldDrop_History/                      # 【C. 版本演进历史归档库?
    ├── QFieldDrop_V-1.0.1.zip               # 桌面端历史版本快?
    ├── QFieldDropMobile_V-1.0.4.zip         # 移动端历史直装包快照
    └── QFieldDropMobile_folder_V-1.0.4.zip  # 移动端历史沙盒包快照
```

### 3.1 移动端发布包 SHA-256 校验基准

| 资产文件?| 适用安装场景 | SHA-256 校验?|
| :--- | :--- | :--- |
| **`QFieldDropMobile_V-1.0.4.zip`** | 手机 QField 内部：设?$\rightarrow$ 插件 $\rightarrow$ 从压缩包安装 (推荐) | `fe897035b3bcf3969d243a672f944d6bbda9e83034014657030ccedba071b85f` |
| **`qfield_drop_mobile.zip`** | 局域网 HTTP 扫码在线直链下载 | `fe897035b3bcf3969d243a672f944d6bbda9e83034014657030ccedba071b85f` |
| **`QFieldDropMobile_folder_V-1.0.4.zip`** | Android 手机文件管理器手动解压至 `/sdcard/.../plugins/qfield_drop/` | `cbdc025766efb96c059bac61b8bbe78ff2c4f3be6fef93fcfe1c73dcbb6674db` |

---

## 🛠?四、打包与分发流水线指?

项目已配置一键式流水线脚本，可在开发根目录下直接调用：

1. **桌面?+ 移动?全量纯净打包**?
   ```powershell
   python build_clean_release.py
   ```
   * 自动解析两端 `metadata.txt` 语义化版本号?
   * 严格剔除 `tests/`、`testdata/`、`0_*.svg`、`*.pyc` 等开发杂质；
   * 强制检查所?ZIP 条目均为 POSIX 正斜?`/`?
   * 自动归档?`QFieldDrop-4QGIS/`、`QFieldDropMobile/` ?`QFieldDrop_History/`?

2. **移动端单独快速打?*?
   ```powershell
   python build_mobile_release.py
   ```
   * 独立快速构?3 种格式的移动?QField 安装包并自动更新 `README.md` 校验码?

3. **多语言二进制编?*?
   ```powershell
   python i18n/build_i18n.py zh_CN
   python i18n/build_i18n.py zh_TW
   ```
