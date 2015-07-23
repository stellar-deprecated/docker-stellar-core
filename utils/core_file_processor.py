#!/usr/bin/env python

import logging
import sys
import ConfigParser
import os
import socket
import time
import subprocess
from string import Template
import textwrap
import boto.ses


def format_time(epoch_time):
    time_format = "%Y-%m-%dT%H:%M:%S"
    return time.strftime(time_format, time.gmtime(epoch_time))


class CoreMailer(object):
    def __init__(self, config):
        self.config = config
        self.hostname = self.config.get('Config', 'hostname')
        self.out = sys.stdout

    def find_core(self):
        path = self.config.get('Config', 'cores')
        core_filter = self.config.get('Config', 'core_filter')

        cores = [os.path.join(path, core) for core in os.listdir(path) if core_filter in core]

        if len(cores):
            return max(cores, key=os.path.getctime)

    def filter_logs(self, logs):
        log_filter = self.config.get('Config', 'log_filter')
        if not log_filter:
            return logs

        def strip_prefix(line):
            first_space = line.index(' ')
            following_colon = line.index(':', first_space)
            return line[0:first_space] + line[following_colon:]

        lines = logs.split("\n")
        filtered = filter(lambda line: log_filter in line, lines)
        stripped = map(strip_prefix, filtered)
        return "\n".join(stripped)

    def find_logs(self, epoch_time):
        log = self.config.get('Config', 'log')
        formatted_time = format_time(epoch_time)
        logging.info('Searching %s for logs around %s', log, formatted_time)
        command = ["egrep",
                   "-C1000",
                   ("^%s" % formatted_time),
                   log]
        try:
            return self.filter_logs(subprocess.check_output(command))
        except subprocess.CalledProcessError:
            return 'Unable to retrieve logs around %s' % formatted_time

    def get_trace(self, core):
        binary = self.config.get('Config', 'bin')
        logging.info('Processing core file %s with binary %s', core, binary)

        # matschaffer: this is really awful
        # But lldb just exits with no output and exit code -11 if I try to run
        # this script as a container entry point
        lldb_command = "lldb-3.6 -f %(binary)s -c %(core)s --batch " + \
                       "-o 'target create -c \"%(core)s\" \"%(binary)s\"' " + \
                       "-o 'script import time; time.sleep(1)' " + \
                       "-o 'thread backtrace all'"
        command = ["script", "-c",
                   (lldb_command % {"core": core, "binary": binary})]

        return subprocess.check_output(command, stderr=subprocess.STDOUT)

    def send_alert(self, epoch_time, trace, logs):
        template_vars = {
            "hostname": self.hostname,
            "binary": self.config.get('Config', 'bin'),
            "formatted_time": format_time(epoch_time),
            "trace": trace,
            "logs": logs
        }

        sender = self.config.get('Config', 'from')
        recipient = self.config.get('Config', 'to')

        subject = 'stellar-core crash on %(hostname)s' % template_vars
        template = textwrap.dedent("""
          <p>${binary} on ${hostname} crashed at ${formatted_time} with the
          following back traces:</p>

          <pre><code>
          ${trace}
          </code></pre>

          <h2>Extracted logs</h2>

          <pre><code>
          ${logs}
          </code></pre>
        """)
        body = Template(template).substitute(template_vars)

        logging.info("Sending core alert from %s to %s", sender, recipient)
        self.send_email(sender, recipient, subject, body)

    def send_email(self, sender, recipient, subject, body):
        conn = boto.ses.connect_to_region(self.config.get('Config', 'region'))
        # noinspection PyTypeChecker
        conn.send_email(sender, subject, None, [recipient], html_body=body)

    def output_trace(self, epoch_time, trace):
        template_vars = {
            "hostname": self.hostname,
            "binary": self.config.get('Config', 'bin'),
            "formatted_time": format_time(epoch_time),
            "trace": trace
        }

        template = textwrap.dedent("""
          ${binary} on ${hostname} crashed at ${formatted_time} with the
          following back traces:

          ${trace}
        """)
        body = Template(template).substitute(template_vars)
        self.out.write(body)

    def archive_core(self, core):
        command_string = self.config.get('Config', 'archive_command')
        if command_string:
            core_path = os.path.join(self.hostname, os.path.basename(core))
            command_string = command_string.format(core, core_path)
            logging.info(subprocess.check_output(command_string.split(' ')))
        else:
            logging.warn("No archive command, just removing core file")
        os.remove(core)

    def run(self, single_core):
        core = single_core or self.find_core()
        mode = self.config.get('Config', 'mode')

        if core:
            logging.info('Found core file %s', core)
            epoch_time = os.path.getctime(core)
            trace = self.get_trace(core)

            if mode == "aws":
                logs = self.find_logs(epoch_time)
                self.send_alert(epoch_time, trace, logs)
                self.archive_core(core)
            elif mode == "local":
                self.output_trace(epoch_time, trace)
            else:
                logging.fatal("Unknown MODE setting: %s", mode)
                sys.exit(1)
        else:
            logging.info('No core file found for processing')


if __name__ == "__main__":
    if len(sys.argv) > 1:
        single_core = sys.argv[1]
    else:
        single_core = None

    config_file = "/etc/core_file_processor.ini"

    logging.basicConfig(level=logging.INFO)

    config_parser = ConfigParser.ConfigParser({
        "region": "us-east-1",
        "cores": "/cores",
        "log": "/host/syslog",
        "log_filter": os.environ.get('CORE_LOG_FILTER'),
        "core_filter": "stellar-core",
        "hostname": socket.gethostname(),
        "from": "%(hostname)s <ops+%(hostname)s@stellar.org>",
        "to": os.environ.get('CORE_ALERT_RECIPIENT'),
        "bin": "/usr/local/bin/stellar-core",
        "archive_command": os.environ.get('CORE_ARCHIVE_COMMAND'),
        "mode": os.environ.get('MODE', 'aws')
    })

    config_parser.add_section("Config")
    config_parser.read(config_file)

    mailer = CoreMailer(config_parser)
    mailer.run(single_core)
