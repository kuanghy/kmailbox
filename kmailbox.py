# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>

from __future__ import print_function

import os
import sys
import re
import base64
import logging
import binascii
import datetime
import functools
from collections import namedtuple

import imaplib
import smtplib
import mimetypes
import email
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from email.header import Header as EmailHeader
from email.utils import (
    getaddresses as get_email_addr,
    formatdate as format_email_date,
    parseaddr as parse_email_addr,
    formataddr as format_email_addr,
)

try:
    from collections import UserString
except ImportError:
    from UserString import UserString


__version__ = "0.2.3"

if sys.version_info.major > 2:
    string_types = str
    binary_types = bytes
else:
    string_types = basestring  # noqa
    binary_types = str

if 'ID' not in imaplib.Commands:
    imaplib.Commands['ID'] = ('AUTH', 'NONAUTH')


DEFAULT_IMAP_HOST_MAPPING = {
    "gmail.com": "imap.gmail.com",
    "outlook.com": "outlook.office365.com",
    "qq.com": "imap.qq.com",
    "foxmail.com": "imap.qq.com",
    "163.com": "imap.163.com",
    "yeah.net": "imap.yeah.net",
    "139.com": "imap.139.com",
}

DEFAULT_SMTP_HOST_MAPPING = {
    "gmail.com": "smtp.gmail.com",
    "outlook.com": "smtp.office365.com:587",
    "qq.com": "smtp.qq.com",
    "foxmail.com": "smtp.qq.com",
    "163.com": "smtp.163.com",
    "yeah.net": "smtp.yeah.net",
    "139.com": "smtp.139.com",
}


def _get_default_imap_host(email_address):
    if not email_address:
        return
    match = re.match(r".+@(.+)", email_address)
    if not match:
        return
    email_domain = match.group(1)
    return DEFAULT_IMAP_HOST_MAPPING.get(email_domain)


def _get_default_smtp_host(email_address):
    if not email_address:
        return
    match = re.match(r".+@(.+)", email_address)
    if not match:
        return
    email_domain = match.group(1)
    return DEFAULT_SMTP_HOST_MAPPING.get(email_domain)


def _decode_string(data, encoding="uft-8"):
    if isinstance(data, binary_types):
        try:
            return data.decode(encoding or 'utf-8', 'ignore')
        except LookupError:
            return data.decode('utf-8', 'ignore')
    return data


def _shorten_text(text, width=60, placeholder="..."):
    return (text[:width] + placeholder) if len(text) > width else text


def _shorten_sequence_string(sequence, max_len=3, placeholder="..."):
    return ", ".join(
        [
            "{!r}".format(item) for item in list(sequence)[:max_len]
        ] + ([placeholder] if len(sequence) > max_len else [])
    )


def _decode_email_header(header):
    data, encoding = decode_header(header)[0]
    return _decode_string(data, encoding)


class UnexpectedCommandStatusError(Exception):
    """命令执行返回的状态错误"""


class imap_utf7(object):
    """IMAP 协议中的 UTF7 字符串编解码，按照 RFC 3501 实现

    参考自：https://github.com/ikvk/imap_tools/blob/master/imap_tools/folder.py
    """

    @staticmethod
    def _modified_base64(data):
        return binascii.b2a_base64(
            data.encode('utf-16be')
        ).rstrip(b'\n=').replace(b'/', b',')

    @classmethod
    def encode(cls, data):
        res = []
        _in = []

        def _do_b64():
            if _in:
                res.append(b'&' + cls._modified_base64(''.join(_in)) + b'-')
            del _in[:]

        for c in data:
            ord_c = ord(c)
            if 0x20 <= ord_c <= 0x25 or 0x27 <= ord_c <= 0x7e:
                _do_b64()
                res.append(c.encode())
            elif c == '&':
                _do_b64()
                res.append(b'&-')
            else:
                _in.append(c)
        _do_b64()
        return b''.join(res)

    @staticmethod
    def _modified_unbase64(data):
        return binascii.a2b_base64(
            data.replace(b',', b'/') + b'==='
        ).decode('utf-16be')

    @classmethod
    def decode(cls, data):
        res = []
        decode_arr = bytearray()
        for c in data:
            if c == ord('&') and not decode_arr:
                decode_arr.append(ord('&'))
            elif c == ord('-') and decode_arr:
                if len(decode_arr) == 1:
                    res.append('&')
                else:
                    res.append(cls._modified_unbase64(decode_arr[1:]))
                decode_arr = bytearray()
            elif decode_arr:
                decode_arr.append(c)
            else:
                res.append(chr(c))
        if decode_arr:
            res.append(cls._modified_unbase64(decode_arr[1:]))
        return ''.join(res)


