KMailBox
========

![mailbox](imgs/mailbox-icon.png)

Python 邮件模块，支持邮件发送与接收。

## 接口说明

### Message

```python
Message(sender=None, recipient=None, cc_recipient=None,bcc_recipient=None,
    reply_recipient=None, subject=None, content=None, is_html=False,
    attachments=None, headers=None, charset="utf-8")
```

邮件消息，用于处理发件人、收件人、附件等

如果邮件内容为 HTML，则需将 is_html 设置为 True。当需要在 HTML 中插入图片、音视频等媒体时，媒体文件路径应该放在 attachments 参数中，并以 `cid + 序号:` 开头，以标记是需要在 HTML 中插入的媒体，如：

> cid0:imgs/mailbox-icon.png

### MailBox

```python
MailBox(imap_host=None, smtp_host=None, username=None, password=None,
    use_tls=False, use_ssl=False, use_plain_auth=False, timeout=10,
    logger=None)
```

`imap_host`、`smtp_host` 分别为 imap、smtp 的主机地址，如果需要支持端口号，则用冒号 `:` 分割，如：

> smtp.yeah.net:25

`use_tls` 表示是否加密邮件，`use_ssl` 表示是否使用 ssl 协议。

方法说明：

- login(username, password)

登录邮箱，如果只设置了 smtp_host，则登录只记录密码，在调用 send 方法发送邮件是才真正登录

- logout()

退出登录

- send(message=None, debug=False)

发送邮件，参数 message 为 `Message` 实例，debug 表示是否开启调试模式

接收邮件相关接口待开发...

## 接口调用示例

### 发送普通文本邮件

```python
import os
from kmailbox import Message, MailBox

msg = Message(sender="KMailBox<konitor@yeah.net>", recipient="huayongkuang@qq.com")
msg.subject = "kmailbox test"
msg.content = "This is test"

mailbox = MailBox(smtp_host="smtp.yeah.net", use_tls=True)
mailbox.login(os.environ["MAIL_USER"], os.environ["MAIL_PASSWD"])
mailbox.send(msg)
```

### 发送 HTML 邮件并插入附件

该示例将发送一个 HTML 邮件，同时在 HTML 中插入图片，并且还带上文件附件

```python
msg = Message(sender="KMailBox<konitor@yeah.net>", recipient="huayongkuang@qq.com")
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

mailbox = MailBox(smtp_host="smtp.yeah.net", use_ssl=True)
mailbox.login(os.environ["MAIL_USER"], os.environ["MAIL_PASSWD"])
mailbox.send(msg)
```

## 命令行工具

待开发


## 参考

- [https://github.com/awangga/outlook](https://github.com/awangga/outlook)
- [https://github.com/ikvk/imap_tools](https://github.com/ikvk/imap_tools)
- [https://bitbucket.org/ginstrom/mailer/overview](https://bitbucket.org/ginstrom/mailer/overview)
- [https://github.com/martinrusev/imbox](https://github.com/martinrusev/imbox)
- [https://gist.github.com/nickoala/569a9d191d088d82a5ef5c03c0690a02](https://gist.github.com/nickoala/569a9d191d088d82a5ef5c03c0690a02)
