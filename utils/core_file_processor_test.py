from nose.tools import assert_equals, assert_regexp_matches

from core_file_processor import CoreMailer

import textwrap
import ConfigParser
from StringIO import StringIO

def create_mailer(options=None):
    defaults = {
        "cores": "fakecoredir",
        "log": "fakelogfile",
        "hostname": "unittests",
        "bin": "/usr/local/bin/stellar-core",
        "from": "ops+unittests@stellar.org",
        "to": "mat@stellar.org",
        "region": "us-east-1"
    }
    if options:
        defaults.update(options)
    config = ConfigParser.ConfigParser(defaults)
    config.add_section("Config")
    core_mailer = CoreMailer(config)
    return core_mailer


def test_log_filtering():
    logs = textwrap.dedent("""
      2015-06-16T21:07:04.007435+00:00 core-delivery-001.stg.stellar001.internal.stellar-ops.com docker/b60e5fc489e2[29424]: terminate called after throwing an instance of 'std::runtime_error'
      2015-06-16T21:07:04.007836+00:00 core-delivery-001.stg.stellar001.internal.stellar-ops.com docker/b60e5fc489e2[29424]:   what():  baseCheckDecode decoded to <5 bytes
      2015-06-16T21:07:04.010012+00:00 core-delivery-001.stg.stellar001.internal.stellar-ops.com docker/b60e5fc489e2[29424]: /start: line 29:    28 Aborted                 (core dumped) stellar-core --newdb
      2015-06-16T21:07:04.622539+00:00 core-delivery-001.stg.stellar001.internal.stellar-ops.com kernel: [1542072.767438] docker0: port 1(vethdd214d1) entered disabled state
    """)
    expected_logs = textwrap.dedent("""
      2015-06-16T21:07:04.007435+00:00: terminate called after throwing an instance of 'std::runtime_error'
      2015-06-16T21:07:04.007836+00:00:   what():  baseCheckDecode decoded to <5 bytes
      2015-06-16T21:07:04.010012+00:00: /start: line 29:    28 Aborted                 (core dumped) stellar-core --newdb
    """).strip()
    mailer = create_mailer({"log_filter": "b60e5fc489e2"})
    assert_equals(mailer.filter_logs(logs), expected_logs)

def test_local_mode():
    mailer = create_mailer({"mode": "local"})
    mailer.find_core = lambda: __file__
    mailer.get_trace = lambda _: "some traces"
    mailer.out = StringIO()
    mailer.run()
    assert_regexp_matches(mailer.out.getvalue(), "some traces")

def test_aws_mode():
    captures = {}

    def capture_output(sender, recipient, subject, body):
        captures["sender"] = sender
        captures["recipient"] = recipient
        captures["subject"] = subject
        captures["body"] = body

    mailer = create_mailer({"mode": "aws"})

    mailer.find_core = lambda: __file__
    mailer.find_logs = lambda _: "some logs"
    mailer.archive_core = lambda _: None
    mailer.get_trace = lambda _: "some traces"
    mailer.send_email = capture_output

    mailer.run()
    assert_regexp_matches(captures["subject"], "crash")
    assert_regexp_matches(captures["body"], "some traces")
