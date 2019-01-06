# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2018-02-12 17:30:04

import os
import sys
import re
import time
import logging
import smtplib
import imaplib
import mimetypes
import email
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart


__version__ = "0.1.0"

if sys.version_info.major > 2:
    string_types = str
else:
    string_types = basestring


class Message(object):
    """邮件消息"""

    def __init__(self, sender=None, recipient=None, cc_recipient=None,
                 bcc_recipient=None, reply_recipient=None, subject=None,
                 content=None, is_html=False, attachments=None, headers=None,
                 charset="utf-8"):
        self.sender = sender                    # 发件人
        self.recipient = recipient              # 收件人，多人时为 list 等序列类型
        self.cc_recipient = cc_recipient        # 抄送人(Carbon Copy)
        self.bcc_recipient = bcc_recipient      # 暗抄送人(Blind Carbon Copy)
        self.reply_recipient = reply_recipient  # 回复收件人
        self.subject = subject                  # 邮件主题
        self.content = content                  # 邮件内容
        self.is_html = is_html                  # 是否为 html 内容的邮件
        self.attachments = attachments          # 附件
        self.headers = headers                  # 额外的邮件头
        self.charset = charset                  # 邮件编码

    @property
    def to_addrs(self):
        """邮件消息需要到达的地址"""
        addrs = []
        recipients = [self.recipient, self.cc_recipient, self.bcc_recipient,
                      self.reply_recipient]
        for recp in recipients:
            if not recp:
                continue
            if isinstance(recp, string_types):
                addrs.append(recp)
            else:
                addrs.extend(list(recp))
        return addrs

    def _set_headers(self, msg=None):
        msg = msg or MIMEMultipart()

        msg['Date'] = time.strftime("%Y-%m-%d %H:%M:%S %a", time.localtime())
        msg['Subject'] = self.subject
        msg['From'] = self.sender

        recipient_mapping = {
            "To": self.recipient,
            "CC": self.cc_recipient,
            "BCC": self.bcc_recipient,
            "reply-to": self.reply_recipient,
        }
        for hname, recp in recipient_mapping.items():
            if not recp:
                continue
            if isinstance(recp, string_types):
                msg[hname] = recp
            else:
                msg[hname] = ";".join(list(recp))

        if self.headers:
            for key, value in self.headers.items():
                if isinstance(value, bytes):
                    msg[key] = value.decode(self.charset)
                else:
                    msg[key] = value

        return msg

    def _attach_attachment(self, msg, attachment):
        html_media = re.search("^cid(\d+):(.+)$", attachment)

        att_path = html_media.group(2) if html_media else attachment
        att_name = os.path.basename(att_path)
        ctype, encoding = mimetypes.guess_type(att_path)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)

        if html_media:  # 判断是否为 html 中包含的媒体
            if maintype == "image":
                mime_class = MIMEImage
            elif maintype == "audio":
                mime_class = MIMEAudio
            else:
                raise Exception(
                    "Undefined attachment type of html media: %s" % maintype
                )

            with open(att_path, 'rb') as fp:
                mime = mime_class(fp.read(), _subtype=subtype)

            cid = html_media.group(1)
            mime.add_header('Content-Disposition', 'attachment', filename=att_name)
            mime.add_header('Content-ID', '<{}>'.format(cid))
            mime.add_header('X-Attachment-Id', cid)
            msg.attach(mime)
        else:  # 普通附件文件
            with open(attachment, 'rb') as fp:
                content = fp.read()
            if maintype == "text":
                att = MIMEText(content, _subtype=subtype, _charset=self.charset)
            elif maintype == "image":
                att = MIMEImage(content, _subtype=subtype)
            elif maintype == "audio":
                att = MIMEAudio(content, _subtype=subtype)
            else:
                att = MIMEBase(maintype, subtype)
                att.set_payload(content)
                email.encoders.encode_base64(att)

            att.add_header('Content-Type', 'application/octet-stream')
            att.add_header('Content-Disposition', 'attachment', filename=att_name)
            msg.attach(att)

        return msg

    def _set_attachments(self, msg=None):
        msg = msg or MIMEMultipart()
        for attachment in (self.attachments or []):
            self._attach_attachment(msg, attachment)
        return msg

    @property
    def _msg(self):
        msg = self._set_headers()
        msg.attach(MIMEText(
            self.content,
            _subtype=("html" if self.is_html else "plain"),
            _charset=self.charset)
        )  # 添加正文内容
        self._set_attachments(msg)  # 添加附件
        return msg

    def as_string(self):
        return self._msg.as_string()


class MailBox(object):
    """邮件收发"""

    def __init__(self, imap_host=None, smtp_host=None, username=None,
                 password=None, use_tls=False, use_ssl=False,
                 use_plain_auth=False, timeout=10, logger=None):
        self.imap_host = imap_host  # 接收服务器
        self.smtp_host = smtp_host  # 发送服务器

        self.username = username  # 邮箱账号
        self.password = password  # 邮箱密码

        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.use_plain_auth = use_plain_auth

        self.timeout = timeout

        self._imap = None

        if logger:
            self._log = logger
        else:
            log = logging.getLogger("kmailbox")
            log.addHandler(logging.NullHandler())
            log.propagate = False
            self._log = log

    def login(self, username, password):
        self.username = username
        self.password = password

        if not self.imap_host:
            return

        self._imap = imaplib.IMAP4_SSL(self.imap_host)
        typ, data = self._imap.login(self.username, self.password)
        if typ != 'OK':
            raise Exception(data)
        self._log.info("Sign as '%s'", data)

    def logout(self):
        self.username = None
        self.password = None

        if not self._imap:
            return

        typ, data = self._imap.logout()
        if typ != 'BYE':
            raise Exception(data)
        self._log.info("Sign as '%s'", data)

    def send(self, message=None, debug=False):
        if self.use_ssl:
            server = smtplib.SMTP_SSL(timeout=self.timeout)
        else:
            server = smtplib.SMTP(timeout=self.timeout)
        if debug:
            server.set_debuglevel(1)

        server.connect(self.smtp_host)

        if self.use_tls:
            server.ehlo()
            server.starttls()

        server.ehlo()
        if self.use_plain_auth is True:
                server.esmtp_features["auth"] = "LOGIN PLAIN"
        server.login(self.username, self.password)

        self._log.info("Sending email to %s", ", ".join(message.to_addrs))
        server.sendmail(message.sender, message.to_addrs, message.as_string())
        self._log.info("Send mail is successful")
        server.quit()

    def list(self):
        typ, data = self._imap.list()
        if typ != "OK":
            raise Exception(data)
        return data

    def select(self, box="INBOX"):
        typ, data = self._imap.select(box)
        if typ != "OK":
            raise Exception(data)
        return data

    def get_unread(self):
        typ, data = self._imap.capabilitiesearch(None, "Unseen")
        if typ != "OK":
            raise Exception(data)
        return [self.get_mail_message(num) for num in data[0].split(' ')]

    def get_mail_message(self, num):
        typ, data = self._imap.fetch(num, '(RFC822)')
        if typ != "OK":
            raise Exception(data)
        raw_mail = data[0][1]
        return email.message_from_string(raw_mail)

    def get_message_content(self, msg):
        pass

    def get_message_sender(self, msg):
        pass

    def get_message_recipient(self, msg):
        pass

    def get_message_subject(self, msg):
        email.Header.decode_header(msg['Subject'])[0][0]

    def get_message_attachments(self, msg):
        pass


if __name__ == '__main__':
    pass
