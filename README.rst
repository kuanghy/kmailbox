KMailBox
========

**kmailbox** is a python email library, support for sending and receiving emails via SMTP and IMAP protocol。

send plain text email:

.. code-block:: python

    from kmailbox import Message, MailBox

    msg = Message()
    msg.sender = "Tester<test@google.com>"
    msg.recipient = "hello@google.com"
    msg.subject = "kmailbox test"
    msg.content = "This is test"

    mailbox = MailBox(smtp_host="smtp.gmail.com", use_tls=True)
    mailbox.username = "username"
    mailbox.password = "password"
    mailbox.send(msg)

send html email:

.. code-block:: python

    msg = Message()
    msg.sender = "Tester<test@google.com>"
    msg.recipient = "hello@google.com"
    msg.subject = "kmailbox test send html and add attachments"
    msg.is_html = True
    msg.content = """\
    <body>
    <p><img src="cid:0"></p>

    <p>Hello! I am <em>Huoty</em>.</p>

    <p>How are you?</p>

    <p>Give you a picture:</p>
    <p><img src="cid:1"></p>
    </body>
    """
    msg.attachments = [
        "cid0:imgs/mailbox-icon.png",
        "cid1:imgs/20171005170550.jpg",
        "kmailbox.py",
        "README.md"
    ]

    mailbox = MailBox(
        smtp_host="smtp.gmail.com",
        use_ssl=True,
        username="username"
        password="password"
    )
    mailbox.send(msg)

receive mails:

.. code-block:: python

    mailbox = MailBox(imap_host="imap.gmail.com", use_ssl=True)
    mailbox.username = "username"
    mailbox.password = "password"
    mailbox.select()
    for mail mailbox.all(mark_seen=False, gen=True)
        pprint({
            "uid": mail.uid,
            "sender": mail.sender,
            "to_addrs": mail.to_addrs,
            "subject": mail.subject,
            "date": str(mail.date),
            "flags": mail.flags,
            "attachments": [att.filename for att in mail.attachments],
        })
    mailbox.logout()
