import pexpect

def run_ssh(command, password):
    print(f"Running: {command}")
    child = pexpect.spawn(command, encoding='utf-8')
    try:
        i = child.expect(['assword:', pexpect.EOF], timeout=120)
        if i == 0:
            child.sendline(password)
            child.expect(pexpect.EOF, timeout=120)
            print(child.before)
    except Exception as e:
        print(f"Error: {e}")
        print(child.before)

if __name__ == '__main__':
    pwd = 'Fdq827!#'
    ssh_cmd = 'ssh -o StrictHostKeyChecking=no -p 65002 u957947211@147.93.37.148 "cd /home/u957947211/domains/resultsquad.com.br/public_html && ls -la wp-content/database && php -m | grep sqlite"'
    run_ssh(ssh_cmd, pwd)
