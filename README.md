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
   -- chrome drive: https://gist.github.com/wisscot/271bb7f8f0c85a06fd39f4aa32c196b9
   ```sh
   # Versions
   CHROME_DRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`

   # Install dependencies.
   sudo apt-get update
   sudo apt-get install -y unzip openjdk-8-jre-headless xvfb libxi6 libgconf-2-4

   # Install Chrome.
   sudo curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add
   sudo echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
   sudo apt-get -y update
   sudo apt-get -y install google-chrome-stable

   # Install ChromeDriver.
   wget -N http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/
   unzip ~/chromedriver_linux64.zip -d ~/
   rm ~/chromedriver_linux64.zip
   sudo mv -f ~/chromedriver /usr/local/bin/chromedriver
   sudo chown root:root /usr/local/bin/chromedriver
   sudo chmod 0755 /usr/local/bin/chromedriver   
   ```
### Others:
```sh
py -m pip install beautifulsoup4
py -m pip install pyotp
```
