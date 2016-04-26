#!/usr/bin/env python3


'''This starts an SSH connection to a given host.

'''


import time
import sys
import os
import getpass
import inspect

import json

import pexpect

#copy_id_template = '/usr/bin/ssh-copy-id -i {} {}@{}'
#scp_id_template = '/usr/bin/scp -i {} {} {}@{}:{}'

# Search in /bin, /usr/bin, /usr/local/bin just in case!
# pexpect.spawn() fails with this:
# copy_id_template = 'PATH=/bin:/usr/bin:/usr/local/bin ssh-copy-id -i {} {}@{}'
# scp_id_template  = 'PATH=/bin:/usr/bin:/usr/local/bin scp -i {} {} {}@{}:{}'

# Search in /bin, /usr/bin, /usr/local/bin just in case!
SHELL_PATH='/bin:/usr/bin/:/usr/local/bin'
SHELL_ENV={ 'PATH': SHELL_PATH }

SSH_OPTS=''

NO_HOST_CHECKS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

ssh_key_template     = 'ssh {} -i {} -l {} {}'
ssh_template     = 'ssh {} -l {} {}'
copy_id_template = 'ssh-copy-id {} -i {} {}@{}'
scp_id_template  = 'scp {} -i {} {} {}@{}:{}'

DEFAULT_TIMEOUT=None
DEFAULT_COMMANDS=[]

CONST_INTERACT=1001
CONST_TIMEOUT=1002

CONST_PASSWORDLESS_LOGIN="__NO_PASSWORD__"
#CONST_COMMAND_INSTALL_KEY='[ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q {} .ssh/authorized_keys || { echo "Adding key"; echo {} >> .ssh/authorized_keys; }'
CONST_COMMAND_INSTALL_KEY_ARG='__INSTALL_KEY__'
#CONST_COMMAND_INSTALL_KEY='ls -altr .ssh; [ ! -d .ssh ] && {{ echo "Creating dir .ssh"; mkdir .ssh; }}; grep -q "{}" .ssh/authorized_keys || {{ echo "Adding key"; echo "{}" >> .ssh/authorized_keys; }}; ls -al $PWD/.ssh/authorized_keys'
#CONST_COMMAND_INSTALL_KEY='echo WOOHOO-$USER-$(hostname); ls -altr .ssh; [ ! -d .ssh ] && {{ echo "Creating dir .ssh"; mkdir .ssh; }}; grep -q "{}" .ssh/authorized_keys || {{ echo "Adding key"; echo "{}" >> .ssh/authorized_keys; }}; ls -al .ssh/; wc .ssh/authorized_keys'
#CONST_COMMAND_INSTALL_KEY='echo WOOHOO-$USER-$(hostname)'
CONST_COMMAND_INSTALL_KEY='echo ${{USER}}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && {{ echo "Creating dir .ssh"; mkdir .ssh; }}; grep -q "{}" .ssh/authorized_keys || {{ echo "Adding key"; echo "{}" >> .ssh/authorized_keys; }}; ls -al .ssh/; wc .ssh/authorized_keys'

CONST_COMMAND_SUDO_ARG='__SUDO__'
#CONST_COMMAND_SUDO='echo "/usr/bin/sudo -i"'
CONST_COMMAND_SUDO='sudo -i'
#CONST_COMMAND_SUDO='which sudo; sudo -i'

def readjson(ipfile):
    f = open(ipfile)

    #ip = f.readlines()
    #ips = ''.join(ip)

    # Read lines, skipping comment lines:
    ips = ''
    debug_ips = ''
    lineno = 0
    for line in f.readlines():
        lineno += 1
        strippedline = line.strip()
        debug_ips += str(lineno) + ": "
        if len(strippedline) != 0 and strippedline[0] != '#':
            #ips += line +os.linesep
            #debug_ips += line +os.linesep
            ips += line
            debug_ips += line
        else:
            ips += os.linesep # Keep line numbering the same
            debug_ips += line
            #debug_ips += os.linesep # Keep line numbering the same

    print("json_str i/p: <" + debug_ips +">")

    ## # serialize json-object (ips) to json-formatted str:
    ## js = json.dumps(ips)
    ## print("json i/p: <" + js +">")
     
    # de-serialize string (ips) to a json-object:
    js = json.loads(ips)
    t = type(js)
    print("TYPEOF json i/p: " + str(type(js)))

    # Return as a list of json objects:
    print("json i/p: <" + str(js) +">")
    if isinstance(js, list):
        print("json i/p LIST")
        return js

    if isinstance(js, dict):
        print("json i/p keys: <" + str(js.keys()) +">")
        return [ js ]

    fatal("Unknown type found")

