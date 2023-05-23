This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.


### Testing
The only notable thing about the test setup is that it uses a local test server (tests/fixtures/server.py) via [aiosmtpd](https://aiosmtpd.readthedocs.io/en/latest/), which has sort of replaced the old smtpd module. There is a DummyServer, which has an 'expect_email()' method that is used similarly to the [expect_events()](https://github.com/ghga-de/hexkit/blob/7382c19b84136ea5b1652087ba1da4890267b1b5/hexkit/providers/akafka/testutils.py#L368) method from hexkit's kafka testing module. It can perform simple a authentication check so error handling can be tested. When an email is sent to the test server, the connection is closed and the received/expected emails are compared to make sure that the header and body content is intact. This enables testing the flow of sending an email without actually issuing any real emails and without using real credentials.
