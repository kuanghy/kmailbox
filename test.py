#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2018-02-12 17:40:18

import os
from kmailbox import Message, MailBox


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

    def setup_class(self):
        self.mailbox = MailBox(imap_host="imap.yeah.net", smtp_host="smtp.yeah.net")
        self.mailbox.login(os.environ["MAIL_USER"], os.environ["MAIL_PASSWD"])

        self.msg = Message()
        self.msg.sender = "KMailBox<konitor@yeah.net>"
        self.msg.recipient = "1346632121@qq.com"

    def test_sendmail(self):
        self.msg.subject = "kmailbox test"
        self.msg.content = "This is test"
        self.mailbox.sendmail(self.msg)

    def test_send_html_mail(self):
        self.msg.subject = "kmailbox test send html mail"
        self.msg.content = html_content
        self.msg.is_html = True
        self.msg.attachments = ["cid0:imgs/mailbox-icon.png", "cid1:imgs/20171005170550.jpg"]
        self.mailbox.sendmail(self.msg)

    def test_send_attachments(self):
        self.msg.subject = "kmailbox test send attachments"
        self.msg.content = html_content
        self.msg.is_html = True
        self.msg.attachments = ["cid0:imgs/mailbox-icon.png",
                                "cid1:imgs/20171005170550.jpg",
                                "kmailbox.py", "README.md"]
        self.mailbox.sendmail(self.msg)
