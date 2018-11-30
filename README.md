# SunSon Project

## Ubuntu Config:

   ```sh
   sudo apt update
   sudo apt install make gcc wget tcl
   
   ls -ld .?*     # to list hidden files

   echo 'export PS1="\[\033[1;36m\]\h\[\033[0m\] \[\033[1;36m\]\u\[\033[0m\]:\[\033[1;36m\]\W\[\033[0m\]$ "' >> ~\.bashrc
   source ~\.bashrc
   # add this to ~\.bashrc in Ubuntu
   export PS1="\[\033[1;36m\]\!\[\033[0m\] \[\033[1;36m\]\u\[\033[0m\]:\[\033[1;36m\]\W\[\033[0m\]$ "
   # add this to ~\.bash_profile in OS X 
   
   echo 'alias py="python3"' >> ~/.bash_aliases
   echo 'alias sr="screen -R"' >> ~/.bash_aliases
   source ~/.bash_aliases
   
   #change timezone
   sudo dpkg-reconfigure tzdata
   ```
## Redis - Server
   http://sharadchhetri.com/2015/07/05/install-redis-3-0-from-source-on-ubuntu-14-04-centos-7-rhel-7/
   Linux:
   ```sh
   wget http://download.redis.io/redis-stable.tar.gz
   tar xvzf redis-stable.tar.gz
   cd redis-stable
   cd deps
   make hiredis lua jemalloc linenoise
   cd ..
   make
   make install
   cd utils
   ./install_server.sh
   ```

## Dropbox

- Install Dropbox: https://www.dropbox.com/install-linux 
   ```sh
   cd ~ && wget -O - "https://www.dropbox.com/download?plat=lnx.x86_64" | tar xzf -
   ```

- Run dropbox in background: 
   ```sh
   setsid ~/.dropbox-dist/dropboxd
   ```

## python3 (Ubuntu 17.10 already have it)

   ```sh
   # install pip (Ubuntu)
   sudo apt update
   sudo apt install python3-venv python3-pip
   sudo python3 -m pip install --upgrade pip
   sudo python3 -m pip install setuptools   
   ```   
   install python3.6 for f string:
   http://ubuntuhandbook.org/index.php/2017/07/install-python-3-6-1-in-ubuntu-16-04-lts/   

### Install 3rd party package

- Korbit API wrapper:  https://github.com/wisscot/korbit-python
    *-- download and pip install zip file*
    ```sh
    sudo python3 -m pip install git+https://github.com/wisscot/korbit-python.git
    sudo python3 -m pip uninstall korbit-python   # to uninstall
    ```
    
- Bitstamp API wrapper: https://github.com/wisscot/bitstamp-python-client
    *-- download or *
    ```sh
    sudo python3 -m pip install BitstampClient
    ```
    
- GDAX API wrapper: https://github.com/wisscot/gdax-python
    *-- download and pip install zip file*
    ```sh
    sudo python3 -m pip install git+https://github.com/danpaquin/gdax-python.git
    sudo python3 -m pip install git+https://github.com/wisscot/gdax-python.git
    ```

### Others:
```sh
sudo python3 -m pip install pymongo
sudo python3 -m pip install ccxt
sudo python3 -m pip install redis
```
