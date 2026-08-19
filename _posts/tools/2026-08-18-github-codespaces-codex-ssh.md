---
layout: post
title: "把 GitHub Codespaces 接入 Codex：一次完整的 SSH 配置路线"
date: 2026-08-18
categories: [tools]
tags: [GitHub, Codespaces, Codex, SSH, Jekyll]
author: zhangshuming
---

# 把 GitHub Codespaces 接入 Codex

这篇记录把一个 GitHub Codespaces 项目接入 Codex 桌面端的完整过程：用正式的 GitHub CLI / SSH / Codex CLI 流程，不复制令牌、不暴露远端服务端口。

**最终状态：** Codespace 已能通过 SSH 连接，远端 Codex CLI 已安装、已用设备码登录，并在项目目录 `/workspaces/haikus-for-codespaces` 中运行。页面底色改为红色这项实际改动尚未执行；连接完成后可直接交给 Codex 执行。

> 本文示例的 Codespace 主机别名为 `cs.upgraded-meme-69qwgr49rr9xcr7w9.main`。你的别名会不同，请以 `grep '^Host ' ~/.ssh/codespaces` 的输出为准。

## 路线总览

```text
GitHub CLI 授权（含 codespace scope）
        ↓
启动 Codespace
        ↓
生成 OpenSSH 配置并写入 Include
        ↓
用 SSH 验证连接
        ↓
在 Codespace 安装并登录 Codex CLI
        ↓
Codex 桌面端启用 SSH 主机并选择远端项目
        ↓
让 Codex 修改、运行、验证项目
```

## 0. 目标项目先能正常运行

项目是 GitHub 的 `haikus-for-codespaces` 示例。浏览器预览已经能显示页面，说明 Codespace 的开发容器和端口转发工作正常。

![Codespaces 中运行的 Haikus for Mona 页面]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-2a9493d9-1a8e-4731-b772-19d719bd4b1a.png' | relative_url }})

## 1. 安装并验证 GitHub CLI

在 **本机 Mac 终端** 安装 `gh` 后，先做登录验证：

```bash
gh auth status
```

正确结果应包含 `Logged in to github.com`，并显示 `repo` 等权限范围。

![GitHub CLI 已通过 macOS 钥匙串登录]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-e60a5264-f678-4416-a100-7ae066acf224.png' | relative_url }})

### 必需权限：`codespace`

只拥有 `repo` 并不足以列出或 SSH 到 Codespace；下图的 `HTTP 403` 明确提示缺少 `codespace` scope。

![缺少 codespace scope 的 403 错误]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-00c0364d-f0b7-4175-a612-21a1501dc6e9.png' | relative_url }})

刷新授权并增加该权限：

```bash
gh auth refresh -h github.com -s codespace
```

### 排障：浏览器能打开，终端却超时

设备授权需要终端访问 GitHub 的 HTTPS 接口。如果报错中出现 `login/device/code` 或 `read: operation timed out`，不是账号权限问题，而是终端没有走通 GitHub 网络路径。

![GitHub 设备授权端点网络超时]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-da765d8c-8fda-446e-926a-f1f4b768146f.png' | relative_url }})

先检查：

```bash
curl -I --connect-timeout 10 https://github.com
```

若仍超时，需要让终端走可用的 VPN / 代理，再重新执行 `gh auth refresh`。不要通过复制 GitHub Token 或把 Token 发给他人来绕过这个步骤。

## 2. 启动 Codespace 并生成 SSH 配置

停止状态的 Codespace 不能生成有效 SSH 配置。命令出现 `Shutdown` 时，先在 GitHub 网页中选择 **Resume / Restart codespace**，等它进入运行状态。

![Codespace 处于 Shutdown 状态]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-a2c1975d-d6a2-4fea-85f7-9c186b4afe1d.png' | relative_url }})

再运行：

```bash
gh codespace ssh --config > ~/.ssh/codespaces
```

没有错误输出并返回提示符，通常表示配置已生成成功。

![成功生成 Codespaces SSH 配置]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-07da12a2-e69d-412f-b356-0c019671c718.png' | relative_url }})

### 将生成的配置纳入 OpenSSH

`Include ~/.ssh/codespaces` 是 SSH 配置文件的一行，不是一条 shell 命令。用 Vim 编辑：

```bash
vim ~/.ssh/config
```

按 `G`、`o`，添加：

```sshconfig
Include ~/.ssh/codespaces
```

再按 `Esc`，输入 `:wq` 并回车保存。

## 3. 找到主机别名并验证 SSH

列出生成的具体主机别名：

