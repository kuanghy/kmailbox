#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2018-02-12 17:40:18

import os
from kmailbox import Message, MailBox

try:
    from unittest import mock
except ImportError:
    import mock


html_content = '''\
<body>
<p><img src="cid:0"></p>

<p>Hello! I am <em>Huoty</em>.</p>

<p>How are you?</p>

<p>Give you a picture:</p>
<p><img src="cid:1"></p>
</body>
'''


class TestMailBox(object):

    def setup_class(cls):
        # cls.mailbox = MailBox(imap_host="imap.yeah.net", smtp_host="smtp.yeah.net")
        cls.mailbox = MailBox(smtp_host="smtp.yeah.net")
        cls.mailbox.login(os.environ["MAIL_USER"], os.environ["MAIL_PASSWD"])

        cls.msg = Message()
        cls.msg.sender = "KMailBox<konitor@yeah.net>"
        cls.msg.recipient = "huayongkuang@qq.com"

    def test_sendmail(self):
        self.msg.subject = "kmailbox test"
        self.msg.content = "This is test"
        self.mailbox.send(self.msg)

    def test_send_html_mail(self):
        self.msg.subject = "kmailbox test send html mail"
        self.msg.content = html_content
        self.msg.is_html = True
        self.msg.attachments = ["cid0:imgs/mailbox-icon.png",
                                "cid1:imgs/20171005170550.jpg"]
        with mock.patch.object(self.mailbox, "use_tls", True):
            self.mailbox.send(self.msg)

    def test_send_attachments(self):
        self.msg.subject = "kmailbox test send attachments"
        self.msg.content = html_content
        self.msg.is_html = True
        self.msg.attachments = ["cid0:imgs/mailbox-icon.png",
                                "cid1:imgs/20171005170550.jpg",
                                "kmailbox.py", "README.md"]
        self.mailbox.send(self.msg)