def getUserHost(route_login):
    if not "@" in route_login:
        fatal("Expect '@' in route_login")

    atPos = route_login.find("@")
    if atPos == -1:
        fatal("Expected route to <user@hostSpec> - not found in <" + route_login + ">")
    endUser = route_login[ : atPos ]
    endHost = route_login[ atPos+1 : ]

    return (endUser, endHost)

def findRouteTo2(node0, routeEnd, jsonNodes):
    if not isinstance(jsonNodes, list):
        fatal("Expected list")

    hosts={}
    addrs={}
    revAddrs={}
    routesTo={}
    sudoRoutesTo={}

    for node in jsonNodes:
         if not 'name' in node:
             fatal("Missing name for node")

         name=node['name']
         if 'host' in node and node['host'] != "":
             hosts[name] = node['host']
             #print("ADDING hosts[{}]={}".format(name, node['host']))
         if 'addr' in node and node['addr'] != "":
             addrs[name] = node['addr']
             print("ADDING addrs[{}]={}".format(name, node['addr']))
             revAddrs[ node['addr'] ] = name
             print("ADDING revAddrs[{}]={}".format(node['addr'], name))

    for node in jsonNodes:
        name=node['name']
        print("NODE=" + name)
        if 'logins' in node:
            for login in node['logins']:
                if 'routes' in login:
                    for route in login['routes']:
                        (user, host) = getUserHost(route)
                        info = route
                        #print("HOST=" + host)
                        if host in addrs: info += " addr: " + addrs[host]
                        if host in hosts: info += " hosts " + hosts[host]
                        print("route --> " + info)
                        routesTo[route]={"name": name, "via": login}
     
        if 'sudo_routes' in node:
            for route in node['sudo_routes']:
                (user, host) = getUserHost(route)
                info = route
                #print("HOST=" + host)
                if host in addrs: info += " addr: " + addrs[host]
                if host in hosts: info += " hosts: " + hosts[host]
                print("sudor --> " + info)
                sudoRoutesTo[route]={"name": name, "via": 'XXX'}

    maxLoops=5
    while maxLoops > 0:
        maxLoops -= 1
        print("LOOP=" + str(maxLoops))
        nextNode = getNextHop( node0, routeEnd, jsonNodes, hosts, addrs, revAddrs, routesTo, sudoRoutesTo)
        print("routeEnd=<{}>".format(routeEnd))
        print("nextNode=<{}>".format(str(nextNode)))
        print("node0=<{}>".format(str(node0)))
       
        node = nextNode['name']
        login = nextNode['via']['login']
        (user,password) = getUserPassFromLogin(login)

        if loginOK(user, node, node0):
            fatal("Route found")
            pass
            #continue

        nextNode = user + '@' + node
        print("node=<{}>".format(node))
        print("user=<{}>".format(user))
        #if nextNode == node0:
            #return

        print("NEW routeEnd=<{}>".format(routeEnd))
        #fatal("So?")
        #routeEnd = nextNode
    #node0

def getUserPassFromLogin(login):
    if '/' in login:
        user = login[ :login.find('/')]
        password = login[ login.find('/')+1 :]
        return (user, password)
    return (login, None)

def loginOK(user, node, node0):
    for login in node0['logins']:
        login = login['login']
        print("node0['name']={} node={}".format(node0['name'], node))
        if node0['name'] == node:
            (user0,password0) = getUserPassFromLogin(login)
            print("node0['user']={} user={}".format(user0, user))
            if user == user0:
                return True
    return False
        

def getNextHop( node0, routeEnd, jsonNodes, hosts, addrs, revAddrs, routesTo, sudoRoutesTo):
    print("Searching for route ... to " + routeEnd)
    (u, h) = getUserHost(routeEnd)
    if h in revAddrs:
        routeEnd = u + '@' + revAddrs[h]
    print("Searching for route ... to " + routeEnd)

    if routeEnd in routesTo:
        print("Go via '" + str(routesTo[routeEnd]) + "'")
        return routesTo[routeEnd]
    if routeEnd in sudoRoutesTo:
        print("Go via sudo '" + str(sudoRoutesTo[routeEnd]) + "'")
        return sudoRoutesTo[routeEnd]
    #followRouteTo(routeEnd

    fatal("No route found from <{}> to <{}>".format(str(node0), routeEnd))
     
