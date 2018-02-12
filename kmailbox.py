#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2018-02-12 17:30:04

import os
import sys
import re
import time
import getopt
import getpass
import mimetypes
import smtplib
import logging
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Message(object):

    def __init__(self, sender=None, recipient=None, subject=None, content=None,
                 is_html=False, attachments=None, charset="utf-8"):
        self.sender = sender         # 发件人
        self.recipient = recipient   # 收件人，多人时为 list 等序列类型
        self.subject = subject       # 邮件主题
        self.content = content       # 邮件内容
        self.is_html = is_html       # 是否为 html 内容的邮件
        self.attachments = attachments  # 附件
        self.charset = charset       # 邮件编码

    @property
    def _msg(self):
        if isinstance(self.recipient, (list, tuple, set)):
            recipient = ";".join(self.recipient)
        else:
            recipient = self.recipient

        subtype = "html" if self.is_html else "plain"

        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['From'] = self.sender
        msg['To'] = recipient
        msg['Date'] = time.strftime("%Y-%m-%d", time.localtime())

        msg.attach(MIMEText(self.content, _subtype=subtype, _charset=self.charset))

        # 添加附件
        attachments = self.attachments or []
        for attachment in attachments:
            html_media = re.search("^cid(\d+):(.+)$", attachment)

            att_path = html_media.group(2) if html_media else attachment
            ctype, encoding = mimetypes.guess_type(att_path)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            if html_media:  # 判断是否为 html 中包含的媒体
                fp = open(html_media.group(2), 'rb')
                if maintype == "image":
                    mime = MIMEImage(fp.read(), _subtype=subtype)
                elif maintype == "audio":
                    mime = MIMEAudio(fp.read(), _subtype=subtype)
                else:
                    fp.close()
                    raise Exception("Undefined attachment type of html media!")
                fp.close()

                mime.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment))
                mime.add_header('Content-ID', '<' + html_media.group(1) + '>')
                mime.add_header('X-Attachment-Id', html_media.group(1))
                msg.attach(mime)
            else:  # 普通附件文件
                fp = open(attachment, 'rb')
                if maintype == "text":
                    att = MIMEText(fp.read(), _subtype=subtype)
                elif maintype == "image":
                    att = MIMEImage(fp.read(), _subtype=subtype)
                elif maintype == "audio":
                    att = MIMEAudio(fp.read(), _subtype=subtype)
                else:
                    att = MIMEBase(maintype, subtype)
                    att.set_payload(fp.read())
                    encoders.encode_base64(att)
                fp.close()

                att.add_header('Content-Type', 'application/octet-stream')
                att.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment))
                msg.attach(att)

        return msg

    def as_string(self):
        return self._msg.as_string()


class MailBox(object):
    '''发送邮件'''

    def __init__(self, imap_host=None, smtp_host=None):
        self.imap_host = imap_host  # 接收服务器
        self.smtp_host = smtp_host  # 发送服务器

        self.username = None  # 邮箱账号
        self.password = None  # 邮箱密码

    def login(self, username, password):
        self.username = username
        self.password = password

        if not self.imap_host:
            return

    def logout(self):
        pass

    def sendmail(self, message=None):
        server = smtplib.SMTP()
        server.connect(self.smtp_host)
        server.ehlo()
        server.starttls()
        server.login(self.username, self.password)
        log.info("Sending email...")
        server.sendmail(message.sender, message.recipient, message.as_string())
        log.info("Send mail is successful")
        server.close()

    def list(self):
        pass


# Script starts from here

def _usage():
    print u'''
Usage: sendmail command

sendmail is a simple command line for sending email.

Commands:
    h | --help        Show usage
    v | --version     Show version
'''

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hv", ["help", "version"])
    except getopt.GetoptError:
        print "Invalid option!"

    if opts:
        for o, a in opts:
            if o in ("-h", "--help"):
                _usage()
                sys.exit()

            if o in ("-v", "--version"):
                print u"Sendmail version: sendmail/1.0 (all platforms)"
                print u"Sendmail built:   2015-07-07"
                print u"Sendmail author:  huoty"
                sys.exit()
    else:
        print "Please enter the following information:"
        mailserver = raw_input("Email server: ")
        mailsender = raw_input("Email sender: ")
        mailpassed = getpass.getpass("Emial passwd: ")

        receivers = raw_input("To list: ").split(",")
        mailtolist = [ receiver.strip() for receiver in receivers ]
        print str(mailtolist)

        mailsubject = raw_input("Email subject: ")

        print "Email content: "
        mailcontent = ""
        while True:
            strline = raw_input()
            if strline.strip() == ">>>end":
                break
            else:
                mailcontent += strline + "\n"

        atts = raw_input("Email attachments: ").split(",")
        mailattachments = [ att.strip() for att in atts ]
        print mailattachments

        print "\n"
        mail = SendMail(mailserver)
        mail.set_sender(mailsender, mailpassed, mailtolist)
        mail.set_content(mailsubject, mailcontent.strip(), attachments = mailattachments)
        mail.startup()
