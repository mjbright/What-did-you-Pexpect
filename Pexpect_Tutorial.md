
<center>
<h1>What did you Expect?</h1>
<h1>Python module - Pexpect</h1>
</center>

# Overview
- Expect, tcl, Pexpect
- Pexpect capabilities
- Pexpect examples
- Pexpect demos
  - One off password login
  - Multi-hop ssh key setup
  - Switch config: login, navigation, paging

Note: To run most of these demonstration elements it is sufficient to have
- Jupyter installed with bash_kernel extension
- pexpect module imported
- A set of machines available with addresses 172.17.0.2, 172.17.0.3, 172.17.0.4 each with user/password as login
    This can be done using the https://github.com/mjbright/Containers-as-servers repository

# Expect, tcl, Pexpect

History of expect, a tcl facility

Pexpect module to provide same functionality

Used by Jupyter when handling kernels

# Pexpect capabilities

Ability to
- interact with a tty and simulate a user typing at a keyboard
- detect (**expect**) patterns in the output to allow to pass back control

- pexpect.spawn: a class allowing to spawn a sub-process and to control it
  - detect patterns in the output using expect()
  - send() input to the process
- run: a method which allows simplified scenarios
- replwrapper: a useful abstraction for controlling an interpreter
- pxssh: a useful wrapper for handling a simple ssh connection


# Pexpect examples

First let's import the pexpect module, set a default timeout to use and set a default PROMPT for shell interactions.


```python
import pexpect

timeout=5

#PROMPT='monitoring: '
PROMPT='\$ '

# Create a pretty printer:
import pprint
pp = pprint.PrettyPrinter(indent=4)
```

```pexpect.run(command, timeout=30, withexitstatus=False, events=None, extra_args=None, logfile=None, cwd=None, env=None, **kwargs)```

