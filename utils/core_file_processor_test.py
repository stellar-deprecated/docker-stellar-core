from nose.tools import assert_equals

from core_file_processor import CoreMailer

import textwrap
import ConfigParser

def mailer(options):
    defaults = {
        "hostname": "unittests"
    }
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
    config = { "log_filter": "b60e5fc489e2" }
    assert_equals(mailer(config).filter_logs(logs), expected_logs)
