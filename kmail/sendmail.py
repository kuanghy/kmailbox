#! /usr/bin/env python
# -*- coding: utf-8 -*-

# *************************************************************
#     Filename @  sendmail.py
#       Author @  Huoty
#  Create date @  2015-07-05 09:25:55
#  Description @  邮件发送
# *************************************************************

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


def set_debug_level(self, debug=True, logfile=sys.stdout):
    logging.basicConfig(
        level = logging.NOTSET if debug else logging.ERROR,
        format = '%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s',
        datefmt = '%x %X',
        stream = logfile,
        filemode = 'a'
    )

class SendMail(object):
    '''发送邮件'''

    def __init__(self, mail_host):
        '''初始化邮件发送所必须的配置变量, 参数 mail_host 为邮件服务器主机地址
        '''
        self.mail_host = mail_host  # 邮件服务器主机地址,支持直接加端口号,例如 "smtp.XXX.com:25"
        self.mail_user = ""    # 邮箱用户名，仅用户名，例如 Huoty
        self.mail_passwd = ""  # 邮箱登录密码
        self.mail_sender = ""  # 邮件发送者，支持两种：
                               # 一种直接是邮箱地址，例如 sudohuoty@163.com;
                               # 另一种是带发送者昵称的，例如 huoty<sudohuoty@163.com>
        self.mail_tolist = ""  # 邮件接受者列表，支持群发
        self.mail_msg = MIMEMultipart()  # 要发送的邮件信息，包括文本和附件



    def set_sender(self, sender, passwd, tolist):
        '''设置发件人姓名和邮箱地址，邮箱密码，和收件人列表。
        sender可以是单纯的邮箱地址，例如 sudohuoty@163.com；
        也可以是带发送者姓名的邮件地址，例如 Huoty<sudohuoty@163.com>。
        tolist为收件人列表, 如果为群发, 则用列表或元组包含多个收件地址。
        '''
        logging.info("Setting the sender information ...")
        logging.debug(str("Sender is " + sender))

        # 提取邮箱用户名
        reg_result = re.search("([a-z0-9_\.-]+)@([\da-z\.-]+)\.([a-z\.]{2,6})", sender)
        if reg_result:
            self.mail_user = reg_result.group(1)
        else:
            logging.error("The email address of sender is a incorrect format!")
            return False

        logging.debug(str("Mail user is " + self.mail_user))

        self.mail_passwd = passwd
        self.mail_sender = sender
        self.mail_tolist = tolist

        return True

    def set_content(self, subject, content, charset = "utf-8", attachments = None):
        '''设置邮件内容：
            subject：邮件主题
            content：邮件文本内容
            charset：邮件内容的编码方式
            attachment：附件列表
        当邮件类型为 html 和 misc 时才需要传递 attachment 参数。当邮件类型为 misc，且文本内容为 html 形式，并包含媒体内容，则在 attachment 中传递媒体资源时，应将其加 “cid + 编号：” 前缀，例如 “cid0：/home/konghy/temp/psb.jpg”
        '''
        logging.info("Setting the mail content ...")

        self.mail_msg['Subject'] = subject
        self.mail_msg['From'] = self.mail_sender
        self.mail_msg['To'] = ";".join(self.mail_tolist)
        self.mail_msg['Date'] = time.strftime("%Y-%m-%d", time.localtime())

        # initialize attachments
        if attachments is None:
            attachments = []

        is_html = re.search("<body>.*</body>", content, re.S)
        subtype = "html" if is_html else "plain"
        self.mail_msg.attach(MIMEText(content, _subtype = subtype, _charset = charset))
        logging.debug("Mail subtype: " + subtype)

        try:
            for attachment in attachments:
                html_media = re.search("^cid(\d+):(.+)$", attachment)

                att_path = html_media.group(2) if html_media else attachment
                ctype, encoding = mimetypes.guess_type(att_path)
                if ctype is None or encoding is not None:
                    # No guess could be made, or the file is encoded (compressed), so
                    # use a generic bag-of-bits type.
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

                    mime.add_header('Content-Disposition', 'attachment', filename = os.path.basename(attachment))
                    mime.add_header('Content-ID', '<' + html_media.group(1) + '>')
                    mime.add_header('X-Attachment-Id', html_media.group(1))
                    self.mail_msg.attach(mime)
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
                    att.add_header('Content-Disposition', 'attachment', filename = os.path.basename(attachment))
                    self.mail_msg.attach(att)
        except Exception, e:
            logging.error(e)
            return False
        else:
            #logging.debug(self.mail_msg.as_string())
            return True

    def startup(self):
        '''连接邮件服务器,并发送邮件'''

        logging.info("Sending mail ...")

        try:
            server = smtplib.SMTP()
            if debug: server.set_debuglevel(1)
            server.connect(self.mail_host)
            server.ehlo()
            server.starttls()
            server.login(self.mail_user, self.mail_passwd)
            server.sendmail(self.mail_sender, self.mail_tolist, self.mail_msg.as_string())
            server.close()
        except Exception, e:
            logging.debug("Failed to send mail: " + e)
            return False
        else:
            logging.info("Send the email is successful")
            return True

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