class MailFolder(namedtuple("MailFolder", "name flags delim")):
    """邮箱目录

    name: str - folder name
    flags: str - folder flags
    delim: str - delimitor
    """


class MailFlag(object):
    """基本邮件标志"""

    SEEN = 'SEEN'          # 邮件已读
    ANSWERED = 'ANSWERED'  # 邮件已回复
    FLAGGED = 'FLAGGED'    # 邮件标记为紧急或者特别注意
    DELETED = 'DELETED'    # 邮件为删除状态
    DRAFT = 'DRAFT'        # 邮件未写完（标记为草稿状态）
    RECENT = 'RECENT'      # 邮件最近到达该邮箱（本次会话是首次收到当前邮件通知）


class MailAddress(UserString):
    """邮件地址"""

    _addr_pattern = r"(.*)<(.*@.*)>"

    def __init__(self, address, name=None):
        match = re.match(self._addr_pattern, address)
        if match:
            self.name, self.address = match.groups()
            self.data = address
        else:
            self.address = address
            self.name = name
            if name:
                self.data = '{}<{}>'.format(name, address)
            else:
                self.data = address


class MailAttachment(object):
    """邮件附件"""

    def __init__(self, part):
        self._part = part

        self._filename = None
        self._payload = None

    @property
    def filename(self):
        if self._filename is None:
            filename = self._part.get_filename()
            self._filename = _decode_email_header(filename).strip()
        return self._filename

    @property
    def content_type(self):
        return self._part.get_content_type()

    def _get_payload(self):
        payload = self._part.get_payload(decode=True)
        if payload:
            return payload
        # multipart payload, such as .eml (see get_payload)
        multipart_payload = self._part.get_payload()
        if isinstance(multipart_payload, list):
            for payload_item in multipart_payload:
                if hasattr(payload_item, 'as_bytes'):
                    payload_item_bytes = payload_item.as_bytes()
                    encoding = self._part.get('content-transfer-encoding', '')
                    cte = str(encoding).lower().strip()
                    if payload_item_bytes and cte:
                        if cte == 'base64':
                            return base64.b64decode(payload_item_bytes)
                        elif cte in ('7bit', '8bit', 'quoted-printable', 'binary'):
                            return payload_item_bytes  # quopri.decodestring
        # could not find payload
        return b''

    @property
    def payload(self):
        if self._payload is None:
            self._payload = self._get_payload()
        return self._payload

    def download(self, directory=None, filename=None):
        if not filename:
            filename = self.filename
        path = os.path.join(directory, filename) if directory else filename
        with open(path, "wb") as fp:
            fp.write(self.payload)


class MessageProperty(object):
    """邮件属性描述符

    在 Message 对象没有设置属性的时候，尝试从其 _msg 对象中获取相应的值并做转化
    """

    # 收件人字段与 Message 对象 Key 的对应关系
    _recipient_mapping = {
        'recipient': 'To',
        'cc_recipient': 'CC',
        'bcc_recipient': 'BCC',
        'reply_recipient': 'Reply-To'
    }

    def __init__(self, name, default=None):
        self.name = name
        self.default = default

    def _decode_header(self, header):
        data, encoding = decode_header(header)[0]
        return _decode_string(data, encoding)

    def _parse_addr(self, data):
        result = []
        if isinstance(data, EmailHeader):
            result.append(MailAddress(_decode_email_header(data.encode())))
        elif data:
            for raw_name, address in get_email_addr([data]):
                try:
                    name = _decode_email_header(raw_name).strip()
                except Exception:
                    name = raw_name
                try:
                    address = _decode_email_header(address).strip()
                except Exception:
                    address = address
                if not address:
                    continue
                result.append(MailAddress(address, name))
        return tuple(result)

    @staticmethod
    def _fetch_date(obj):
        value = obj._msg.get('Date')
        if not value:
            value = obj._msg.get('Received', '')
        short_month_names = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', "Dec")
        match = re.search((
            r'(?P<date>\d{1,2}\s+(' + '|'.join(short_month_names) +
            r')\s+\d{4})\s+' +
            r'(?P<time>\d{1,2}:\d{1,2}(:\d{1,2})?)\s*' +
            r'(?P<zone_sign>[+-])?(?P<zone>\d{4})?'
        ), value)
        if match:
            group = match.groupdict()
            day, month, year = group['date'].split()
            time_values = group['time'].split(':')
            zone_sign = int('{}1'.format(group.get('zone_sign') or '+'))
            zone = group['zone']
            return datetime.datetime(
                year=int(year),
                month=short_month_names.index(month) + 1,
                day=int(day),
                hour=int(time_values[0]),
                minute=int(time_values[1]),
                second=int(time_values[2]) if len(time_values) > 2 else 0,
                tzinfo=datetime.timezone(datetime.timedelta(
                    hours=int(zone[:2]) * zone_sign,
                    minutes=int(zone[2:]) * zone_sign
                )) if zone else None,
            )
        else:
            return datetime.datetime.min

    @staticmethod
    def _fetch_content(obj):
        for part in obj._msg.walk():
            if part.is_multipart():
                continue
            content_type = part.get_content_type()
            if content_type not in ('text/plain', 'text/html', 'text/'):
                continue
            text = part.get_payload(decode=True)
            charset = part.get_content_charset()
            return _decode_string(text, charset)
        return ''

    @staticmethod
    def _fetch_attachments(obj):
        results = []
        for part in obj._msg.walk():
            if part.is_multipart():
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            if not filename:
                continue  # this is what happens when Content-Disposition = inline
            results.append(MailAttachment(part))
        return results

    def __get__(self, obj, type=None):
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        elif not obj._msg:
            return self.default
        else:
            if self.name == "sender":
                name = 'From'
                sender = self._parse_addr(obj._msg.get(name, self.default))[0]
                obj.__dict__[self.name] = sender
                return sender
            elif self.name == "subject":
                name = self.name.title()
                subject = _decode_email_header(obj._msg.get(name, self.default))
                obj.__dict__[self.name] = subject
                return subject
            elif self.name == "date":
                date = self._fetch_date(obj)
                obj.__dict__[self.name] = date
                return date
            elif self.name == "content":
                content = self._fetch_content(obj)
                obj.__dict__[self.name] = content
                return content
            elif self.name == "attachments":
                attachments = self._fetch_attachments(obj)
                obj.__dict__[self.name] = attachments
                return attachments
            elif self.name in self._recipient_mapping:
                name = self._recipient_mapping[self.name]
                recipient = self._parse_addr(obj._msg.get(name, self.default))
                obj.__dict__[self.name] = recipient
                return recipient
            else:
                return obj._msg.get(self.name.title(), self.default)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value


