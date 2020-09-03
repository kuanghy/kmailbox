#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2018-02-12 17:40:18

import os
import sys
import logging
from inspect import isgenerator
from pprint import pprint
from kmailbox import Message, MailBox, string_types

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


class TestMessage(object):

    def test_property(self):
        msg = Message()
        assert msg.sender is None
        msg.sender = "hello@email.com"
        assert msg.sender == "hello@email.com"

        msg.recipient = "to@email.com"
        msg.cc_recipient = "cc@email.com"
        assert len(msg.to_addrs) == 2

    def test_as_string(self):
        msg = Message()
        msg.sender = "Test<test@email.com>"
        msg.recipient = "to@email.com"
        msg.reply_recipient = "reply@email.com"
        msg.content = "This is Test"
        msg_str = msg.as_string()
        print(msg_str)
        assert msg_str


class TestMailBox(object):

    def setup_class(cls):
        logger = logging.getLogger("kmailbox")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            "%(levelname)s - %(asctime)s - %(message)s"
        ))
        logger.addHandler(handler)
        logger.propagate = False

        cls.mailbox = MailBox(
            imap_host=os.getenv("KMAILBOX_IMAP_HOST"),
            smtp_host=os.getenv("KMAILBOX_SMTP_HOST"),
            use_ssl=True,
            logger=logger,
        )
        cls.mailuser = os.environ["KMAILBOX_USER"]
        cls.mailbox.username = cls.mailuser
        cls.mailbox.password = os.environ["KMAILBOX_PASSWD"]

        cls.sender = "KMailBox<{}>".format(cls.mailuser)
        cls.recipient = "huayongkuang@qq.com"
        # cls.cc_recipient = ["sudohuoty@163.com"]

    def teardown_class(cls):
        cls.mailbox.close()

    def create_message(self):
        msg = Message()
        msg.sender = self.sender
        msg.recipient = self.recipient
        # msg.cc_recipient = self.cc_recipient
        return msg

    def test_sendmail(self):
        msg = self.create_message()
        msg.subject = "kmailbox test"
        msg.content = "This is test"
        self.mailbox.send(msg)

    def test_send_html_mail(self):
        msg = self.create_message()
        msg.subject = "kmailbox test send html mail"
        msg.content = html_content
        msg.is_html = True
        msg.attachments = ["cid0:imgs/mailbox-icon.png",
                           "cid1:imgs/20171005170550.jpg"]
        with mock.patch.object(self.mailbox, "use_tls", True):
            self.mailbox.send(msg)

    def test_send_attachments(self):
        msg = self.create_message()
        msg.subject = "kmailbox test send attachments"
        msg.content = html_content
        msg.is_html = True
        msg.attachments = ["cid0:imgs/mailbox-icon.png",
                           "cid1:imgs/20171005170550.jpg",
                           "kmailbox.py", "README.md"]
        self.mailbox.send(msg)

    def test_receive_mails(self):
        print(self.mailbox.folders)
        self.mailbox.select()
        # print(self.mailbox.select("垃圾邮件"))
        mails = self.mailbox.all(mark_seen=False)
        # mails = self.mailbox.unread(mark_seen=False)
        # mails = self.mailbox.new(mark_seen=False)
        # mails = self.mailbox.from_criteria("konitor@yeah.net", mark_seen=False)
        print(mails)
        pprint([{
            "uid": mail.uid,
            "sender": mail.sender,
            "to_addrs": mail.to_addrs,
            "subject": mail.subject,
            "date": str(mail.date),
            "flags": mail.flags,
            "attachments": [att.filename for att in mail.attachments],
        } for mail in mails])
        assert isinstance(mails[0].content, string_types)

        assert isgenerator(self.mailbox.all(mark_seen=False, gen=True))

    def test_flag(self):
        self.mailbox.select()
        print(self.mailbox.mark_as_unseen("1384335828"))
        print(self.mailbox.mark_as_seen("1384335828"))

    def test_delete_mail(self):
        self.mailbox.select()
        self.mailbox.mark_as_delete("1384335845,1384335844")
        self.mailbox.expunge()

    def test_download_attachment(self):
        self.mailbox.select()
        for mail in self.mailbox.all(mark_seen=False, gen=True):
            if not mail.attachments:
                continue
            for att in mail.attachments:
                att.download(os.path.expanduser("~/Temp"))
                print("download attachment '%s'" % att.filename)
