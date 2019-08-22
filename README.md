# PyDaemon

* Python 3.7+
* Uses standard library
* Not meant for production...

### Usage
If running directly via the command line, overwrite the `app` function to whatever your daemon needs to run.

`python3 pydaemon.py -pidfile /tmp/test.pid -action start`

`python3 xtx.py -pidfile /tmp/test.pid -action stop`

You can also import it as a module and specify your own `app` function:

    import pydaemon
    import time
    
    def my_function(n):
        with open("/tmp/example.txt", "w") as f:
            for i in range(n):
                f.write(f"{i}\n")
                time.sleep(1)
                
    pydaemon.main("/tmp/pidfile.pid", 20, action="start", app=my_function)