class Message(object):
    """邮件消息

    用于构建将要发送的消息或者解析接收到的消息
    """

    # 发件人
    sender = MessageProperty("sender")
    # 收件人，多人时为 list 等序列类型
    recipient = MessageProperty("recipient")
    # 抄送人(Carbon Copy)
    cc_recipient = MessageProperty("cc_recipient")
    # 暗抄送人(Blind Carbon Copy)
    bcc_recipient = MessageProperty("bcc_recipient")
    # 回复收件人
    reply_recipient = MessageProperty("reply_recipient")
    # 邮件主题
    subject = MessageProperty("subject")
    # 邮件日期
    date = MessageProperty("date")
    # 邮件内容
    content = MessageProperty("content")
    # 附件
    attachments = MessageProperty("attachments")

    def __init__(self, **kwargs):
        self.is_html = kwargs.pop("is_html", False)    # 是否为 html 内容邮件
        self.headers = kwargs.pop("headers", None)     # 邮件头
        self.charset = kwargs.pop("charset", "utf-8")  # 邮件编码

        # 标记是否为接收到的消息，否则为即将要发送的消息
        # 接收的消息与要发送的消息某些字段值的类型可能会不同
        self.is_received = kwargs.pop("is_received", False)

        # 为接受到的消息时会设置的属性
        self.uid = kwargs.pop("uid", None)      # 邮件唯一标识符
        self.flags = kwargs.pop("flags", None)  # 邮件标记

        for name, value in kwargs.items():
            setattr(self, name, value)

        # 底层消息对象，为 email.message.Message 或其子类的对象
        # 用于在解析接收到的邮件消息时记录原始的二进制消息数据
        self._msg = None

    def __repr__(self):
        return "{}(subject={!r}, sender={!r}, date='{}', content={!r})".format(
            self.__class__.__name__,
            _shorten_text(self.subject, 30),
            self.sender,
            self.date,
            _shorten_text(self.content, 50),
        )

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

    def __format_email_addr(self, addr):
        realname, email_address = parse_email_addr(addr)
        realname = EmailHeader(realname, self.charset).encode()
        return format_email_addr((realname, email_address))

    def __set_headers(self, msg=None):
        msg = msg or MIMEMultipart()
        msg['Date'] = format_email_date(localtime=True)
        msg['Subject'] = EmailHeader(self.subject, self.charset).encode()
        msg['From'] = self.__format_email_addr(self.sender)

        recipient_mapping = {
            "To": self.recipient,
            "CC": self.cc_recipient,
            "BCC": self.bcc_recipient,
            "Reply-To": self.reply_recipient,
        }
        for hname, recp in recipient_mapping.items():
            if not recp:
                continue
            if isinstance(recp, string_types):
                msg[hname] = self.__format_email_addr(recp)
            else:
                msg[hname] = "; ".join([
                    self.__format_email_addr(addr) for addr in recp
                ])

        if self.headers:
            for key, value in self.headers.items():
                msg[key] = EmailHeader(value, self.charset).encode()

        return msg

    def __attach_attachment(self, msg, attachment):
        html_media = re.search(R"^cid(\d+):(.+)$", attachment)

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

    def __set_attachments(self, msg=None):
        msg = msg or MIMEMultipart()
        for attachment in (self.attachments or []):
            self.__attach_attachment(msg, attachment)
        return msg

    def as_string(self):
        if self._msg:                    # 为接收到的邮件消息
            return self._msg.as_string()
        elif not self.is_received:       # 为要发送的邮件消息
            msg = self.__set_headers()   # 设置邮件头信息
            msg.attach(MIMEText(
                self.content,
                _subtype=("html" if self.is_html else "plain"),
                _charset=self.charset
            ))                           # 添加正文内容
            self.__set_attachments(msg)  # 添加附件
            self._msg = msg
            return msg.as_string()
        else:
            return None

    def from_string(self, data):
        self._msg = email.message_from_string(data)
        return self

    def from_bytes(self, data):
        self._msg = email.message_from_bytes(data)
        return self

    def uid_from_string(self, data):
        if isinstance(data, binary_types):
            data = data.decode("utf-8")
        uid_match = re.search(r'UID\s+(?P<uid>\d+)', data)
        if uid_match:
            # zimbra, yandex, gmail, gmx
            uid = uid_match.group('uid')
        else:
            # mail.ru, ms exchange server
            re_pattern = r'(^|\s+)UID\s+(?P<uid>\d+)($|\s+)'
            for raw_flag_item in data:
                uid_flag_match = re.search(
                    re_pattern, _decode_string(raw_flag_item)
                )
                if uid_flag_match:
                    uid = uid_flag_match.group('uid')
        self.uid = uid
        return uid

    def flag_from_string(self, data_set):
        result = []
        for raw_flag_item in data_set:
            if isinstance(raw_flag_item, string_types):
                raw_flag_item = raw_flag_item.encode("utf-8")
            result.extend(imaplib.ParseFlags(raw_flag_item))
        flags = tuple(
            item.decode().strip().replace('\\', '').upper() for item in result
        )
        self.flags = flags
        return flags

    def from_raw_message_data(self, data):
        # 提取邮件的标识标记、消息体部分
        raw_message_data = b''
        raw_uid_or_flag_data = []
        for item in data:
            if isinstance(item, (tuple, list)):
                item = list(item)
                if not raw_message_data:
                    try:
                        raw_message_data = item.pop(1)
                    except IndexError:
                        pass
                raw_uid_or_flag_data.extend(item)
            else:
                raw_uid_or_flag_data.append(item)

        # 分别解析邮件的标识、标记、消息体部分
        if isinstance(raw_message_data, str):
            self.from_string(raw_message_data)
        else:
            self.from_bytes(raw_message_data)
        try:
            raw_uid_or_flag_data = b' '.join(raw_uid_or_flag_data)
        except TypeError:
            raw_uid_or_flag_data = ' '.join(raw_uid_or_flag_data)
        try:
            self.uid_from_string(raw_uid_or_flag_data)
            self.flag_from_string([raw_uid_or_flag_data])
        except Exception:
            print("-" * 120)
            print(data)
            print("-" * 120)
        return self


