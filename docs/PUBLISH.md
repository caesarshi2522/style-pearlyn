# 发布到 GitHub

建议仓库名：`style-pearlyn`。

1. 新建 GitHub 仓库；将解压后 `style-pearlyn` 文件夹里的内容放到仓库根目录。根目录应直接出现 README.md、plugins、docs 和隐藏的 .agents 文件夹。
2. 推荐用 Git 或 GitHub Desktop 提交完整目录，以免浏览器拖拽遗漏 .agents 与 .codex-plugin。
3. README 会自动成为仓库首页。所有介绍图片均为相对路径，不需要额外图床。
4. 仓库 About 可填写：`在 Codex 中看图选风格，为已有 HTML 改版，或先设默认风格再生成网页。`
5. Topics 建议：`codex-plugin`、`html`、`web-design`、`visual-design`、`agent-skills`。
6. 上传完成后，先在新的环境按 docs/INSTALL.md 安装验证，再传播仓库链接。若发布 Release，可以附上完整源码 ZIP；不要只上传 ZIP 而省略源码，否则首页和插件源不会生效。

## 根目录应有

```text
.agents/plugins/marketplace.json
plugins/style-atlas/.codex-plugin/plugin.json
plugins/style-atlas/skills/style-atlas/SKILL.md
docs/images/
README.md
```

本目录为可直接发布的仓库内容；远程安装需在目标环境验证。使用许可保持原状，若希望后续按某个开源许可证发布，请由项目所有者明确选择。
