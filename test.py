#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2018-02-12 17:40:18

import os
from kmailbox import Message, MailBox


html_content = '''\
<body>
Hello!

<p><img src="cid:0"></p>
I am Huoty.

How are you?

Give you a picture:
<p><img src="cid:1"></p>
</body>
'''


class TestMailBox(object):

    def setup_class(self):
        self.mailbox = MailBox(imap_host="imap.yeah.net", smtp_host="smtp.yeah.net")
        self.mailbox.login(os.environ["MAIL_USER"], os.environ["MAIL_PASSWD"])

    def test_sendmail(self):
        msg = Message()
        msg.sender = "KMailBox<konitor@yeah.net>"
        msg.recipient = "1346632121@qq.com"
        msg.subject = "kmailbox test"
        msg.content = "This is test"
        self.mailbox.sendmail(msg)