class MailBox(object):
    """邮件收发器"""

    def __init__(self,
                 username=None, password=None,
                 imap_host=None, smtp_host=None,
                 use_tls=False, use_ssl=False,
                 timeout=60, logger=None, debug=False):
        self.username = username or os.getenv("KMAILBOX_USERNAME")
        self.password = password or os.getenv("KMAILBOX_PASSWORD")

        self._imap_host = imap_host or os.getenv("KMAILBOX_IMAP_HOST")
        self._smtp_host = smtp_host or os.getenv("KMAILBOX_SMTP_HOST")

        self.use_tls = use_tls
        self.use_ssl = use_ssl

        self.timeout = timeout

        self._smtp_server = None
        self._imap_server = None

        if not logger:
            logger = logging.getLogger("kmailbox")
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
        self._log = self.logger = logger

        self.debug = debug

    @property
    def imap_host(self):
        host = self._imap_host or _get_default_imap_host(self.username)
        if not host:
            return None

        if ':' in host:
            host, port = host.rsplit(':', 1)
            port = int(port)
        else:
            port = imaplib.IMAP4_SSL_PORT if self.use_ssl else imaplib.IMAP4_PORT
        return host, port

    @property
    def smtp_host(self):
        host = self._smtp_host or _get_default_smtp_host(self.username)
        if not host:
            return None

        if ':' in host:
            host, port = host.rsplit(':', 1)
            port = int(port)
        else:
            port = smtplib.SMTP_SSL_PORT if self.use_ssl else smtplib.SMTP_PORT
        return host, port

    @property
    def imap_server(self):
        if not self._imap_server and self.imap_host:
            if self.use_ssl:
                server = imaplib.IMAP4_SSL(*self.imap_host)
            else:
                server = imaplib.IMAP4(*self.imap_host)
            if self.debug:
                server.debug = 1
            self._log.debug("Using '%s' login to %s",
                            self.username, self.imap_host)
            res = server.login(self.username, self.password)
            self._check_command_response(res, command="login")
            self._imap_server = server
            self.declare_identity()
        return self._imap_server

    @property
    def smtp_server(self):
        if not self._smtp_server and self.smtp_host:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(*self.smtp_host, timeout=self.timeout)
            else:
                server = smtplib.SMTP(*self.smtp_host, timeout=self.timeout)
            if self.debug:
                server.set_debuglevel(1)
            self._log.debug("Using '%s' login to %s",
                            self.username, self.smtp_host)
            server.connect(*self.smtp_host)
            server.ehlo()
            if not self.use_ssl and self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            self._smtp_server = server
        return self._smtp_server

    def _check_command_response(self, response, expected='OK', command=None):
        """校验命令的返回结果状态"""
        typ, data = response[0], response[1]
        if typ == expected:
            if command:
                self._log.info("%s was successful, sign as '%s'",
                               command.upper(), typ)
            return data
        err_str = "Unexpected response status '{}', data: {}".format(typ, data)
        if command:
            err_str += ", command: {}".format(command)
        raise UnexpectedCommandStatusError(err_str)

    def _close_smtp_server(self):
        if not self._smtp_server:
            return
        self._smtp_server.quit()
        self._smtp_server = None

    def _close_imap_server(self):
        if not self._imap_server:
            return
        self._imap_server.close()
        res = self._imap_server.logout()
        self._check_command_response(res, expected="BYE", command="logout")
        self._imap_server = None

    def close(self):
        self._close_smtp_server()
        self._close_imap_server()
        self._username = None
        self._password = None

    def send(self, message, after_reset_connect=False):
        if not message.sender:
            message.sender = self.username
        self._log.info("Sending email to %s", message.to_addrs)
        self.smtp_server.sendmail(message.sender, message.to_addrs, message.as_string())
        self._log.info("Send mail is successful")
        if after_reset_connect:
            self._close_smtp_server()

    def _imap_command(self, command, *args, **kwargs):
        """封装 IMAP4 对象的命令方法"""
        cmd_func = getattr(self.imap_server, command, None)
        if not cmd_func:
            cmd_func = functools.partial(
                self.imap_server._simple_command, command.upper()
            )
        res = cmd_func(*args, **kwargs)
        data = self._check_command_response(res, command=command)
        return data

    def declare_identity(self, name="kmailbox", version=__version__,
                         vendor="kmailbox"):
        client_id = '("name" "{}" "version" "{}" "vendor" "{}")'.format(
            name, version, vendor
        )
        return self._imap_command("ID", client_id)

    @property
    def folders(self):
        data = self._imap_command("list")
        re_pattern = re.compile(
            R'\((?P<flags>[\S ]*)\) "(?P<delim>[\S ]+)" (?P<name>.+)'
        )

        def _parse_folder_item(item):
            folder_match = re.search(re_pattern, imap_utf7.decode(item))
            folder = folder_match.groupdict()
            name = folder['name']
            if name.startswith('"') and name.endswith('"'):
                folder['name'] = name[1:len(name) - 1]
            return MailFolder(**folder)

        return [_parse_folder_item(item) for item in data if item]

    @staticmethod
    def _encode_folder(name):
        """对目录名做 UTF7 编码"""
        if not isinstance(name, binary_types):
            name = imap_utf7.encode(name)
        name = name.replace(b'\\', b'\\\\').replace(b'"', b'\\"')
        return b'"' + name + b'"'

    def select(self, box="INBOX", readonly=False):
        self._log.info("Selecting mail folder '%s'", box)
        self._imap_command("select", self._encode_folder(box), readonly)

    def _search(self, *criterions, **kwargs):
        """搜索邮件

        常用 criterion 字段：
            ALL：所有邮件
            ANSWERED：已回复的邮件
            BODY <string>：在邮件的主体域包含有指定字符串的邮件
            CC <string>：在信封结构的抄送人域包含有指定字符串的邮件
            DELETED：已删除的邮件
            DRAFT：草稿邮件
            FLAGGED：被标记的邮件
            FROM <string>：在信封结构的发件人域包含有指定字符串的邮件
            KEYWORD <flag>：带有指定关键词标记位的邮件
            NEW：新邮件，在功能上等效于“(RECENT UNSEEN)”
            NOT <search-key>：不符合指定检索关键词的邮件
            OLD：旧邮件，在功能上等效于“NOT RECENT”（与“NOT NEW”相反）
            ON <date>：实际日期（忽视时间和时区）在指定日期的邮件
            OR <search-key1> <search-key2>：符合任意一个检索关键词的邮件
            RECENT：最近到达的邮件
            SEEN：已读邮件
            SUBJECT <string>：在信封结构的标题域含有指定字符串的邮件
            TEXT <string>：在邮件的头部或者主体含有指定字符串的邮件
            TO <string>：在信封结构的收件人域含有指定字符串的邮件
            UNANSWERED：未回复的邮件
            UNDELETED：未删除的邮件
            UNDRAFT：不带有 /Draft 标记位的邮件
            UNFLAGGED：未被标记的邮件
            UNKEYWORD <flag>：不带有指定关键词标记位的邮件
            UNSEEN：未读邮件

        Criterion 示例，获取未读且标题中带 hello 的邮件："(UNSEEN SUBJECT 'hello')"

        另外可传递关键参数 charset 来指定编码格式
        """

        if not criterions:
            criterions = ["ALL"]
        charset = kwargs.get("charset", None)
        self._log.info("Using criterion %s search mails", criterions)
        data = self._imap_command('search', charset, *criterions)
        if isinstance(data[0], binary_types):
            mail_list = data[0].decode("utf-8").split()
        else:
            mail_list = data[0].split()
        return mail_list

    def fetch_messages(self, msg_set, mark_seen=True, gen=False):
        """使用 RFC822 电子邮件的标准格式下载邮件

        当 message_part 使用 RFC822 时功能上等同于 BODY[]
        注意 BODY[] 的形式会隐含 /Seen 标记，如不希望如此，可以使用 BODY.PEEK[] 代替
        其不会暗自设置 /Seen 标记
        """
        msg_parts = ("(BODY[] UID FLAGS)" if mark_seen
                     else "(BODY.PEEK[] UID FLAGS)")
        msg_gen = (Message(is_received=True).from_raw_message_data(
            self._imap_command('fetch', num, msg_parts)
        ) for num in msg_set)
        return msg_gen if gen else list(msg_gen)

    def fetch_uids(self, msg_set, gen=False):
        """获取邮件的唯一标识"""
        uid_gen = (Message(is_received=True).uid_from_string(
            self._imap_command('fetch', num, "UID")[0]
        ) for num in msg_set)
        return uid_gen if gen else list(uid_gen)

    def all(self, mark_seen=True, gen=False):
        return self.fetch_messages(self._search("ALL"), mark_seen, gen)

    def unread(self, mark_seen=True, gen=False):
        return self.fetch_messages(self._search("UNSEEN"), mark_seen, gen)

    def recent(self, mark_seen=True, gen=False):
        return self.fetch_messages(self._search("RECENT"), mark_seen, gen)

    def new(self, mark_seen=True, gen=False):
        return self.fetch_messages(self._search("NEW"), mark_seen, gen)

    def old(self, mark_seen=True, gen=False):
        return self.fetch_messages(self._search("OLD"), mark_seen, gen)

    def from_criteria(self, criteria, mark_seen=True, gen=False):
        """按发件人搜索邮件"""
        return self.fetch_messages(
            self._search('FROM "{}"'.format(criteria)), mark_seen, gen
        )

    @staticmethod
    def _clean_uid_set(uid_set):
        """转换 uid 集合

        Uid 集合可以是: 字符串(可以逗号分隔)，可迭代的对象
        """
        if isinstance(uid_set, string_types):
            uid_set = uid_set.split(',')
        try:
            uid_set_iter = iter(uid_set)
        except TypeError:
            raise ValueError('Wrong uid type: "{}"'.format(type(uid_set)))

        uid_list = []
        for uid in uid_set_iter:
            if not isinstance(uid, string_types):
                try:
                    uid = uid.uid
                except AttributeError:
                    raise ValueError('Wrong uid: "{}"'.format(uid))
            uid = uid.strip()
            if not uid.isdigit():
                raise ValueError('Wrong uid: "{}"'.format(uid))
            uid_list.append(uid)
        return ','.join((item for item in uid_list))

    def flag(self, uid_set, flag_set, value):
        """设置或者取消设置邮件标志

        参数 value 值为 True 时表示设置标志，否则为取消
        """
        uid_str = self._clean_uid_set(uid_set)
        if not uid_str:
            return None
        if isinstance(flag_set, string_types):
            flag_set = [flag_set]
        store_result = self.imap_server.uid(
            'STORE', uid_str, ('+' if value else '-') + 'FLAGS',
            '({})'.format(' '.join(('\\' + item for item in flag_set)))
        )
        self._log.info("Falg %s (value=%r) for %s",
                       flag_set, value, _shorten_text(uid_str))
        data = self._check_command_response(store_result)
        return data

    def expunge(self):
        """将邮箱中所有打了删除标记的邮件彻底删除"""
        return self._imap_command("expunge")

    def mark_as_delete(self, uid_set):
        """标记邮件为删除"""
        return self.flag(uid_set, MailFlag.DELETED, True)

    def mark_as_seen(self, uid_set):
        """标记邮件为已读"""
        return self.flag(uid_set, MailFlag.SEEN, True)

    def mark_as_unseen(self, uid_set):
        """标记邮件为未读"""
        return self.flag(uid_set, MailFlag.SEEN, False)

    def move(self, to_folder, criterions=None, on_condition_what=None):
        """移动邮件到指定目录"""
        if on_condition_what and not callable(on_condition_what):
            raise Exception("on_condition_what must be a callable object")
        if criterions:
            msgs = self.fetch_messages(
                self._search(criterions), mark_seen=False, gen=True
            )
        else:
            msgs = self.new(mark_seen=False, gen=True)
        for msg in msgs:
            if on_condition_what and not on_condition_what(msg):
                continue
            self.imap_server.copy(msg.uid, imap_utf7.encode(to_folder))
            self.mark_as_delete(msg.uid)
            self._log.info("Move %s to %s", msg, to_folder)

    def relay(self, to_addrs, criterions=None, on_condition_what=None):
        """邮件转发"""
        if on_condition_what and not callable(on_condition_what):
            raise Exception("on_condition_what must be a callable object")
        if criterions:
            msgs = self.fetch_messages(
                self._search(criterions), mark_seen=False, gen=True
            )
        else:
            msgs = self.new(mark_seen=False, gen=True)
        for msg in msgs:
            if on_condition_what and not on_condition_what(msg):
                continue
            self.smtp_server.sendmail(self.username, to_addrs, msg.as_string())
            self._log.info("Relay %s to %s", msg, to_addrs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()


def _main():
    from argparse import ArgumentParser

    def create_argument(parser, *args, **kwargs):
        parser.add_argument(*args, **kwargs)

    parser = ArgumentParser(
        description="Email tool by python (use smtp and imap protocol)"
    )
    parser._optionals.title = "help arguments"
    create_argument(parser, "-v", "--version", action='version',
                    version=__version__)
    create_argument(parser, "-d", "--debug", action="store_true",
                    help="Enable debug mode")
    create_argument(parser, "--loglevel",
                    choices=["debug", "info", "warning", "error", "fatal",
                             "critical"],
                    help="Set log level and enbale logger")

    basic_group = parser.add_argument_group(title="basic arguments")
    create_argument(basic_group, "--imap", help="Email IMAP server")
    create_argument(basic_group, "--smtp", help="Email SMTP server")
    create_argument(basic_group, "-u", "--user",
                    help="Email user")
    create_argument(basic_group, "-p", "--password",
                    help="Email user's password")
    create_argument(basic_group, "--use-tls", action="store_true",
                    help="Using TLS connect to server")
    create_argument(basic_group, "--use-ssl", action="store_true",
                    help="Using SSL connect to server")
    create_argument(basic_group, "--timeout", type=int, default=30,
                    help="Timeout, default: 30")
    create_argument(basic_group, "--select", default="INBOX",
                    help="Select a mailbox folder, default: INBOX")
    create_argument(basic_group, "--list", action="store_true",
                    help="List mailbox folder names")

    send_group = parser.add_argument_group(title="send arguments")
    create_argument(send_group, "--send", action="store_true", help="Send Mail")
    create_argument(send_group, "-f", "--sender", help="Mail From")
    create_argument(send_group, "-t", "--to", nargs="+", help="Recipients")
    create_argument(send_group, "--cc", nargs="*", help="Carbon Copy recipients")
    create_argument(send_group, "-s", "--subject", help="Mail subject")
    create_argument(send_group, "-c", "--content", help="Mail Content")
    create_argument(send_group, "-a", "--attachment", nargs="*",
                    help="Mail attachments")

    read_group = parser.add_argument_group(title="read arguments")
    create_argument(read_group, "--all", action="store_true",
                    help="Read all mails")
    create_argument(read_group, "--unread", action="store_true",
                    help="Read unread mails")
    create_argument(read_group, "--recent", action="store_true",
                    help="Read recent mails")
    create_argument(read_group, "--new", action="store_true",
                    help="Read new mails")
    create_argument(read_group, "--old", action="store_true",
                    help="Read old mails")
    create_argument(read_group, "--verbose", action="store_true",
                    help="verbosely display mail message")
    create_argument(read_group, "--mark-as-seen", action="store_true",
                    help="Mark as seen after read the mail")

    mark_group = parser.add_argument_group(title="mark arguments")
    create_argument(mark_group, "--delete", action="store_true",
                    help="Delete mails")
    create_argument(mark_group, "--seen", action="store_true",
                    help="Mark mails as seen")
    create_argument(mark_group, "--unseen", action="store_true",
                    help="Mark mails as unseen")
    create_argument(mark_group, "--uid", nargs="+",
                    help="Mail id set, e.g. 1,2,3")

    relay_group = parser.add_argument_group(title="relay arguments")
    create_argument(relay_group, "--relay-to", nargs="*",
                    help="Relay mails to other addresses")

    args = parser.parse_args()

    username = args.user or os.getenv("KMAILBOX_USERNAME")
    password = args.password or os.getenv("KMAILBOX_PASSWORD")
    if not (username and password):
        parser.error(
            "the following arguments are required: -u/--user, -p/--password"
        )
    imap_host = args.imap
    if not imap_host and not args.send:
        imap_host = _get_default_imap_host(username)
        if not imap_host:
            parser.error("argument --imap are required")
    if args.loglevel:
        logger = logging.getLogger("kmailbox")
        loglevel = getattr(logging, args.loglevel.upper())
        logger.setLevel(loglevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(loglevel)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        logger.propagate = False
    else:
        logger = None
    box = MailBox(
        imap_host=imap_host,
        smtp_host=args.smtp,
        username=username,
        password=password,
        use_tls=args.use_tls,
        use_ssl=args.use_ssl,
        timeout=args.timeout,
        logger=logger,
        debug=args.debug,
    )
    if args.send and not box.smtp_host:
        parser.error("argument --smtp are required")
    if not args.list and not args.send:
        box.select(args.select)

    def send_mail():
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        box.logger = logging.getLogger("test")
        msg = Message()
        msg.sender = args.sender
        msg.recipient = args.to
        msg.cc_recipient = args.cc
        msg.attachments = args.attachment
        msg.content = args.content or sys.stdin.read()
        msg.subject = args.subject or _shorten_text(msg.content, 50)
        box.send(msg)
        print("Send mail '{}' to {} done".format(
            _shorten_text(msg.subject, 60),
            _shorten_sequence_string(msg.to_addrs)
        ))

    def display_mails(fetch_func):
        for mail in fetch_func(mark_seen=args.mark_as_seen, gen=True):
            print("========", _shorten_text(mail.subject, 60), "========")
            print("Sender:", mail.sender)
            print("Date:", mail.date)
            print("Recipient:", ", ".join([str(rec) for rec in mail.recipient]))
            if mail.cc_recipient:
                print("CC-Recipient:", ", ".join([
                    str(rec) for rec in mail.cc_recipient
                ]))
            if mail.bcc_recipient:
                print("BCC-Recipient:", ", ".join([
                    str(rec) for rec in mail.bcc_recipient
                ]))
            if mail.reply_recipient:
                print("Reply-Recipient:", ", ".join([
                    str(rec) for rec in mail.reply_recipient
                ]))
            print("UID:", mail.uid, "  ", "Flags:", ", ".join(mail.flags))
            print("Attachments:", mail.attachments)
            if args.verbose:
                print("Content:")
                print(mail.content)
            print()

    if args.list:
        for folder in box.folders:
            print(folder.name, folder.flags, folder.delim)
    elif args.send:
        send_mail()
    elif args.all:
        display_mails(box.all)
    elif args.unread:
        display_mails(box.unread)
    elif args.recent:
        display_mails(box.recent)
    elif args.new:
        display_mails(box.new)
    elif args.old:
        display_mails(box.old)
    elif args.delete:
        box.mark_as_delete(args.uid)
        print("Mark {} as delete done.".format(_shorten_sequence_string(args.uid)))
    elif args.seen:
        box.mark_as_seen(args.uid)
        print("Mark {} as seen done.".format(_shorten_sequence_string(args.uid)))
    elif args.unseen:
        box.mark_as_unseen(args.uid)
        print("Mark {} as unseen done.".format(_shorten_sequence_string(args.uid)))
    elif args.relay_to:
        box.relay(args.relay_to)
    else:
        parser.print_usage(sys.stderr)


if __name__ == '__main__':
    _main()
