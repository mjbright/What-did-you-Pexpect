#!/usr/bin/env python3

'''This starts an SSH connection to a given host.

'''


import time
import sys
import os
import getpass
import inspect

import pexpect

#ssh_template = '/usr/bin/ssh -l {} {}'
#copy_id_template = '/usr/bin/ssh-copy-id -i {} {}@{}'
#scp_id_template = '/usr/bin/scp -i {} {} {}@{}:{}'

# Search in /bin, /usr/bin, /usr/local/bin just in case!
# pexpect.spawn() fails with this:
# ssh_template     = 'PATH=/bin:/usr/bin:/usr/local/bin ssh -l {} {}'
# copy_id_template = 'PATH=/bin:/usr/bin:/usr/local/bin ssh-copy-id -i {} {}@{}'
# scp_id_template  = 'PATH=/bin:/usr/bin:/usr/local/bin scp -i {} {} {}@{}:{}'

# Search in /bin, /usr/bin, /usr/local/bin just in case!
SHELL_PATH='/bin:/usr/bin/:/usr/local/bin'
SHELL_ENV={ 'PATH': SHELL_PATH }

SSH_OPTS=''

NO_HOST_CHECKS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

ssh_template     = 'ssh {} -l {} {}'
copy_id_template = 'ssh-copy-id {} -i {} {}@{}'
scp_id_template  = 'scp {} -i {} {} {}@{}:{}'

DEFAULT_TIMEOUT=None

CONST_INTERACT=1001
CONST_TIMEOUT=1002

ENCODING=None # Use bytes array
ENCODING='utf-8'
ENCODING='ascii'

KNOWN_HOSTS_PROMPT='Are you sure you want to continue connecting (yes/no)?'
KNOWN_HOSTS_REPLY='yes'

########################################
# Config:

host=None
user=None
password=None
cmd_list=[]

VERBOSE=0
DEBUG=0

#MATCH_PROMPT='HypriotOS: '
DEFAULT_MATCH_PROMPT=':~# '
# root@poc2kvm1:~#

########################################
# Functions:

def fatal(msg):
    print("FATAL error: " + msg)
    print()
    frame=inspect.currentframe()
    backframe=frame.f_back

    filename = inspect.getframeinfo(backframe).filename
    lineno = backframe.f_lineno

    print("-- called from {} at line {} of {}".format( backframe.f_code.co_name, lineno, filename ))

def debug(level, msg):
    if VERBOSE >= level:
        print(msg)

def scp( host, user, password, src_file, dst ):

    timeout=DEFAULT_TIMEOUT
    debug(1, "scp {} -> {}@{}:{}".format(src_file, host, user, dst))

    try:
        debug(1, "Copying to host " + host)
        command = scp_id_template.format(SSH_OPTS, key_file, src_file, user, host, dst)

        debug(1, "Command='" + command + "'")
        ssh_child = pexpect.spawn( command, timeout=timeout, env=SHELL_ENV )
        if DEBUG > 0:
            ssh_child.logfile = sys.stdout

        if password:
            send_password(ssh_child, password, timeout)

        ssh_child.expect(pexpect.EOF)

    except Exception as e:
        print("Exception = <<<\n" + str(e) + "\n    >>>")

def copy_key( host, user, password, key_file):

    timeout=DEFAULT_TIMEOUT
    debug(1, "Copy_id {} -> {}@{}/{}".format(key_file, host, user, password))
    try:
        debug(1, "Coying to host " + host)
        command = copy_id_template.format(SSH_OPTS, key_file, user, host)

        debug(1, "Command='" + command + "'")
        ssh_child = pexpect.spawn( command, timeout=timeout, env=SHELL_ENV )
        if DEBUG > 0:
            ssh_child.logfile = sys.stdout

        if password:
            send_password(ssh_child, password, timeout)

        ssh_child.expect(pexpect.EOF)

    except Exception as e:
        print("Exception = <<<\n" + str(e) + "\n    >>>")


