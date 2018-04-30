# SunSon Project

## Ubuntu Config:

   ```sh
   ls -ld .?*     # to list hidden files

   echo 'export PS1="\[\033[1;36m\]\h\[\033[0m\] \[\033[1;36m\]\u\[\033[0m\]:\[\033[1;36m\]\W\[\033[0m\]$ "' >> ~\.bashrc
   source ~\.bashrc
   # add this to ~\.bashrc in Ubuntu
   export PS1="\[\033[1;36m\]\!\[\033[0m\] \[\033[1;36m\]\u\[\033[0m\]:\[\033[1;36m\]\W\[\033[0m\]$ "
   # add this to ~\.bash_profile in OS X 
   
   echo 'alias py="python3"' >> ~/.bash_aliases
   source ~/.bash_aliases
   
   #change timezone
   sudo dpkg-reconfigure tzdata
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
   sudo apt-get update
   sudo apt install python3-venv python3-pip
   py -m pip install --upgrade pip
   py -m pip install setuptools   
   ```

### Install 3rd party package

- Korbit API wrapper:  https://github.com/wisscot/korbit-python
    *-- download and pip install zip file*
    ```sh
    py -m pip install git+https://github.com/wisscot/korbit-python.git
    py -m pip uninstall korbit-python   # to uninstall
    ```
    
- Bitstamp API wrapper: https://github.com/wisscot/bitstamp-python-client
    *-- download or *
    ```sh
    py -m pip install BitstampClient
    ```
    
- GDAX API wrapper: https://github.com/wisscot/gdax-python
    *-- download and pip install zip file*
    ```sh
    py -m pip install git+https://github.com/wisscot/gdax-python.git
    ```

   ```
### Others:
```sh
py -m pip install pymongo
py -m pip install ccxt
```
