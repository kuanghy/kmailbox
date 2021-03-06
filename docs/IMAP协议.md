IMAP 协议简介
============

IMAP（Internet Message Access Protocol，因特网信息访问协议，也称作交互邮件访问协议）允许电子邮件客户端下载服务器上的邮件。与 POP3（Post Office Protocol，邮局协议）不同，IMAP 支持与邮件服务器进行双向通信，客户端的操作都会反馈到服务器上，对邮件进行的操作，服务器上的邮件也会做相应的动作（如移动、标记已读邮件等）。

客户端在发起命令操作时，每个命令需以一个标识作为前缀（典型的有字母、数字构成的短字符串，如：A0001，A0002，等等）――它称为“标签”。客户端需为每个命令生成不同的“标签”，同时服务区会返回相同的扁标签，以及响应内容。

可以通过 telnet 工具连接邮箱进行指令测试。如：

```
$ telnet imap.qq.com 143
> A0001 LOGIN laoww@163.com 123456
> A0002 SELECT INBOX
> A0003 UID SEARCH UNDELETED
> a0004 UID FETCH 3 (BODY.PEEK[HEADER])
```
