import os
import signal
import sys
import time
import traceback
import logging


def start(pid_file, app, *args, **kwargs):
    """
    Starts the daemon.
    Args:
        pid_file - Path to pid file
        app - The function that will be run as a daemon
        *args, **kwargs - These will be passed on to the app function
    """
    logging.info("Starting daemon")
    logging.debug(f"PID file location: {pid_file}")

    try:
        with open(pid_file, "r") as f:
            pid = f.read()
        logging.info(f"Process already exists with PID: {pid}... Exiting")
        return 0
        
    except FileNotFoundError:
        pass
    
    logging.debug("Entering fork function...")
    fork(pid_file) # Create a fork

    logging.debug("Running app function...")
    app(*args, **kwargs) # Run the app function

    logging.info("Function completed. Deleting pidfile")
    os.remove(pid_file)

    return 0

def stop(pid_file):
    """
    Stops the daemon. This deletes the pid file when the process has been killed.
    Args:
        pid_file - Path to pid file
    """

    pid = get_pid(pid_file)
    if pid == -1:
        return 1

    try:
        os.kill(pid, 0) # Send signal 0 to the process which does nothing if the process exists. This part is so the user knows that the process didn't exist but the PID file existed anyway
    except ProcessLookupError:
        logging.warning(f"Process {pid} does not exist. Removing old PID file.")
        os.remove(pid_file)
        return 0
    
    try:
        for _ in range(10): # Try killing the process 10 times with a 2 second sleep between trys. This can be changed to a while True loop which would try to kill the process indefinitely.
            os.kill(pid, signal.SIGKILL)
            time.sleep(2)
        else: # Exit if all 10 iterations were completed
            logging.error(f"Unable to kill process {pid}")
            return 1
    except ProcessLookupError:
        logging.info(f"Process {pid} is now terminated. Removing PID file.")
        os.remove(pid_file)
    
    return 0

def fork(pid_file):
    """
    Creates a daemon by forking the current process twice
    Args:
        pid_file - Path to pid file
    """
    # Double fork method of daemonising a process in Unix
    pid = os.fork() # The first fork is to prevent a zombie process by exiting the parent process straight away
    if pid > 0: # os.fork() returns 0 if the current process is the child and the child's pid in the parent. So this if block only gets executed in the parent
        sys.exit() # Exit the parent process

    os.chdir("/") # Change directory to /
    os.setsid() # This is to ensure the process doesn't die or hang when the terminal is logged out
    os.umask(0) # Reset umask
    
    pid = os.fork() # Fork again from the child
    if pid > 0:
        # This is inside the first child which creates the pid file.
        # One problem with this method is that if the pid file is deleted and the daemon is started again, there will be two instances of the daemon running.
        # A workaround could be to have the pid file be opened by the app function in a seperate thread but not written to.
        # This would prevent multiple instances running as the OS will prevent a proceess from deleting a file if it is open in another process
        create_pid_file(pid_file, pid)
        sys.exit() # Exit the second parent. The child process is now orphaned and is parented by pid 0
    
    # From this point the code is running in the grandchild process which is parented by 0

    # Redirect stdout and stderr to /dev/null
    logging.debug("Redirecting stdout and stderr to /dev/null")
    sys.stdout = open('/dev/null', 'w') 
    sys.stderr = open('/dev/null', 'w')

    return pid

def create_pid_file(pid_file, pid):
    """
    Creates a pid file.
    Args:
        pid_file - Path to pid file
        pid - process number to be written to file
    """
    with open(pid_file, "w") as f:
        logging.debug(f"Writing PID {pid} to file {pid_file}")
        f.write(str(pid))

def get_pid(pid_file):
    """
    Gets pid number from file.
    Args:
        pid_file: Path to pid file
    """
    try:
        with open(pid_file, "r") as f:
            pid = f.read()
            logging.debug(f"Read PID file {pid_file}. Contents:\n{pid}")
        
    except FileNotFoundError:
        logging.error(f"The process is not running or the PID file has been deleted")
        return -1
    
    pid = pid.strip()
    try:
        pid = int(pid)
    except ValueError:
        logging.error("PID file is invalid")
        return -1
    
    return pid

def sigterm_handler(signal, frame): # This is to handle sigterm which can be sent via the kill command
    logging.info("SIGTERM received. Stopping process and exiting")
    sys.exit()

def log_except_hook(*exc_info): # This is to handle any exceptions that are not in an except block
    text = "".join(traceback.format_exception(*exc_info))
    logging.critical(f"Unhandled Exception:\n{text}")
    sys.exit(1)


def app(*args, **kwargs):
    """
    This is the function that is run as a daemon.
    """

    with open("/tmp/pydaemon.txt", "w") as f:
        for i in range(20):
            time.sleep(1)
            f.write(f"{i}\n")
            f.flush()

def main(pid_file, *args, action="start", app=app, logLevel=logging.INFO, **kwargs):
    """
    main function
    args:
        pid_file (/tmp/pydaemin.pid) - The location of the pid file. Will be created if it doesn't exist
        action (start) - start or stop the daemon
        app - The function that will be run as a daemon
        logLevel (logging.INFO) - Log level
    """
    logging.debug(f"main arguments: {locals()}")

    signal.signal(signal.SIGTERM, sigterm_handler) # Register sigterm handler
    currentDir = os.path.dirname(os.path.abspath(__file__))
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logLevel, handlers=[
        logging.FileHandler(currentDir+"/pydaemon.log"),
        logging.StreamHandler()
    ])

    if action == "start":
        code = start(pid_file, app, *args, **kwargs)
    elif action == "stop":
        code = stop(pid_file)
    else:
        print("Action can only be start or stop")
    
    if __name__ == "__main__":
        sys.exit(code)
    else:
        return code

    

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('-pidfile', action="store", dest="pid_file")
    parser.add_argument('-action', action="store", dest="action", default="start")
    parser.add_argument('-loglevel', action="store", nargs="?", dest="logLevel", const="info", default="info", choices=["off", "debug", "info", "warning", "error", "critical"])
    args = parser.parse_args()

    logLevels = {
        "off": logging.NOTSET,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    logLevel = logLevels[args.logLevel]

    sys.excepthook = log_except_hook
    main(args.pid_file, action=args.action, app=app, logLevel=logLevel)