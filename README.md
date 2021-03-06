KMailBox
========

![mailbox](imgs/mailbox-icon.png)

Python 邮件模块，支持邮件发送与接收。

## 接口说明

### Message

```python
Message(**kwargs)
```

用于描述邮件内容，仅支持关键参数，支持以下的参数（同时也为对象属性）：

- **sender**: 发件人
- **recipient**: 收件人（多人时为 list 等序列类型，抄送人、回复人等字段也一样）
- **cc_recipien**: 抄送人
- **bcc_recipien**: 暗抄送人
- **reply_recipient**: 回复收件人
- **subject**: 主题
- **content**: 内容
- **is_html**: 是否为 HTML 内容，否则为普通文本内容
- **attachments**: 附件
- **to_addrs**: 所有收件人地址，包括收件人、抄送人、暗抄送人、回复收件人在内
- **headers**: 邮件头（为要发送的消息时可用于设置格外头信息）
- **charset**: 编码
- **is_received** 用于标记消息是否为从 IMAP 服务器接收到的消息（接收的消息与要发送的消息某些字段值的类型可能会不同）

为接受到的消息时会设置的属性：

- **uid**: 唯一标识
- **flags**: 标志

如果邮件内容为 HTML，则需将 is_html 设置为 True。当需要在 HTML 中插入图片、音视频等媒体时，媒体文件路径应该放在 attachments 参数中，并以 `cid + 序号:` 开头，以标记是需要在 HTML 中插入的媒体，如：

> cid0:imgs/mailbox-icon.png

对象方法包括：

- **as_string**: 转化为字符串
- **from_string**: 从文本字符串中获取消息并转化
- **from_bytes**: 从二进制中获取消息并转化
- **uid_from_string**: 从字符串中获取 UID
- **flag_from_string**: 从字符串中国获取 Flag
- **from_raw_message_data**: 从原始的消息数据中获取消息并转化

### MailFlag

基本邮件标志，包括以下属性：

- SEEN: 邮件已读
- ANSWERED: 邮件已回复
- FLAGGED: 邮件标记为紧急或者特别注意
- DELETED: 邮件为删除状态
- DRAFT: 邮件未写完（标记为草稿状态）
- RECENT: 邮件最近到达该邮箱（本次会话是首次收到当前邮件通知）

### MailAddress

```python
MailAddress(address, name=None)
```

用于描述邮件地址，继承自 UserString，其属性包括：

- address: 邮箱地址
- name: 邮箱所有者名字
- data: 若 name 存在，则为 'name<address>' 的形式，否则为 address

使用示例：

```
>>> import kmailbox
>>> addr = kmailbox.MailAddress('sudohuoty@163.com', 'Huoty')
>>> addr
'Huoty<sudohuoty@163.com>'
>>> addr.address
'sudohuoty@163.com'
>>> addr.name
'Huoty'
```

### MailAttachment

```python
MailAttachment(part)
```

用户描述邮件附件，参数 part 为一个 multipart 对象。

其对象包含以下只读属性：

- **filename**: 文件名
- **content_type**: 内容类型
- **payload**: 具体的数据

对象方法：

- **download(directory=None, filename=None)**: 下载为本地文件

### MailBox

```python
MailBox(imap_host=None, smtp_host=None, username=None, password=None,
        use_tls=False, use_ssl=False, timeout=60, logger=None)
```

`imap_host`、`smtp_host` 分别为 imap、smtp 的主机地址，如果需要支持端口号，则用冒号 `:` 分割，如：

> smtp.gmail.com:25

`use_tls` 表示是否加密邮件，`use_ssl` 表示是否使用 ssl 协议。

参数 imap_host, smtp_host, username, password 可以通过设置环境来自动获取，对应的环境变量值为：

- **KMAILBOX_IMAP_HOST**
- **KMAILBOX_SMTP_HOST**
- **KMAILBOX_USERNAME**
- **KMAILBOX_PASSWORD**

方法说明：

- send(message=None, debug=False)

发送邮件，参数 message 为 `Message` 实例，debug 表示是否开启调试模式

- select(box="INBOX", readonly=False)

选择要操作的邮箱目录，参数 readonly 表示对邮件只读

- all(mark_seen=True, gen=False)

读取选定邮箱目录中的所有邮件，参数 mark_seen 表示在读取邮件时是否将其标记为已读，参数 gen 表示是否返回一个迭代器，否则返回一个列表

