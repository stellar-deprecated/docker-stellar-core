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

class CoreMailer(object):
    def __init__(self, config):
        self.config = config
        self.hostname = self.config.get('Config', 'hostname')

    def format_time(self, epoch_time):
        time_format = "%Y-%m-%dT%H:%M:%S"
        return time.strftime(time_format, time.gmtime(epoch_time))

    def find_core(self):
        path = self.config.get('Config', 'cores')
        cores = [os.path.join(path, core) for core in os.listdir(path)]
        if len(cores):
          return max(cores, key=os.path.getctime)

    def find_logs(self, epoch_time):
        log = self.config.get('Config', 'log')
        formatted_time = self.format_time(epoch_time)
        logging.info('Searching %s for logs around %s', log, formatted_time)
        command = ["egrep",
                   "-C50",
                   ("^%s" % formatted_time),
                   log]
        try:
            return subprocess.check_output(command)
        except subprocess.CalledProcessError:
            return 'Unable to retrieve logs around %s' % formatted_time

    def get_trace(self, core):
        binary = self.config.get('Config', 'bin')
        logging.info('Processing core file %s with binary %s', core, binary)
        command = ["lldb-3.6",
                   "-f", binary,
                   "-c", core,
                   "--batch",
                   "-o", ("target create -c '%s' '%s'" % (core, binary)),
                   "-o", "script import time; time.sleep(1)",
                   "-o", "thread backtrace all"]
        return subprocess.check_output(command, stderr=subprocess.STDOUT)

    def send_alert(self, epoch_time, trace, logs):
        template_vars = {
            "hostname": self.hostname,
            "binary": self.config.get('Config', 'bin'),
            "formatted_time": self.format_time(epoch_time),
            "trace": trace,
            "logs": logs
        }

        sender = self.config.get('Config', 'from')
        recipient = self.config.get('Config', 'to')

        subject = 'stellar-core crash on %(hostname)s' % template_vars
        template = textwrap.dedent("""
          <p>${binary} on ${hostname} crashed at ${formatted_time} with the
          following backtraces:</p>

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
        conn = boto.ses.connect_to_region(self.config.get('Config', 'region'))
        conn.send_email(sender, subject, None, [recipient], html_body=body)

    def archive_core(self, core):
        command_string = self.config.get('Config', 'archive_command')
        if command_string:
            core_path = os.path.join(self.hostname, os.path.basename(core))
            command_string = command_string.format(core, core_path)
            logging.info(subprocess.check_output(command_string.split(' ')))
        else:
            logging.warn("No archive command, just removing core file")
        os.remove(core)

    def run(self):
        core = self.find_core()
        if core:
            logging.info('Found core file %s', core)
            epoch_time = os.path.getctime(core)
            logs = self.find_logs(epoch_time)
            trace = self.get_trace(core)
            self.send_alert(epoch_time, trace, logs)
            self.archive_core(core)
        else:
            logging.info('No core file found for processing')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "/etc/coremailer.ini"

    logging.basicConfig(level=logging.INFO)

    config = ConfigParser.ConfigParser({
        "region": "us-east-1",
        "cores": "/cores",
        "log": "/logs/host/syslog",
        "hostname": socket.gethostname(),
        "from": "%(hostname)s <ops+%(hostname)s@stellar.org>",
        "to": os.environ.get('CORE_ALERT_RECIPIENT'),
        "bin": "/usr/local/bin/stellar-core",
        "archive_command": os.environ.get('CORE_ARCHIVE_COMMAND')
    })
    config.add_section("Config")
    config.read(config_file)

    mailer = CoreMailer(config)
    mailer.run()