```bash
grep '^Host ' ~/.ssh/codespaces
```

![生成的 Codespace SSH 主机别名]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-00440297-70a4-4163-9fdd-42674d10408a.png' | relative_url }})

使用该别名验证连接：

```bash
ssh cs.upgraded-meme-69qwgr49rr9xcr7w9.main 'pwd'
```

如果返回远端路径，说明 SSH 隧道、GitHub CLI 权限和 Codespace 都已就绪。

## 4. 在远端安装 Codex CLI

Codex 桌面端会发现 SSH 主机，但远端必须有可执行的 `codex`。红点“未安装 Codex CLI”正是这一缺口。

![Codex 桌面端已发现 SSH 主机，但远端尚无 Codex CLI]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-d025b003-b3de-44c6-8dc0-97ea16e714d0.png' | relative_url }})

进入远端：

```bash
ssh cs.upgraded-meme-69qwgr49rr9xcr7w9.main
```

在 Codespace 中按官方安装方式执行：

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
```

## 5. 在无浏览器的远端使用“设备码登录”

远端 Codespace 没有可直接交互的浏览器时，在 Codex 的登录菜单选择 **2. Sign in with Device Code**。

![Codex CLI 的设备码登录选项]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-1cbebfaa-debf-4cd5-9246-82cc9004be73.png' | relative_url }})

本机 ChatGPT 应用中，确保已开启“为 Codex 启用设备代码授权”。

![ChatGPT 应用中的设备代码授权开关]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-d5d1ddfc-7326-4834-8979-49bb9c32c65c.png' | relative_url }})

然后回到远端终端按回车。它会给出一次性验证码和授权网址：在本机浏览器打开网址、输入验证码、确认授权；不要在远端终端输入 ChatGPT 密码，也不要把验证码公开发送。

> **常见误区：** “控制其他设备 → 添加设备”里要求的 8 位 PIN，是把另一台 Mac/PC 加为远程控制设备的功能，和 Codespace 的设备码登录无关。

![与 SSH 设备码登录无关的 Mac/PC 配对窗口]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-e449c8f5-219e-4b3a-b0fe-74f2e0e1606b.png' | relative_url }})

## 6. 验证远端 Codex 已可运行

成功后，Codex 应显示当前目录为项目工作区。`bubblewrap` 的黄色提示在本例中不阻断运行：Codex 会使用内置版本。

![远端 Codex 已在项目目录中运行]({{ '/assets/images/codespaces-codex-guide/codex-clipboard-56d77958-9c45-48d9-93a4-bfd41850bc55.png' | relative_url }})

确认信息应类似：

```text
directory: /workspaces/haikus-for-codespaces
```

## 7. 在 Codex 桌面端接入项目

回到 Codex 桌面端：

1. 打开 **设置 → Connections → SSH**。
2. 关闭再打开该 Codespace 主机，或重启应用，让状态重新探测。
3. 红点消失后，启用主机。
4. 选择远端项目目录：`/workspaces/haikus-for-codespaces`。

此后在该远端项目启动的 Codex 对话，会在 Codespace 的文件系统和 shell 内运行；本机文件不会被误改。

## 8. 连接完成后：执行“底色改红”任务

在选中远端项目的 Codex 对话中发送：

```text
请定位此项目控制页面背景色的样式，把底色改为红色；运行项目并验证浏览器预览。完成后展示 diff 和验证结果。
```

建议在改动前后都执行：

```bash
git status
```

并在确认页面正确后再决定是否提交到 GitHub。

## 关键原则

- GitHub CLI 授权、SSH 配置和 Codex 登录各自独立；网页登录成功不代表 `gh` 已获得所需 scope。
- `codespace` scope 是 GitHub CLI 管理 Codespaces 的必要权限。
- 停止 Codespace 可以停止算力计费，但保留的磁盘仍会占用存储额度。
- 只使用 SSH 隧道连接远端，不将 Codex 服务端口暴露到公网。
- 不共享 GitHub Token、ChatGPT 密码或设备验证码。

## 官方参考

- [GitHub：通过 GitHub CLI 使用 Codespaces](https://docs.github.com/en/codespaces/developing-in-a-codespace/using-github-codespaces-with-github-cli)
- [GitHub：修改 Codespace 机器类型](https://docs.github.com/en/codespaces/customizing-your-codespace/changing-the-machine-type-for-your-codespace)
- [OpenAI：Codex SSH 远程连接](https://learn.chatgpt.com/docs/remote-connections)
- [OpenAI：Codex CLI 安装与登录](https://learn.chatgpt.com/docs/codex/cli)
