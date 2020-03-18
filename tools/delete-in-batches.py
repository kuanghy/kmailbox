#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Huoty, All rights reserved
# Author: Huoty <sudohuoty@163.com>
# CreateTime: 2020-03-16 22:00:38

import os
import logging
from kmailbox import MailBox


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    box = MailBox(
        imap_host=os.getenv("KMAILBOX_IMAP_HOST"),
        smtp_host=os.getenv("KMAILBOX_SMTP_HOST"),
        logger=logging.getLogger("kmailbox"),
    )
    box.login(os.environ["KMAILBOX_USER"], os.environ["KMAILBOX_PASSWD"])
    box.select()
    id_list = box._search('FROM "{}"'.format("kuanghuayong@joinquant.com"))
    uid_list = box.fetch_uids(id_list)
    box.mark_as_delete(uid_list)
    box.expunge()
    box.logout()


if __name__ == "__main__":
    main()