def findRouteTo(routeEnd, jsonNodes):
    if not isinstance(jsonNodes, list):
        fatal("Expected list")

    print("Searching for route to " + routeEnd)
    ( endUser , endHost ) = getUserHost( routeEnd )

    print("user={} host={}".format(endUser, endHost))

    findRouteTo2(jsonNodes[0], routeEnd, jsonNodes)
    
    return


ENCODING=None # Use bytes array
ENCODING='utf-8'
ENCODING='ascii'

KNOWN_HOSTS_PROMPT='Are you sure you want to continue connecting (yes/no)?'
KNOWN_HOSTS_REPLY='yes'

########################################
# Config:

VERBOSE=0
DEBUG=0

#MATCH_PROMPT='HypriotOS: '
DEFAULT_ROOT_MATCH_PROMPT=':~# '
DEFAULT_USER_MATCH_PROMPT=':~\$ '
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
    sys.exit(1)

def debug(level, msg):
    if VERBOSE >= level:
        print("DEBUG-{}: {}".format(level, msg))

'''
def UNUSED_ssh( host, user, password, cmd_list ):

    timeout=DEFAULT_TIMEOUT
    debug(1, "Cnxn {}@{}/{}".format( host, user, password ))

    try:
        debug(1, "Connecting to host " + host)

        # NOTE: use of optional encoding argument:
        ssh_child = pexpect.spawn( command, timeout=timeout, encoding=ENCODING , env=SHELL_ENV )
        if DEBUG > 0:
            ssh_child.logfile = sys.stdout

        _ssh( ssh_child, host, user, password, timeout, match_prompt, cmd_list )

    except Exception as e:
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("Exception = <<<\n" + str(e) + "\n    >>>")

    #print("Forcing exit")

def UNIMPLEMENTED_scp( host, user, password, src_file, dst ):

    timeout=DEFAULT_TIMEOUT
    debug(1, "scp {} -> {}@{}:{}".format(src_file, host, user, dst))

    try:
        debug(1, "Copying to host " + host)
        command = scp_id_template.format(SSH_OPTS, key_file, src_file, user, host, dst)

        debug(1, "Command='" + command + "'")
        ssh_child = pexpect.spawn( command, timeout=timeout, encoding=ENCODING , env=SHELL_ENV )
        if DEBUG > 0:
            #OUTPUT=True
            #ssh_child.logfile = None
            #fatal("ssh_child.logfile = sys.stdout")
            ssh_child.logfile = sys.stdout

        if password and password != CONST_PASSWORDLESS_LOGIN:
            send_password(ssh_child, password, timeout)

        ssh_child.expect(pexpect.EOF)

    except Exception as e:
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("Exception = <<<\n" + str(e) + "\n    >>>")

def UNIMPLEMENTED_copy_key( host, user, password, key_file):

    timeout=DEFAULT_TIMEOUT
    debug(1, "Copy_id {} -> {}@{}/{}".format(key_file, host, user, password))
    try:
        debug(1, "Coying to host " + host)
        command = copy_id_template.format(SSH_OPTS, key_file, user, host)

        debug(1, "Command='" + command + "'")
        ssh_child = pexpect.spawn( command, timeout=timeout, encoding=ENCODING , env=SHELL_ENV )
        if DEBUG > 0:
            ssh_child.logfile = sys.stdout

        if password and password != CONST_PASSWORDLESS_LOGIN:
            send_password(ssh_child, password, timeout)

        ssh_child.expect(pexpect.EOF)

    except Exception as e:
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("Exception = <<<\n" + str(e) + "\n    >>>")

'''

def send_password(ssh_child, password, timeout, known_hosts_prompt_seen=False, optional_match_prompt='UNMATCHABLE_PROMPT'):
    debug(1, "Waiting for password prompt[timeout={}] ....".format(timeout))

    idx = ssh_child.expect(['[Pp]assword:|[Pp]assword for \S+:', KNOWN_HOSTS_PROMPT, pexpect.EOF, pexpect.TIMEOUT, optional_match_prompt], timeout=timeout)
    if idx == 0:
        op = ssh_child.before
        #print("OP=" + str(op) )
        # print( str(op) )
        debug(1, "Got it .... password prompt ...." + op)
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
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("-- Received EOF")

    elif idx == 3:
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("-- Received TIMEOUT")

    elif idx == 4:
        debug(1,"optional_match_prompt: NO password needed")
        # Password not sent:
        return False

    else:
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("-- Received unexpected MATCH")

    # Password sent:
    return True