def send_password(ssh_child, password, timeout, known_hosts_prompt_seen=False):
    debug(1, "Waiting for password prompt[timeout={}] ....".format(timeout))

    idx = ssh_child.expect(['[Pp]assword:', KNOWN_HOSTS_PROMPT, pexpect.EOF, pexpect.TIMEOUT], timeout=timeout)
    if idx == 0:
        op = ssh_child.before
        #BAD: op = ssh_child.read()
        #BAD: op = ssh_child.readline()
        #print("OP=" + str(op) )
        print( str(op) )
        debug(1, "Got it .... password prompt ....")
        debug(1, "Sending password ...")


        ## CHANGED to use send() rather than sendline() as setecho doesn't work on sendline(), see here:
        ##    http://stackoverflow.com/questions/13464759/pexpect-setecho-not-working

        ssh_child.delaybeforesend = 1
        ssh_child.setecho(False)

        ssh_child.send(password + os.linesep)

        ssh_child.delaybeforesend = 0
        ssh_child.setecho(True)

    elif idx == 1:
        debug(1, "Got 'known hosts prompt'")
        debug(1, "Sending yes/no reply [{}] ..." + KNOWN_HOSTS_REPLY)
        if known_hosts_prompt_seen:
            fatal("Not accepting prompt when 'known_hosts_prompt_seen' already set")

        ssh_child.sendline(KNOWN_HOSTS_REPLY)

        # Call send_password again, but fail (call fatal()) if same prompt seen:
        send_password(ssh_child, password, timeout, known_hosts_prompt_seen=True)

    elif idx == 2:
        fatal("-- Received EOF")

    elif idx == 3:
        fatal("-- Received TIMEOUT")

    else:
        fatal("-- Received unexpected MATCH")


def ssh( host, user, password, cmd_list ):

    timeout=DEFAULT_TIMEOUT
    debug(1, "Cnxn {}@{}/{}".format( host, user, password ))

    try:
        debug(1, "Connecting to host " + host)
        command = ssh_template.format(SSH_OPTS, user, host)

        debug(1, "Command='" + command + "'")

        # NOTE: use of optional encoding argument:
        ssh_child = pexpect.spawn( command, timeout=timeout, env=SHELL_ENV )
        if DEBUG > 0:
            ssh_child.logfile = sys.stdout

        timeout=DEFAULT_TIMEOUT
        MATCH_PROMPT=DEFAULT_MATCH_PROMPT

        if password:
            send_password(ssh_child, password, timeout)

        #time.sleep(0.1)
        ssh_child.expect(MATCH_PROMPT, timeout=timeout)
        debug(1, "Got prompt")

        for cmd in cmd_list:
            print("CMD=" + cmd)
            if cmd == CONST_INTERACT:
                debug(1, "INTERACT")
                #ssh_child.expect(MATCH_PROMPT, timeout=timeout)
                debug(1, "Got prompt")

                print("")
                print("Entering interactive mode ...")
                print("  -- Press <enter> to start")
                print("  -- Enter 'quit'  to end")

                ssh_child.interact()
                MATCH_PROMPT=DEFAULT_MATCH_PROMPT
                print("Setting prompt back to " + MATCH_PROMPT)

            # If starts with '-' assume a timeout value (make +ve first!)
            elif cmd[0] == '-':
                timeout=-cmd

            else:
                debug(1, cmd)

                #ssh_child.send(cmd + '\n')
                ssh_child.sendline(cmd)

                if cmd == "quit":
                    MATCH_PROMPT=DEFAULT_MATCH_PROMPT

                if cmd == "sys":
                    MATCH_PROMPT='\\[' + DEFAULT_MATCH_PROMPT[1:]

                # LOCAL!! (i.e. not across ssh connection) op = pexpect.run(cmd)

                # NOTE: we can pass alist of regex matches, and also EOF, TIMEOUT values:
                idx = -1
	        MATCH_MORE_PROMPT = '---- More ----'
                while idx != 0:
                    idx = ssh_child.expect([ MATCH_PROMPT, MATCH_MORE_PROMPT, pexpect.EOF, pexpect.TIMEOUT ], timeout=timeout)
                    if idx == 0:
                        op = ssh_child.before
                        print( str(op) )
                    elif idx == 1:
                        op = ssh_child.before
                        print( str(op) )
                        ssh_child.sendline(' ')
                        continue
                    elif idx == 2:
                        fatal("-- Received EOF")
                    elif idx == 3:
                        fatal("-- Received TIMEOUT")
                    else:
                        fatal("-- Received unexpected MATCH")

                # Note: we can't spawn commands here as we've already done a spawn
                # child = ssh_child.spawn(cmd)
                # child.logfile_read = sys.stdout
                # child.expect(pexpect.EOF)
                timeout=DEFAULT_TIMEOUT

        #uptime = pexpect.run('uptime')
        #print(uptime)

        #time.sleep(60) # Cygwin is slow to update process status.
        #ssh_child.expect(pexpect.EOF)

    except Exception as e:
        print("Exception = <<<\n" + str(e) + "\n    >>>")

    #print("Forcing exit")
    #sys.exit(0)