**run** [documentation](https://pexpect.readthedocs.org/en/stable/api/pexpect.html#run-function) returns command output as a string (or a tple with exit code if withexitstatus is True).

### Optional event handling:
- events takes a Dictionary or tpl matching events (o/p pattern matches, timeouts, Pexcept exceptions) with an appropriate action
- extra_args are passed into event callbacks
- event callbacks return True to stop processing events



Let's just call the run() method with a command string, specifying an encoding
(we get more readable output than the default unencodede byte array).

We are just executing a command and returning


```python
# run() is a convenience function to run a command and recuperate it's output
# - returns byte array, unless encoding is specified
print(pexpect.run('ls -al', encoding='utf-8'))
```

    total 88
    drwxrwxr-x  4 ubuntu ubuntu  4096 Apr 26 17:50 .
    drwxr-xr-x 12 ubuntu ubuntu  4096 Apr 26 14:20 ..
    drwxr-xr-x  2 ubuntu ubuntu  4096 Apr 25 19:09 .ipynb_checkpoints
    -rw-rw-r--  1 ubuntu ubuntu   754 Apr 26 17:50 jupyter.log
    drwxrwxr-x  2 ubuntu ubuntu  4096 Apr 26 14:20 pexpect
    -rw-rw-r--  1 ubuntu ubuntu 27448 Apr 26 17:50 Pexpect Tutorial.ipynb
    -rw-rw-r--  1 ubuntu ubuntu 38641 Apr 26 10:59 Pexpect Tutorial.ipynb.2
    


Run can match events and act accordingly, first let's define some handler functions to be called
on error, timeout or successful match.

These functions will show us what is happening and what text precedes/follows any match


```python
USER_PASSWORD='password'

# Handle errors and timeouts:
def ferr(spawnObject):
    if spawnObject['index'] == 2:
        print("ferr: TIMEOUT event seen - stop processing (return True)")
    elif spawnObject['index'] == 3:
        print("ferr: EOF event seen (child exited) - stop processing (return True)")
    else:
        print("ferr: ERROR event seen - stop processing (return True)")
    #pp.pprint(spawnObject)
    print("BEFORE=<<"+spawnObject['child'].before.strip() + ">>")
    return True

# Handle matched prompt:
def fprompt(spawnObject):
    print("fprompt: PROMPT matched - stop processing (return True)")
    #pp.pprint(spawnObject)
    print("BEFORE=<<"+ ppbefore(spawnObject) + "\n>>")
    print("AFTER=<<"+ ppafter(spawnObject) + "\n>>")
    return True

```

Now let's run an ssh command but with 0 seconds timeout which will obviously(hopefully!) fail with a timeout.


```python
#
# Very short TIMEOUT
#

op = pexpect.run('ssh user@172.17.0.2', events=[('[Pp]assword:', USER_PASSWORD+'\n'),\
                                           ('\$', fprompt), (pexpect.TIMEOUT, ferr), (pexpect.EOF, ferr)],\
            timeout=0, encoding='utf-8')
print()
```

    ferr: TIMEOUT event seen - stop processing (return True)
    {   'child': <pexpect.pty_spawn.spawn object at 0x7f6e440bd6d8>,
        'child_result_list': [''],
        'command': 'ssh user@172.17.0.2',
        'cwd': None,
        'env': None,
        'event_count': 0,
        'events': [   ('[Pp]assword:', 'password\n'),
                      ('\\$', <function fprompt at 0x7f6e440a3ea0>),
                      (   <class 'pexpect.exceptions.TIMEOUT'>,
                          <function ferr at 0x7f6e440ed840>),
                      (   <class 'pexpect.exceptions.EOF'>,
                          <function ferr at 0x7f6e440ed840>)],
        'extra_args': None,
        'index': 2,
        'kwargs': {'encoding': 'utf-8'},
        'logfile': None,
        'patterns': [   '[Pp]assword:',
                        '\\$',
                        <class 'pexpect.exceptions.TIMEOUT'>,
                        <class 'pexpect.exceptions.EOF'>],
        'responses': [   'password\n',
                         <function fprompt at 0x7f6e440a3ea0>,
                         <function ferr at 0x7f6e440ed840>,
                         <function ferr at 0x7f6e440ed840>],
        'timeout': 0,
        'withexitstatus': False}
    BEFORE=<<>>
    


Now let's use a very long timeout but see what happens when we provide a bad password.

Behind the scenes we get prompted multiple times for the password until the ssh server rejects us.


```python
#
# BAD PASSWORD: keeps trying until process exists: (BEFORE TIMEOUT of 4000 secs)
#

op = pexpect.run('ssh user@172.17.0.2', events=[('[Pp]assword:', '****BAD_PASSWORD****'+'\n'),\
                                           ('\$', fprompt), (pexpect.TIMEOUT, ferr), (pexpect.EOF, ferr)],\
            timeout=4000, encoding='utf-8')
print()
```

    ferr: EOF event seen (child exited) - stop processing (return True)
    BEFORE=<<Permission denied (publickey,password).>>
    


Let's now define some helper functions used to show text surrounding the matched text:


```python

# Helper function ppbefore: to pretty-print text before the match:
def ppbefore(object):
    if isinstance(object, pexpect.pty_spawn.spawn):
        pass
    elif isinstance(object, dict):
        object = object['child']
    else:
        return("<<UnknownType>>")
        
    if hasattr(object, 'child'):
        object = object['child']

    if not hasattr(object, 'before'):
        return "<<None>>"
    if object.before == pexpect.EOF:
        return "<<pexpect.EOF>>"
    if object.before == pexpect.TIMEOUT:
        return "<<pexpect.TIMEOUT>>"
    
    return str.join('\n    ', object.before.strip().split('\n') )

# Helper function ppafter: to pretty-print text after the match:
def ppafter(object):
    if isinstance(object, pexpect.pty_spawn.spawn):
        pass
    elif isinstance(object, dict):
        object = object['child']
    else:
        return("<<UnknownType>>")
        
    if hasattr(object, 'child'):
        object = object['child']

    if not hasattr(object, 'after'):
        return "<<None>>"
    if object.after == pexpect.EOF:
        return "<<pexpect.EOF>>"
    if object.after == pexpect.TIMEOUT:
        return "<<pexpect.TIMEOUT>>"

    return str.join('\n    ', object.after.strip().split('\n') )

#ssh_child = pexpect.spawn( "ls -al", timeout=timeout, encoding='utf-8')
#ssh_child.expect(pexpect.EOF)
#print("ssh_child.before=" + ssh_child.before)
#print("ppbefore(ssh_child=" + ppbefore(ssh_child) + ")")
#print("ppafter(ssh_child="  + ppafter(ssh_child) + ")")
```

Now let's perform a successful login:


```python
#
# SUCCESSFUL login:
#
op = pexpect.run('ssh user@172.17.0.2', events=[('[Pp]assword:', USER_PASSWORD+'\n'),\
                                                (PROMPT, fprompt),\
                                                (pexpect.TIMEOUT, ferr),\
                                                (pexpect.EOF, ferr)],\
                 timeout=4, encoding='utf-8')
print()
```

    fprompt: PROMPT matched - stop processing (return True)
    BEFORE=<<Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
        
         * Documentation:  https://help.ubuntu.com/
        Last login: Tue Apr 26 17:49:03 2016 from 172.17.0.1
    >>
    AFTER=<<$
    >>
    


# pexpect.spawn class

Now let's look at the spawn class

```class pexpect.spawn(command, args=[], timeout=30, maxread=2000, searchwindowsize=None, logfile=None, cwd=None, env=None, ignore_sighup=False, echo=True, preexec_fn=None, encoding=None, codec_errors='strict', dimensions=None)```

*class* **spawn** [documentation](https://pexpect.readthedocs.org/en/stable/api/pexpect.html#spawn-classy)

Spawns a sub-process which we can control, returns a spawn instance.
We can
- detect patterns on the process output with *expect()*
- control the sub-process by sending to its' input with *send()*.





The spawn class constructor returns us an instance of a spawned process to which we can send further input.

(this is used under the hood in the run() method we saw earlier)

Now when we perform operations we can match output in an imperative way.

Let's launch a process, and run it to completion by waiting on the EOF token.


```python
ssh_child = pexpect.spawn( "ls -al", timeout=timeout, encoding='utf-8')
ssh_child.expect(pexpect.EOF)
print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
print("AFTER=<<" + ppafter(ssh_child)  + "\n>> ----")
#dir(ssh_child)
```

    BEFORE=<<total 96
        drwxrwxr-x  4 ubuntu ubuntu  4096 Apr 26 17:58 .
        drwxr-xr-x 12 ubuntu ubuntu  4096 Apr 26 14:20 ..
        drwxr-xr-x  2 ubuntu ubuntu  4096 Apr 25 19:09 .ipynb_checkpoints
        -rw-rw-r--  1 ubuntu ubuntu  1026 Apr 26 17:58 jupyter.log
        drwxrwxr-x  2 ubuntu ubuntu  4096 Apr 26 14:20 pexpect
        -rw-rw-r--  1 ubuntu ubuntu 33172 Apr 26 17:58 Pexpect Tutorial.ipynb
        -rw-rw-r--  1 ubuntu ubuntu 38641 Apr 26 10:59 Pexpect Tutorial.ipynb.2
    >> ----
    AFTER=<<<<pexpect.EOF>>
    >> ----


Now let's run the same ls command, but stop as soon as we see the '..' parent dir characters


```python
ssh_child = pexpect.spawn( "ls -al", timeout=timeout, encoding='utf-8')
ssh_child.expect('\.\.')
print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
```

    BEFORE=<<total 96
        drwxrwxr-x  4 ubuntu ubuntu  4096 Apr 26 17:58 .
        drwxr-xr-x 12 ubuntu ubuntu  4096 Apr 26 14:20
    >> ----


Let's see how we can provide a list of possible matches, including EOF and TIMEOUT special cases.

The call to expect() blocks until it gets a match.

It returns an index to the matching element of our list.

In the following example we provide '.' and '..' match patterns, the first will match first.


```python
ssh_child = pexpect.spawn( "ls -al", timeout=timeout, encoding='utf-8')
idx = ssh_child.expect(['\.','\.\.',pexpect.EOF,pexpect.TIMEOUT])
print("index=" + str(idx))
print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
print("Matched on <<" + str( ssh_child.match ) + ">>")
print("AFTER=<<"+ ppafter(ssh_child) + "\n>> ----")
```

    index=0
    BEFORE=<<total 96
        drwxrwxr-x  4 ubuntu ubuntu  4096 Apr 26 18:00
    >> ----
    Matched on <<<_sre.SRE_Match object; span=(57, 58), match='.'>>>
    AFTER=<<.
    >> ----


Let's perform a similar match query which cannot match.

We see that expect() returns a EOF as the 'ls' command completed but we didn't match either of the 2 strings before
matching the EOF.


```python
ssh_child = pexpect.spawn( "ls -al", timeout=timeout, encoding='utf-8')
idx = ssh_child.expect(['NOTSEEN','EITHER',pexpect.EOF,pexpect.TIMEOUT])
print("index=" + str(idx))
print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
print("Matched on <<" + str( ssh_child.match ) + ">>")
print("AFTER=<<"+ ppafter(ssh_child) + "\n>> ----")
```

    index=2
    BEFORE=<<total 96
        drwxrwxr-x  4 ubuntu ubuntu  4096 Apr 26 18:00 .
        drwxr-xr-x 12 ubuntu ubuntu  4096 Apr 26 14:20 ..
        drwxr-xr-x  2 ubuntu ubuntu  4096 Apr 25 19:09 .ipynb_checkpoints
        -rw-rw-r--  1 ubuntu ubuntu  1094 Apr 26 18:00 jupyter.log
        drwxrwxr-x  2 ubuntu ubuntu  4096 Apr 26 14:20 pexpect
        -rw-rw-r--  1 ubuntu ubuntu 34168 Apr 26 18:00 Pexpect Tutorial.ipynb
        -rw-rw-r--  1 ubuntu ubuntu 38641 Apr 26 10:59 Pexpect Tutorial.ipynb.2
    >> ----
    Matched on <<<class 'pexpect.exceptions.EOF'>>>
    AFTER=<<<<pexpect.EOF>>
    >> ----


Now let's do the same query whilst forcing a timeout


```python
ssh_child = pexpect.spawn( "ls -al", timeout=0, encoding='utf-8')
idx = ssh_child.expect(['NOTSEEN','EITHER',pexpect.EOF,pexpect.TIMEOUT])
print("index=" + str(idx))
print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
print("Matched on <<" + str( ssh_child.match ) + ">>")
print("AFTER=<<"+ ppafter(ssh_child) + "\n>> ----")
```

    index=3
    BEFORE=<<total 96
        drwxrwxr-x  4 ubuntu ubuntu  4096 Apr 26 18:00 .
        drwxr-xr-x 12 ubuntu ubuntu  4096 Apr 26 14:20 ..
        drwxr-xr-x  2 ubuntu ubuntu  4096 Apr 25 19:09 .ipynb_checkpoints
        -rw-rw-r--  1 ubuntu ubuntu  1094 Apr 26 18:00 jupyter.log
        drwxrwxr-x  2 ubuntu ubuntu  4096 Apr 26 14:20 pexpect
        -rw-rw-r--  1 ubuntu ubuntu 34168 Apr 26 18:00 Pexpect Tutorial.ipynb
        -rw-rw-r--  1 ubuntu ubuntu 38641 Apr 26 10:59 Pexpect Tutorial.ipynb.2
    >> ----
    Matched on <<<class 'pexpect.exceptions.TIMEOUT'>>>
    AFTER=<<<<pexpect.TIMEOUT>>
    >> ----


These were still very simple examples.  In use we want to spawn a process and then interact with it, using expect() to detect the process state and then send() or sendline() to send input to the process (such as commands to a shell)


```python
ssh_child = pexpect.spawn( "bash", timeout=timeout, encoding='utf-8')
```


```python
# send() returns number of characters sent:
ssh_child.send("ls -al")
#print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
```




    6




```python
ssh_child.expect(PROMPT, timeout=timeout)
```




    0




```python
print("BEFORE=<<"+ ppbefore(ssh_child) + "\n>> ----")
print("Matched on <<" + str( ssh_child.match ) + ">>")
print("AFTER=<<"+ ppafter(ssh_child) + "\n>> ----")
```

    BEFORE=<<]0;ubuntu@ubuntu-xenial: ~/notebooks[01;32mubuntu@ubuntu-xenial[00m:[01;34m~/notebooks[00m
    >> ----
    Matched on <<<_sre.SRE_Match object; span=(96, 98), match='$ '>>>
    AFTER=<<$
    >> ----


Now let's inspect the 'ssh_child' which is spawn object:


```python
print(ssh_child)
```

    <pexpect.pty_spawn.spawn object at 0x7f6e440beeb8>
    command: /bin/bash
    args: ['/bin/bash']
    searcher: None
    buffer (last 100 chars): 'ls -alls -al'
    before (last 100 chars): '\x1b]0;ubuntu@ubuntu-xenial: ~/notebooks\x07\x1b[01;32mubuntu@ubuntu-xenial\x1b[00m:\x1b[01;34m~/notebooks\x1b[00m'
    after: '$ '
    match: <_sre.SRE_Match object; span=(96, 98), match='$ '>
    match_index: 0
    exitstatus: None
    flag_eof: False
    pid: 3768
    child_fd: 53
    closed: False
    timeout: 5
    delimiter: <class 'pexpect.exceptions.EOF'>
    logfile: None
    logfile_read: None
    logfile_send: None
    maxread: 2000
    ignorecase: False
    searchwindowsize: None
    delaybeforesend: 0.05
    delayafterclose: 0.1
    delayafterterminate: 0.1


# pexepct.REPLWrapper()

```class pexpect.replwrap.REPLWrapper(cmd_or_spawn, orig_prompt, prompt_change, new_prompt='[PEXPECT_PROMPT>', continuation_prompt='[PEXPECT_PROMPT+', extra_init_cmd=None)[source]
```

The following example shows how the replwrap wrapper can be used to wrap around a sub-process and send commands which will be correctly handled as the wrapper handles detection of the prompt.

We launch the Python interpreter as a sub-process and send commands to it.


```python
import pexpect.replwrap

#py = pexpect.replwrap.REPLWrapper("python", ">>> ", "import sys; sys.ps1={!r}; sys.ps2={!r}")

py = pexpect.replwrap.REPLWrapper("python", ">>> ", None)
print ( py.run_command("4+7") )
print ( py.run_command("print('hello')") )

```

    11
    
    hello
    


# Pexpect.pxssh()

```class pexpect.pxssh.pxssh(timeout=30, maxread=2000, searchwindowsize=None, logfile=None, cwd=None, env=None, ignore_sighup=True, echo=True, options={}, encoding=None, codec_errors='strict')
```

pxssh provides a useful wrapper for handling a simple ssh connection


```python
import pexpect.pxssh
import getpass
try:
    s = pexpect.pxssh.pxssh(encoding='utf-8')
    hostname = '172.17.0.2'
    username = 'user'
    password = 'password'
    s.login(hostname, username, password)
    s.sendline('uptime')   # run a command
    s.prompt()             # match the prompt
    print(s.before)        # print everything before the prompt.
    s.sendline('ls -l')
    s.prompt()
    print(s.before)
    s.sendline('df')
    s.prompt()
    print(s.before)
    s.logout()
except pxssh.ExceptionPxssh as e:
    print("pxssh failed on login.")
    print(e)
```

    uptime
     20:50:49 up  2:33,  1 user,  load average: 0.15, 0.06, 0.06
    
    ls -l
    total 0
    
    df
    Filesystem     1K-blocks    Used Available Use% Mounted on
    none            10098468 3767584   6314500  38% /
    tmpfs             508100       0    508100   0% /dev
    tmpfs             508100       0    508100   0% /sys/fs/cgroup
    /dev/sda1       10098468 3767584   6314500  38% /etc/hosts
    shm                65536       0     65536   0% /dev/shm
    


# Pexpect demos
  - One off password login (already seen)
  - Multi-hop ssh key setup
  - Switch config: login, navigation, paging

# Pexpect demos
##  Multi-hop ssh key setup


```python
!~/bin/mhop_ssh.py -d     -h 172.17.0.2 -u user -p password       --PROMPT '\$ ' -to 3 -c 'echo "HOSTNAME=$(hostname)"'
```

    ssh  -l user 172.17.0.2
    To run a command as administrator (user "root"), use "sudo <command>".
    See "man sudo_root" for details.
    
    ssh  -l user 172.17.0.2
    ubuntu@ubuntu-xenial:/home/ubuntu/notebooks$ ssh  -l user 172.17.0.2
    user@172.17.0.2's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 17:57:54 2016 from 172.17.0.1
    $ echo "HOSTNAME=$(hostname)"
    echo "HOSTNAME=$(hostname)"
    HOSTNAME=container1
    $ 


```python
MH="~/bin/mhop_ssh.py"
HOST1="-h 172.17.0.2 -u user -p password --PROMPT '\$ ' -to 3"
CMD='echo "HOSTNAME=$(hostname)"'

!$MH -d $HOST1 -c '$CMD'
```

    ssh  -l user 172.17.0.2
    To run a command as administrator (user "root"), use "sudo <command>".
    See "man sudo_root" for details.
    
    ssh  -l user 172.17.0.2ubuntu@ubuntu-xenial:/home/ubuntu/notebooks$ ssh  -l user 172.17.0.2
    user@172.17.0.2's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:10:46 2016 from 172.17.0.1
    $ echo "HOSTNAME=$(hostname)"
    echo "HOSTNAME=$(hostname)"
    HOSTNAME=container1
    $ 


```python
MH="~/bin/mhop_ssh.py"
HOST1="-h 172.17.0.2 -u user -p password --PROMPT '\$ ' -to 3"
HOST2="-h 172.17.0.3 -u user -p password --PROMPT '\$ ' -to 3"
HOST3="-h 172.17.0.4 -u user -p password --PROMPT '\$ ' -to 3"
CMD='echo "USER=$USER HOSTNAME=$(hostname)"'

!$MH -d $HOST1 -c '$CMD' $HOST2 -c '$CMD' $HOST3 -c '$CMD'
```

    ssh  -l user 172.17.0.2
    To run a command as administrator (user "root"), use "sudo <command>".
    See "man sudo_root" for details.
    
    ssh  -l user 172.17.0.2ubuntu@ubuntu-xenial:/home/ubuntu/notebooks$ ssh  -l user 172.17.0.2
    user@172.17.0.2's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:11:14 2016 from 172.17.0.1
    $ echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"
    USER=user HOSTNAME=container1
    $ ssh  -l user 172.17.0.3
    ssh  -l user 172.17.0.3
    The authenticity of host '172.17.0.3 (172.17.0.3)' can't be established.
    ECDSA key fingerprint is SHA256:IACNeco28miw3ncf888cWd9caRCBoPrKjsQQtp4NdqU.
    Are you sure you want to continue connecting (yes/no)? yes
    yes
    Warning: Permanently added '172.17.0.3' (ECDSA) to the list of known hosts.
    user@172.17.0.3's password: password
    password^J
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    
    The programs included with the Ubuntu system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/*/copyright.
    
    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.
    
    $ echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=user HOSTNAME=container2
    $ ssh  -l user 172.17.0.4
    ssh  -l user 172.17.0.4^Jssh  -l user 172.17.0.4
    The authenticity of host '172.17.0.4 (172.17.0.4)' can't be established.
    ECDSA key fingerprint is SHA256:IACNeco28miw3ncf888cWd9caRCBoPrKjsQQtp4NdqU.
    Are you sure you want to continue connecting (yes/no)? yes
    yes^Jyes
    Warning: Permanently added '172.17.0.4' (ECDSA) to the list of known hosts.
    user@172.17.0.4's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    
    The programs included with the Ubuntu system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/*/copyright.
    
    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.
    
    $ echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=user HOSTNAME=container3
    $ 


```python
MH="~/bin/mhop_ssh.py"
HOST1="-h 172.17.0.2 -u user -p password --PROMPT '\$ ' -to 3 -root-match-prompt '#SPACE'"
HOST2="-h 172.17.0.3 -u user -p password --PROMPT '\$ ' -to 3"
HOST3="-h 172.17.0.4 -u user -p password --PROMPT '\$ ' -to 3"
CMD='echo "USER=$USER HOSTNAME=$(hostname)"'

!echo $MH -d $HOST1 -c '$CMD' -C SUDO -c '$CMD' $HOST2 -c '$CMD' $HOST3 -c '$CMD'
!$MH -d $HOST1 -c '$CMD' -C SUDO -c '$CMD' $HOST2 -c '$CMD' -C SUDO -c '$CMD' $HOST3 -c '$CMD' -C SUDO -c '$CMD' 
```

    ssh  -l user 172.17.0.2
    To run a command as administrator (user "root"), use "sudo <command>".
    See "man sudo_root" for details.
    
    ssh  -l user 172.17.0.2ubuntu@ubuntu-xenial:/home/ubuntu/notebooks$ ssh  -l user 172.17.0.2
    user@172.17.0.2's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:17:45 2016 from 172.17.0.1
    $ echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"
    USER=user HOSTNAME=container1
    $ sudo -i
    sudo -i
    [sudo] password for user: password
    
    root@container1:~# echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=root HOSTNAME=container1
    root@container1:~# ssh  -l user 172.17.0.3
    ssh  -l user 172.17.0.3^Jssh  -l user 172.17.0.3
    The authenticity of host '172.17.0.3 (172.17.0.3)' can't be established.
    ECDSA key fingerprint is SHA256:IACNeco28miw3ncf888cWd9caRCBoPrKjsQQtp4NdqU.
    Are you sure you want to continue connecting (yes/no)? yes
    yes^Jyes
    Warning: Permanently added '172.17.0.3' (ECDSA) to the list of known hosts.
    user@172.17.0.3's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:17:19 2016 from 172.17.0.1
    $ echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=user HOSTNAME=container2
    $ sudo -i
    sudo -i^Jsudo -i
    [sudo] password for user: password
    
    root@container2:~# echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=root HOSTNAME=container2
    root@container2:~# ssh  -l user 172.17.0.4
    ssh  -l user 172.17.0.4^Jssh  -l user 172.17.0.4
    The authenticity of host '172.17.0.4 (172.17.0.4)' can't be established.
    ECDSA key fingerprint is SHA256:IACNeco28miw3ncf888cWd9caRCBoPrKjsQQtp4NdqU.
    Are you sure you want to continue connecting (yes/no)? yes
    yes^Jyes
    Warning: Permanently added '172.17.0.4' (ECDSA) to the list of known hosts.
    user@172.17.0.4's password: password
    password^J
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:17:32 2016 from 172.17.0.1
    $ echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=user HOSTNAME=container3
    $ sudo -i
    sudo -i^Jsudo -i
    [sudo] password for user: password
    password^J
    root@container3:~# echo "USER=$USER HOSTNAME=$(hostname)"
    echo "USER=$USER HOSTNAME=$(hostname)"^Jecho "USER=$USER HOSTNAME=$(hostname)"
    USER=root HOSTNAME=container3
    root@container3:~# 


```python
KEY="~/.ssh/id_rsa"
INSTALL_KEYS="-C INSTALL_KEY " + KEY + " -C SUDO -C INSTALL_KEY " + KEY
!echo $MH -d $HOST1 $INSTALL_KEYS $HOST2 $INSTALL_KEYS $HOST3 $INSTALL_KEYS 
!$MH -d $HOST1 $INSTALL_KEYS $HOST2 $INSTALL_KEYS $HOST3 $INSTALL_KEYS 
```

    /home/ubuntu/bin/mhop_ssh.py -d -h 172.17.0.2 -u user -p password --PROMPT \$  -to 3 -root-match-prompt #SPACE -C INSTALL_KEY /home/ubuntu/.ssh/id_rsa -C SUDO -C INSTALL_KEY /home/ubuntu/.ssh/id_rsa -h 172.17.0.3 -u user -p password --PROMPT \$  -to 3 -C INSTALL_KEY /home/ubuntu/.ssh/id_rsa -C SUDO -C INSTALL_KEY /home/ubuntu/.ssh/id_rsa -h 172.17.0.4 -u user -p password --PROMPT \$  -to 3 -C INSTALL_KEY /home/ubuntu/.ssh/id_rsa -C SUDO -C INSTALL_KEY /home/ubuntu/.ssh/id_rsa
    ssh  -l user 172.17.0.2
    To run a command as administrator (user "root"), use "sudo <command>".
    See "man sudo_root" for details.
    
    ssh  -l user 172.17.0.2ubuntu@ubuntu-xenial:/home/ubuntu/notebooks$ ssh  -l user 172.17.0.2
    user@172.17.0.2's password: password
    
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:21:42 2016 from 172.17.0.1
    $ echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    user@container1
    ls: cannot access '.ssh': No such file or directory
    Creating dir .ssh
    grep: .ssh/authorized_keys: No such file or directory
    Adding key
    total 12
    drwxr-xr-x 2 user users 4096 Apr 26 18:22 .
    drwxr-xr-x 4 user users 4096 Apr 26 18:22 ..
    -rw-r--r-- 1 user users  402 Apr 26 18:22 authorized_keys
      1   3 402 .ssh/authorized_keys
    $ sudo -i
    sudo -i
    [sudo] password for user: password
    password^J
    root@container1:~# echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    <.ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/auth                         orized_keys
    root@container1
    total 12
    drwx------ 2 root root 4096 Apr 26 18:19 .
    -rw-r--r-- 1 root root  222 Apr 26 18:19 known_hosts
    drwx------ 3 root root 4096 Apr 26 18:19 ..
    grep: .ssh/authorized_keys: No such file or directory
    Adding key
    total 16
    drwx------ 2 root root 4096 Apr 26 18:22 .
    drwx------ 3 root root 4096 Apr 26 18:19 ..
    -rw-r--r-- 1 root root  402 Apr 26 18:22 authorized_keys
    -rw-r--r-- 1 root root  222 Apr 26 18:19 known_hosts
      1   3 402 .ssh/authorized_keys
    root@container1:~# ssh  -l user 172.17.0.3
    ssh  -l user 172.17.0.3^Jssh  -l user 172.17.0.3
    user@172.17.0.3's password: password
    password^J
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:19:47 2016 from 172.17.0.2
    $ echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys^Jecho ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    user@container2
    ls: cannot access '.ssh': No such file or directory
    Creating dir .ssh
    grep: .ssh/authorized_keys: No such file or directory
    Adding key
    total 12
    drwxr-xr-x 2 user users 4096 Apr 26 18:22 .
    drwxr-xr-x 4 user users 4096 Apr 26 18:22 ..
    -rw-r--r-- 1 user users  402 Apr 26 18:22 authorized_keys
      1   3 402 .ssh/authorized_keys
    $ sudo -i
    sudo -i^Jsudo -i
    [sudo] password for user: password
    
    root@container2:~# echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    <.ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/auth                         orized_keys
    root@container2
    total 12
    -rw-r--r-- 1 root root  222 Apr 26 18:19 known_hosts
    drwx------ 2 root root 4096 Apr 26 18:19 .
    drwx------ 3 root root 4096 Apr 26 18:19 ..
    grep: .ssh/authorized_keys: No such file or directory
    Adding key
    total 16
    drwx------ 2 root root 4096 Apr 26 18:22 .
    drwx------ 3 root root 4096 Apr 26 18:19 ..
    -rw-r--r-- 1 root root  402 Apr 26 18:22 authorized_keys
    -rw-r--r-- 1 root root  222 Apr 26 18:19 known_hosts
      1   3 402 .ssh/authorized_keys
    root@container2:~# ssh  -l user 172.17.0.4
    ssh  -l user 172.17.0.4^Jssh  -l user 172.17.0.4
    user@172.17.0.4's password: password
    password^J
    Welcome to Ubuntu 16.04 LTS (GNU/Linux 4.4.0-21-generic x86_64)
    
     * Documentation:  https://help.ubuntu.com/
    Last login: Tue Apr 26 18:19:49 2016 from 172.17.0.3
    $ echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys^Jecho ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    user@container3
    ls: cannot access '.ssh': No such file or directory
    Creating dir .ssh
    grep: .ssh/authorized_keys: No such file or directory
    Adding key
    total 12
    drwxr-xr-x 2 user users 4096 Apr 26 18:22 .
    drwxr-xr-x 4 user users 4096 Apr 26 18:22 ..
    -rw-r--r-- 1 user users  402 Apr 26 18:22 authorized_keys
      1   3 402 .ssh/authorized_keys
    $ sudo -i
    sudo -i^Jsudo -i
    [sudo] password for user: password
    
    root@container3:~# echo ${USER}@$(hostname); ls -altr .ssh; [ ! -d .ssh ] && { echo "Creating dir .ssh"; mkdir .ssh; }; grep -q "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" .ssh/authorized_keys || { echo "Adding key"; echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDKrUEty+kY1B6M1K/7xvWAJIIi3s50Q7ltvXgbz3bJDu/2laSO7FL+/oxB/fzdV4KTNh9VS8ZYhFgISdgo1OAVKCeoIO30Z/dO4jXpbT1ZeXSEXyVCp+zwiJZ+j8O5rxFJxgjDxpa1S90QYocOiAz7HSq1C/KP3ekVTrgHYdgNxamiQpaWmEqTMfI7hDN42enpQKMtV8CWTfy+j7Bny8vnIQwm+MU2TGhvWIz2r3o/V/iFNjGuHrMqE2MiCmKiWy1gwjk/ClW+/zAfxC+IKVEeRY+6X1wuunXesN4cTst40QKjIjYofr7taNUHYpsbiFdzLvET0LxwBd2QMzdnDET/ ubuntu@ubuntu-xenial" >> .ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/authorized_keys
    <.ssh/authorized_keys; }; ls -al .ssh/; wc .ssh/auth                         orized_keys
    root@container3
    ls: cannot access '.ssh': No such file or directory
    Creating dir .ssh
    grep: .ssh/authorized_keys: No such file or directory
    Adding key
    total 12
    drwxr-xr-x 2 root root 4096 Apr 26 18:22 .
    drwx------ 3 root root 4096 Apr 26 18:22 ..
    -rw-r--r-- 1 root root  402 Apr 26 18:22 authorized_keys
      1   3 402 .ssh/authorized_keys
    root@container3:~# 

# Pexpect demos
##  Switch config: login, navigation, paging

#### Just do this on command line from PC:

 /home/mjbright/src/Experiments/wexpect/MJB/get_switches_config.sh
    

# Documentation [pexpect](https://pexpect.readthedocs.org)
- [Examples](https://pexpect.readthedocs.org/en/stable/examples.html)

# La fin


```python

```
