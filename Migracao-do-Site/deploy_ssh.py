import pexpect
import sys

def run_ssh(command, password):
    print(f"Running: {command}")
    child = pexpect.spawn(command, encoding='utf-8')
    try:
        i = child.expect(['assword:', 'continue connecting (yes/no)?', pexpect.EOF], timeout=120)
        if i == 1:
            child.sendline('yes')
            child.expect('assword:')
            child.sendline(password)
        elif i == 0:
            child.sendline(password)
        
        child.expect(pexpect.EOF, timeout=300)
        print(child.before)
    except Exception as e:
        print(f"Error: {e}")
        print(child.before)

if __name__ == '__main__':
    pwd = 'Fdq827!#'
    # 1. SCP the zip file
    run_ssh('scp -o StrictHostKeyChecking=no -P 65002 deploy_root.zip u957947211@147.93.37.148:/home/u957947211/domains/resultsquad.com.br/public_html/deploy_root.zip', pwd)
    
    # 2. SSH to unzip and configure
    ssh_cmd = 'ssh -o StrictHostKeyChecking=no -p 65002 u957947211@147.93.37.148 "cd /home/u957947211/domains/resultsquad.com.br/public_html && unzip -o deploy_root.zip && rm deploy_root.zip"'
    run_ssh(ssh_cmd, pwd)
