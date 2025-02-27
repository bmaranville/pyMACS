Installation
=======================

Configuration of McStas environment
------------------------------------

.. note:: 

	pyMACS requires a bash terminal. It is untested on any platform except Ubuntu, so use at your own risk. Windows users should use the Windows subshell for Linux. 

Windows users should refer to `the WSL documentation <https://learn.microsoft.com/en-us/windows/wsl/install>`_ to configure a local Ubuntu environment. 

While Mac is not natively supported, it should work so long as the bash terminal is used. Internally, pyMACS uses a virtual disk on memory which in linux is located at 

.. code-block:: console

	/dev/shm/

This will need to be redefined to point to an alternate directory if using Mac - this step may be automated in a future update if needed, but for now please contact me if you need help with this. The software should run perfectly fine without this, but it may be bottlenecked by your hard disk.

Please refer to the `McStas documentation <https://github.com/McStasMcXtrace/McCode/blob/mccode-legacy/INSTALL-McStas-3.x/Linux/README.md>`_ to get a working McStas 3.X installation. 

Install with *pip*
----------------------

It is highly recommended to use a seperate virtual environment to run pyMACS and install its dependencies. This can be done simply asssuming one has a conda installtion, here for example I create an environment called "mcstas"

.. code-block:: console

	(base) $ conda create --name mcstas 
	(base) $ conda activate mcstas


To use pyMACS, simply install using pip:

.. code-block:: console

	(mcstas) $ install git+https://github.com/thallor1/pyMACS

You will need to have a valid `git installation <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_ first. 

There is one last step that is required which is the configuration of mcstasscript, which is a key dependency of pyMACS. Please refer to the `mcstasscript documentation <https://mads-bertelsen.github.io/getting_started/installation.html#configuration>`_ .