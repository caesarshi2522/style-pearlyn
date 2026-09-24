# 安装 Style Pearlyn

## 环境

支持本地插件的 Codex、可执行本地文件的任务环境，以及完整 Python 3.9+。使用 Python 标准库，不需要 pip install。优先使用 Codex 工作区自带的 Python。当前只在 Windows 验证。

## 下载后安装

在仓库点 Code → Download ZIP 并解压。将完整目录路径交给 Codex，要求添加这个目录作为插件源，安装 `style-atlas@style-pearlyn`。安装后新建任务。

也可以在解压后的仓库根目录运行：

```sh
codex plugin marketplace add .
codex plugin add style-atlas@style-pearlyn
```

第二条命令适用于提供 `plugin add` 的 Codex 版本。其他版本请重启应用，在插件目录中切换到 `style-pearlyn` 来源，安装 Style Pearlyn。

显示名称：Style Pearlyn；插件 ID：style-atlas；仓库插件源：style-pearlyn。不要仅复制 SKILL.md，它依赖随包的脚本、参考图和目录数据。已有同名来源时，先核对路径，不要覆盖其他人的插件源。

## 从 GitHub 仓库安装

从本项目的公开仓库安装：

```sh
codex plugin marketplace add caesarshi2522/style-pearlyn
codex plugin add style-atlas@style-pearlyn
```

仓库地址：https://github.com/caesarshi2522/style-pearlyn 。完整的新设备安装仍需在目标环境验证。

## 首次使用

新建本地任务，说“先用 Style Pearlyn 选一个默认风格”。打开图片面板后点“选用”，确认出现“当前默认”，再描述要生成的网页。

已有 HTML 则先上传，再说“用 Style Pearlyn 给这个 HTML 换个风格”。保持任务运行直到收到新文件。

## 更新和换设备

重新下载新版并安装，在新任务加载新版本。插件不自动迁移其他设备上的任务状态；换设备需要重新安装并提供 HTML 和依赖文件。本机面板地址不能跨设备使用。

安装结构参考 [OpenAI 官方插件文档](https://developers.openai.com/plugins/build/plugins)。本项目未宣称上架官方公共插件目录。