def mhop_ssh( hosts ):
    timeout=DEFAULT_TIMEOUT

    command = 'bash'
    ## # NOTE: use of optional encoding argument:
    ssh_child = pexpect.spawn( command, timeout=timeout, encoding=ENCODING , env=SHELL_ENV )
    if DEBUG > 0:
        ssh_child.logfile = sys.stdout
    debug(1,"-- bash spawned ...")

    for hostentry in hosts:

        #try:
        _ssh( ssh_child, hostentry )

        #except Exception as e:
        #if ssh_child.before:
        #    debug(1,"\nbefore='" + ssh_child.before + "'")
        #fatal("Exception = <<<\n" + str(e) + "\n    >>>")


def wait_on_prompt(ssh_child, match_prompt, timeout):
    debug(1, "wait_on_prompt(ssh_child, {}, {})".format(match_prompt, str(timeout)))
    idx = ssh_child.expect([ match_prompt, '[Pp]assword:', pexpect.EOF, pexpect.TIMEOUT], timeout=timeout)
    if idx == 0:
        op = ssh_child.before; debug(1, str(op) )
        #print("OP='" + str(op) + "'" )
        debug(1, "Got prompt")
    elif idx == 1:
        op = ssh_child.before; debug(1, str(op) )
        fatal("-- Unexpected password prompt")
    elif idx == 2:
        op = ssh_child.before; debug(1, str(op) )
        fatal("-- Received EOF")
    elif idx == 3:
        op = ssh_child.before; debug(1, str(op) )
        fatal("-- Received TIMEOUT")
    else:
        op = ssh_child.before; debug(1, str(op) )
        fatal("-- Received unexpected MATCH")

def createInstallKeyCommand( keyfile ):
    try:
        debug(1,"KEYFILE=" + keyfile)
        kf = open(keyfile)
        key_content=kf.readline().rstrip(os.linesep)
        kf.close()
        debug(1,"KEYCONTENT=" + key_content)
        install_key_command = CONST_COMMAND_INSTALL_KEY.format(key_content, key_content)
        debug(1,"KEYCOMMAND=" + install_key_command)
    except Exception as e:
        fatal("Install_KEY_template Exception = <<<\n" + str(e) + "\n    >>>")

    return install_key_command

