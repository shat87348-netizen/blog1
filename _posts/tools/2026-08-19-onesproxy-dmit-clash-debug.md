---
layout: post
title: "OnesProxy + DMIT + Clash Verge 链式代理排障记录"
date: 2026-08-19 14:00:00 +0800
categories: [tools]
tags: [OnesProxy, DMIT, Clash-Verge, SOCKS5, VLESS, chain-proxy]
author: zhangshuming
excerpt: "通过 DMIT 与 Clash Verge 配置 OnesProxy SOCKS5 链式代理，并定位直连超时与错误出口问题的排障记录。"
---


## 问题背景

需要使用 OnesProxy 的静态住宅 SOCKS5 作为最终出口。该代理在本地网络不能直接连接，但可通过一台 DMIT 美国服务器访问。因此目标链路是：

```text
Mac → Clash Verge → DMIT VLESS → OnesProxy SOCKS5 → Internet
```

OnesProxy 后台显示该静态住宅代理为 SOCKS5 协议。

![OnesProxy 协议确认](/assets/images/onesproxy-dmit-clash/01-onesproxy-protocol-confirmation.png)

## 1. 先确认：本机直连确实不通

在 Mac 上直接测试 SOCKS5 的主机和端口，连接超时。

```bash
nc -vz <ONESPROXY_HOST> <PORT>
```

![Mac 直连端口超时](/assets/images/onesproxy-dmit-clash/02-mac-direct-nc-timeout.png)

这并不直接说明账号或代理失效，只能说明“Mac 到 SOCKS5 服务端”的直连路径不可达。供应商客服也说明，境内一般不支持直接使用海外代理 IP，需要经由可访问该代理的节点中转。

![OnesProxy 静态住宅代理入口](/assets/images/onesproxy-dmit-clash/03-onesproxy-static-residential-menu.png)

![供应商关于境内访问的说明](/assets/images/onesproxy-dmit-clash/04-onesproxy-support-access-note.png)

![供应商关于配置方式的说明](/assets/images/onesproxy-dmit-clash/05-onesproxy-support-setup-note.png)

## 2. 建立并验证 DMIT 中转

先在 DMIT 控制台准备 SSH 公钥。若出现 `Permission denied (publickey)`，检查私钥文件、权限和实际使用的密钥路径。

![DMIT SSH 密钥管理](/assets/images/onesproxy-dmit-clash/06-dmit-ssh-key-management.png)

![SSH 公钥认证失败](/assets/images/onesproxy-dmit-clash/07-ssh-publickey-auth-failed.png)

![本地 SSH 私钥文件](/assets/images/onesproxy-dmit-clash/08-ssh-private-key-files.png)

成功登录 DMIT 后，才从中转机验证 OnesProxy。

![DMIT SSH 登录成功](/assets/images/onesproxy-dmit-clash/09-dmit-ssh-login-success.png)

在 DMIT 上测试 SOCKS5 的 TCP 端口，结果成功：

```bash
nc -vz <ONESPROXY_HOST> <PORT>
```

![DMIT 端口测试成功](/assets/images/onesproxy-dmit-clash/10-dmit-nc-port-success.png)

再通过 SOCKS5 请求 IP 查询服务，得到 OnesProxy 的住宅出口 IP，说明代理凭据和出口均可用。

```bash
curl --socks5-hostname <USER>:<PASSWORD>@<ONESPROXY_HOST>:<PORT> https://ipinfo.io/ip
```

![DMIT 经 SOCKS5 请求成功](/assets/images/onesproxy-dmit-clash/11-dmit-socks5-curl-success.png)

## 3. 本机成功不等于链路配置正确

本机在特定代理环境下可以完成 SOCKS5 请求，且浏览器 IP 查询显示的是 DMIT 的美国地址。这说明流量可能只走到了 DMIT VLESS，而没有继续通过 OnesProxy 作为最终出口。

![Mac SOCKS5 测试成功](/assets/images/onesproxy-dmit-clash/12-mac-socks5-direct-success.png)

![ping0 显示 DMIT 地址](/assets/images/onesproxy-dmit-clash/13-ping0-dmit-ip.png)

关键不是把两个节点同时添加进 Clash，而是让 SOCKS5 节点的建连请求通过 DMIT 节点发出。

## 4. 失败路径：节点存在，但没有真正串联

在节点编辑页将 SOCKS5 与 VLESS 关联，UI 看起来已经选中了前置节点；但这还需要通过最终配置验证。

![编辑 SOCKS5 节点并选择前置代理](/assets/images/onesproxy-dmit-clash/14-clash-edit-socks5-pre-proxy.png)

![节点选择状态](/assets/images/onesproxy-dmit-clash/15-clash-edit-nodes-selected.png)

![Clash 首页代理选择](/assets/images/onesproxy-dmit-clash/16-clash-main-proxy-selection.png)

这时若 `curl` 报 SSL 连接错误或超时，不能只凭界面判断链路已经生效。

![经 Clash 请求时的 SSL 错误](/assets/images/onesproxy-dmit-clash/17-curl-through-clash-ssl-error.png)

日志给出了决定性证据：Clash 仍在直接拨号 OnesProxy 的地址，导致 `i/o timeout`。

当前配置中 SOCKS5 节点缺少 `dialer-proxy` 字段，正是链式代理没有落地的原因。

## 5. 正确做法：使用 Clash Verge 的链式代理模式

链式代理模式的节点点击顺序就是流量顺序：**先选 DMIT VLESS 作为入口，再选 OnesProxy SOCKS5 作为出口**。

```text
入口：DMIT VLESS
  ↓
出口：OnesProxy SOCKS5
```

初始状态没有代理链配置。

![链式代理模式初始页](/assets/images/onesproxy-dmit-clash/21-clash-chain-mode-empty.png)

添加节点后，确认右侧配置为“DMIT VLESS → OnesProxy SOCKS5”。此处 SOCKS5 单节点显示超时是预期现象：它的可达性测试会从本机直连，而本机原本就无法直接到达该地址；应以整条代理链的实际请求结果为准。

![链式代理模式已配置](/assets/images/onesproxy-dmit-clash/22-clash-chain-mode-configured.png)

另一次同样的节点选择界面记录如下：

![已选择的链式节点](/assets/images/onesproxy-dmit-clash/18-clash-edit-socks5-chain-ready.png)

## 6. 验证清单

启用链路后，保持 Clash Verge 的 TUN 或系统代理处于所需状态，并直接执行：

```bash
curl https://ipinfo.io/ip
```

预期应返回 OnesProxy 的出口 IP，而不是 DMIT 的 IP。随后可在浏览器访问 IP 查询站点复核。

排查时按以下顺序能最快缩小范围：

1. Mac `nc` 直连 SOCKS5 是否超时；
2. DMIT 上 `nc` 是否成功；
3. DMIT 上经 SOCKS5 的 `curl` 是否成功并显示住宅出口；
4. Clash 日志是否仍出现直拨 SOCKS5 的 `dial tcp ... i/o timeout`；
5. 最终配置是否包含让 SOCKS5 经 DMIT 拨号的链路配置；
6. 实际出口 IP 是否为 OnesProxy，而不是 DMIT。
