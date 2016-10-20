#! /usr/bin/env python
# -*- coding: utf-8 -*-

# *************************************************************
#     Filename @  test_sendmail.pysw
#       Author @  Huoty
#  Create date @  2016-04-06 09:59:09
#  Description @
# *************************************************************

import pytest

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sendmail
from sendmail import SendMail

# Script starts from here

def test_sendmail():
    #sendmail.debug = False

    content = '''\
<body>
Hello!

<p><img src="cid:0"></p>
I am Huoty.

How are you?

Give you a picture:
<p><img src="cid:1"></p>
</body>
'''

    tolist = ["sudohuoty@163.com", "1346632121@qq.com"]
    attachments = ["cid0:/home/huoty/temp/kk.png", "cid1:/home/huoty/temp/khy.jpg", "/home/huoty/temp/test.png", "/home/huoty/temp/test.pdf", "/home/huoty/temp/test.py", "/home/huoty/temp/new1.txt", "/home/huoty/temp/gcolor2.tar.gz"]
    mail = SendMail("smtp.yeah.net")
    mail.set_debug_level(debug=False)
    assert True == mail.set_sender("konitor@yeah.net", "YQfvomHHHhqd9q9H", tolist)
    assert True == mail.set_content("Test to send email by python", content, attachments=attachments)
    assert True == mail.startup()