def _ssh( ssh_child, hostentry ):

    host = hostentry["host"]
    user = hostentry["user"]

    use_key=None
    password=None
    if "use_key" in hostentry:
        use_key = hostentry["use_key"]
    elif "password" in hostentry:
        password = hostentry["password"]
    else:
        pass

    cmd_list = DEFAULT_COMMANDS.copy()
    if "commands" in hostentry:
        cmd_list.extend( hostentry["commands"] )

    if "timeout" in hostentry:
            timeout = hostentry["timeout"]
    else:
            timeout = None

    if "match_prompt" in hostentry:
            match_prompt = hostentry["match_prompt"]
    else:
            match_prompt = None # Use default

    debug(1,"Connect to {}@{}".format( user, host ))

    if use_key:
        command = ssh_key_template.format(SSH_OPTS, use_key, user, host)
        debug(1, "_ssh(child, {}, {}/key={}, {}, match_prompt={}, [{}]".format( host, user, use_key, timeout, str(match_prompt), str(cmd_list) ))
    elif password:
        command = ssh_template.format(SSH_OPTS, user, host)
        debug(1, "_ssh(child, {}, {}/pwd={}, {}, match_prompt={}, [{}]".format( host, user, password, timeout, str(match_prompt), str(cmd_list) ))
    else:
        command = ssh_template.format(SSH_OPTS, user, host)
        debug(1, "_ssh(child, {}, {}, {}, match_prompt={}, [{}]".format( host, user, timeout, str(match_prompt), str(cmd_list) ))

    debug(1, "Command='" + command + "'")
    ssh_child.sendline(command)

    if timeout == None:
        timeout = DEFAULT_TIMEOUT

    if match_prompt == None:
        if user == "root":
            if "root_match_prompt" in hostentry:
                match_prompt = hostentry["root_match_prompt"]
            else:
                match_prompt=DEFAULT_ROOT_MATCH_PROMPT
        else:
            match_prompt=DEFAULT_USER_MATCH_PROMPT
        debug(1,"Setting match_prompt=<<" + match_prompt + ">>")

    try:
        if password and password != CONST_PASSWORDLESS_LOGIN:
            send_password(ssh_child, password, timeout)

        #time.sleep(0.1)
        debug(1, "Waiting for '{}' prompt".format(match_prompt))
        wait_on_prompt(ssh_child, match_prompt, timeout)
    except Exception as e:
        debug(1,"\nbefore='" + ssh_child.before + "'")
        fatal("Connection Exception = <<<\n" + str(e) + "\n    >>>")



    #ssh_child.setecho(False)
    debug(1, "COMMAND_LIST=" + str(cmd_list))
    for cmd in cmd_list:
        debug(1,"cmd_list CMD=" + str(cmd))
        debug(1,"cmd_list match_prompt=" + str(match_prompt))

        # Insert INSTALL_KEY command, then pass to standard processing:
        if cmd == CONST_COMMAND_INSTALL_KEY_ARG:
            cmd = createInstallKeyCommand( hostentry["install_key"] )
            if cmd == None:
                fatal("Failed to create install_key command")

        elif cmd == CONST_COMMAND_SUDO_ARG:
            cmd = CONST_COMMAND_SUDO
            ssh_child.sendline(cmd)

            if "root_match_prompt" in hostentry:
                match_prompt = hostentry["root_match_prompt"]
            else:
                match_prompt=DEFAULT_ROOT_MATCH_PROMPT
            debug(1,"SUDO: Setting match_prompt=<<" + match_prompt + ">>")
            
            if send_password(ssh_child, password, timeout, optional_match_prompt=match_prompt):
                # Wait on prompt unless no password needed (prompt already seen):
                wait_on_prompt(ssh_child, match_prompt, timeout)
            continue
            #pass

        debug(1,"CMD=" + cmd)
        if cmd == CONST_INTERACT:
            try:
                debug(1, "INTERACT")
                TEMP_PROMPT="INTERACT: $PS1"
                #debug(1,"Setting prompt PS1=\"INTERACT \$PS1\"")
                #ssh_child.send('PS1="INTERACT \$PS1' + '\n')
                debug(1,"Setting prompt PS1=" + TEMP_PROMPT)
                ssh_child.sendline('PS1="' + TEMP_PROMPT + '"')
                saved_match_prompt=match_prompt
                match_prompt='INTERACT: '
                ssh_child.expect(match_prompt, timeout=timeout)
                debug(1, "Got prompt")

                print("")
                print("Entering interactive mode ...")
                print("  -- Press <enter> to start")
                print("  -- Press 'ctrl-]' to end")

                ssh_child.interact()
                match_prompt=saved_match_prompt
                print("Setting prompt back to " + match_prompt)
            except Exception as e:
                debug(1,"\nbefore='" + ssh_child.before + "'")
                fatal("INTERACT Exception = <<<\n" + str(e) + "\n    >>>")

            # If starts with '-' assume a timeout value (make +ve first!)
        elif cmd[0] == '-':
            timeout=-cmd

        else:
            try:
                debug(1, cmd)

                #ssh_child.send(cmd + '\n')
                debug(1,"sendline(" + cmd + ")")
                ssh_child.sendline(cmd)

                # LOCAL!! (i.e. not across ssh connection) op = pexpect.run(cmd)

                # NOTE: we can pass alist of regex matches, and also EOF, TIMEOUT values:
                debug(1,"expect(" + match_prompt + ")")
                wait_on_prompt(ssh_child, match_prompt, timeout)

                # Note: we can't spawn commands here as we've already done a spawn
                # child = ssh_child.spawn(cmd)
                # child.logfile_read = sys.stdout
                # child.expect(pexpect.EOF)
                timeout=DEFAULT_TIMEOUT

            except Exception as e:
                debug(1,"\nbefore='" + ssh_child.before + "'")
                fatal("CMD_LIST Exception = <<<\n" + str(e) + "\n    >>>")
                #import traceback, os.path
                #top = traceback.extract_stack()[-1]
                #debug(1, ', '.join([type(e).__name__, os.path.basename(top[0]), str(top[1])]))