- unread(mark_seen=True, gen=False)

读取未读邮件

- recent(mark_seen=True, gen=False)

读取当前到达的邮件

- new(mark_seen=True, gen=False)

读取新邮件（即当前到达的未读邮件）

- old(mark_seen=True, gen=False)

读取以前的邮件

- flag(uid_set, flag_set, value)

为邮件设置 Flag

- expunge()

将邮箱中所有打了删除标记的邮件彻底删除

- mark_as_delete(uid_set)

标记邮件为已删除

- mark_as_seen(uid_set)

标记邮件为已读

- mark_as_unseen(uid_set)

标记邮件为未读

- close()

关闭邮箱，同时会关闭与 imap、smtp 服务器的连接

## 接口调用示例

### 发送普通文本邮件

```python
from kmailbox import Message, MailBox

msg = Message()
msg.sender = "Tester<test@google.com>"
msg.recipient = "hello@google.com"
msg.subject = "kmailbox test"
msg.content = "This is test"

mailbox = MailBox(smtp_host="smtp.gmail.com", use_tls=True)
mailbox.username = "username"
mailbox.password = "password"
mailbox.send(msg)
```

### 发送 HTML 邮件并插入附件

该示例将发送一个 HTML 邮件，同时在 HTML 中插入图片，并且还带上文件附件

```python
msg = Message()
msg.sender = "Tester<test@google.com>"
msg.recipient = "hello@google.com"
msg.subject = "kmailbox test send html and add attachments"
msg.is_html = True
msg.content = """\
<body>
<p><img src="cid:0"></p>

<p>Hello! I am <em>Huoty</em>.</p>

<p>How are you?</p>

<p>Give you a picture:</p>
<p><img src="cid:1"></p>
</body>
"""
msg.attachments = [
    "cid0:imgs/mailbox-icon.png",  # 注意 cid 后的序号应与 HTML 中标记的 cid 序号一致
    "cid1:imgs/20171005170550.jpg",
    "kmailbox.py",  # 普通文件附件
    "README.md"
]

mailbox = MailBox(
    smtp_host="smtp.gmail.com",
    use_ssl=True,
    username="username"
    password="password"
)
mailbox.send(msg)
```

### 接收邮件

```python
mailbox = MailBox(imap_host="imap.gmail.com", use_ssl=True)
mailbox.username = "username"
mailbox.password = "password"
mailbox.select()
for mail mailbox.all(mark_seen=False, gen=True)
    pprint({
        "uid": mail.uid,
        "sender": mail.sender,
        "to_addrs": mail.to_addrs,
        "subject": mail.subject,
        "date": str(mail.date),
        "flags": mail.flags,
        "attachments": [att.filename for att in mail.attachments],
    })
mailbox.logout()
```

## 命令行工具

命令行工具参数如下：

```
usage: kmailbox [-h] [-v] [-d]
                [--loglevel {debug,info,warning,error,fatal,critical}]
                [--imap IMAP] [--smtp SMTP] [-u USER] [-p PASSWORD]
                [--use-tls] [--use-ssl] [--timeout TIMEOUT]
                [--select SELECT] [--list] [--send] [-f SENDER]
                [-t TO [TO ...]] [--cc [CC [CC ...]]] [-s SUBJECT]
                [-c CONTENT] [-a [ATTACHMENT [ATTACHMENT ...]]] [--all]
                [--unread] [--recent] [--new] [--old] [--verbose]
                [--mark-as-seen] [--delete] [--seen] [--unseen]
                [--uid UID [UID ...]]
                [--relay-to [RELAY_TO [RELAY_TO ...]]]
```

详细使用方式可以通过执行 `kmailbox --help` 查看。

## 参考

- [https://github.com/awangga/outlook](https://github.com/awangga/outlook)
- [https://github.com/ikvk/imap_tools](https://github.com/ikvk/imap_tools)
- [https://bitbucket.org/ginstrom/mailer/overview](https://bitbucket.org/ginstrom/mailer/overview)
- [https://github.com/martinrusev/imbox](https://github.com/martinrusev/imbox)
- [https://gist.github.com/nickoala/569a9d191d088d82a5ef5c03c0690a02](https://gist.github.com/nickoala/569a9d191d088d82a5ef5c03c0690a02)