def main():
    ssh( host, user, password, cmd_list )


########################################
# Args:

## # using get will return `None` if a key is not present rather than raise a `KeyError`
## print os.environ.get('HOME')
## 
## # os.getenv is equivalent, and can also give a default value instead of `None`
## print os.getenv('HOME', default_value)
## 


SSHPY_TIMEOUT = int(os.getenv('SSHPY_TIMEOUT', 0))
if SSHPY_TIMEOUT == 0:
    SSHPY_TIMEOUT = None

VERBOSE       = int( os.getenv('SSHPY_VERBOSE', VERBOSE) )
DEBUG         = int( os.getenv('SSHPY_DEBUG', DEBUG) )

if DEBUG != 0:
    print("DEBUG=" + str(DEBUG))

if VERBOSE != 0:
    print("VERBOSE=" + str(VERBOSE))
    if SSHPY_TIMEOUT != None:
        print("SSHPY_TIMEOUT=" + str(SSHPY_TIMEOUT))

if SSHPY_TIMEOUT != None:
    DEFAULT_TIMEOUT=SSHPY_TIMEOUT

a=0
while a < (len(sys.argv)-1):
    a += 1

    if VERBOSE >= 3:
        #print(a)
        print("sys.argv[{}]={}".format(a,sys.argv[a]))

    if sys.argv[a] == '-d':
        DEBUG += 1
        continue

    if sys.argv[a] == '-v':
        VERBOSE += 1
        continue

    if sys.argv[a] == '--PROMPT':
        a += 1; DEFAULT_MATCH_PROMPT = sys.argv[a]
        continue

    if sys.argv[a] == '-h':
        a += 1; host = sys.argv[a]
        continue

    if sys.argv[a] == '-u':
        a += 1; user = sys.argv[a]
        continue

    if sys.argv[a] == '-p':
        a += 1; password = sys.argv[a]
        continue

    if sys.argv[a] == '-c':
        a += 1; cmd = sys.argv[a]
        cmd_list.append(cmd)
        print("OK")
        continue

    if sys.argv[a] == '-to':
        a += 1; timeout = sys.argv[a]
        cmd_list.append(-timeout)
        continue

    if sys.argv[a] == '-no-host-checks' or sys.argv[a] == '-nhc':
        SSH_OPTS += NO_HOST_CHECKS
        continue

    if sys.argv[a] == '-int':
        cmd_list.append(CONST_INTERACT)
        continue

    if sys.argv[a] == '-i':
        a += 1; key_file = sys.argv[a]
        continue

    if sys.argv[a] == '--copy-id':
        copy_key( host, user, password, key_file=key_file )
        password = None
        copy_id = False
        continue

    if sys.argv[a] == '--scp':
        a += 1; key_file = sys.argv[a]
        a += 1; src_file = sys.argv[a]
        a += 1; dst      = sys.argv[a]
        scp( host, user, password, src_file, dst )

    fatal("Unknown arg#[{}] <{}>".format(a, sys.argv[a]))

########################################
# Main:

if VERBOSE != 0:
    print("VERBOSE=" + str(VERBOSE))
    if DEFAULT_TIMEOUT != None:
        print("DEFAULT_TIMEOUT=" + str(DEFAULT_TIMEOUT))

if __name__ == '__main__':
    main()