def add_command(cmd):
    if len(hosts) == 0:
        if len(DEFAULT_COMMANDS) != 0:
            DEFAULT_COMMANDS.append(cmd)
        else:
            DEFAULT_COMMANDS = [ cmd ]
        debug(1, "Added command into DEFAULT_COMMANDS: " + str(DEFAULT_COMMANDS))
    else:
        if "commands" in hosts[-1]:
            hosts[-1]["commands"].append(cmd)
        else:
            hosts[-1]["commands"] = [ cmd ]
        debug(1, "Added command into hosts[-1][commands]: " + str(hosts[-1]["commands"]))

def main():
    mhop_ssh( hosts )


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

hosts = []

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

    if sys.argv[a] == '-json':
        a += 1; ipfile = sys.argv[a]
        jstree = readjson(ipfile)
        if not isinstance(jstree, list):
            fatal("Expected list")
        continue

    if sys.argv[a] == '-R':
        a += 1; routeEnd = sys.argv[a]
        findRouteTo(routeEnd, jstree)
        continue

    if sys.argv[a] == '-h':
        a += 1; hosts.append({ "host": sys.argv[a]})
        continue

    if sys.argv[a] == '-u':
        a += 1;
        hosts[-1]["user"] = sys.argv[a]
        continue

    if sys.argv[a] == '-p':
        a += 1;
        hosts[-1]["password"] = sys.argv[a]
        continue

    if sys.argv[a] == '-root-match-prompt':
        a += 1; prompt = sys.argv[a]
        hosts[-1]["root_match_prompt"] = prompt.replace('SPACE', ' ')
        continue

    if sys.argv[a] == '-i':
        a += 1;
        hosts[-1]["use_key"] = sys.argv[a]
        continue

    if sys.argv[a] == '-nopass':
        hosts[-1]["password"] = CONST_PASSWORDLESS_LOGIN
        continue

    if sys.argv[a] == '-install-key':
        a += 1;
        hosts[-1]["install_key"] = sys.argv[a]
        continue

    if sys.argv[a] == '-C':
        a += 1; cmd = sys.argv[a]
        if cmd == "SUDO":
            add_command(CONST_COMMAND_SUDO_ARG)
        elif cmd == "INSTALL_KEY":
            add_command(CONST_COMMAND_INSTALL_KEY_ARG)
            a += 1; keyfile = sys.argv[a]
            if ".pub" in keyfile:
                fatal("Please provide private key path")
            keyfile = keyfile + ".pub"
            hosts[-1]["install_key"] = keyfile
        else:
            fatal("Unknown command: " + cmd)
        continue

    if sys.argv[a] == '-c':
        a += 1; cmd = sys.argv[a]
        add_command(cmd)
        continue

    if sys.argv[a] == '-int':
        add_command(CONST_INTERACT)
        continue

    ## if sys.argv[a] == '-noop':
        ## OUTPUT=False
        ## continue

    if sys.argv[a] == '-to':
        a += 1; timeout = int(sys.argv[a])
        if len(hosts) == 0:
            DEFAULT_TIMEOUT = timeout
        else:
            hosts[-1]["timeout"] = timeout
        continue

    if sys.argv[a] == '--PROMPT' or sys.argv[a] == '-mp':
        #a += 1; match_prompt = int(sys.argv[a])
        #hosts[-1]["match_prompt"] = match_prompt
        a += 1; match_prompt = sys.argv[a]
        hosts[-1]["match_prompt"] = match_prompt.replace('SPACE', ' ')
        continue

    if sys.argv[a] == '-no-host-checks' or sys.argv[a] == '-nhc':
        SSH_OPTS += NO_HOST_CHECKS
        continue

    #if sys.argv[a] == '--copy-id':
    #    copy_key( host, user, password, key_file=key_file )
    #    password = None
    #    copy_id = False
    #    continue

    #if sys.argv[a] == '--scp':
    #    a += 1; key_file = sys.argv[a]
    #    a += 1; src_file = sys.argv[a]
    #    a += 1; dst      = sys.argv[a]
    #    scp( host, user, password, src_file, dst )

    fatal("Unknown arg#[{}] <{}>".format(a, sys.argv[a]))

########################################
# Main:

if VERBOSE != 0:
    print("VERBOSE=" + str(VERBOSE))
    if DEFAULT_TIMEOUT != None:
        print("DEFAULT_TIMEOUT=" + str(DEFAULT_TIMEOUT))

if __name__ == '__main__':
    #print(str(hosts[-1]["commands"]))
    #fatal("TEST")
    main()


