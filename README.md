# SunSon Project

## Ubuntu Config:

Install Dropbox: https://www.dropbox.com/install-linux 

Run dropbox in background: setsid ~/.dropbox-dist/dropboxd


### Install python3 (Ubuntu 17.10 already have it)

   ```sh
   ls -ld .?*     to list hidden files
   echo 'alias py="python3"' >> ~/.bash_aliases
   source ~/.bash_aliases
   ```

### Install 3rd party package

- Korbit API wrapper:  https://github.com/wisscot/korbit-python
    *-- download and pip install zip file*
    ```sh
    py -m pip install git+https://github.com/wisscot/korbit-python.git
    ```
    
- Bitstamp API wrapper: https://github.com/wisscot/bitstamp-python-client
    *-- download or pip install BitstampClient*
    
- GDAX API wrapper: https://github.com/wisscot/gdax-python
    *-- download and pip install zip file*
    ```sh
    py -m pip install git+https://github.com/wisscot/gdax-python.git
    ```

- Bithumb: Splinter + Chrome
   
   -- splinter: https://splinter.readthedocs.io/en/latest/index.html
   ```sh
   py -m pip install splinter
   ```
   -- chrome drive: https://splinter.readthedocs.io/en/latest/drivers/chrome.html
