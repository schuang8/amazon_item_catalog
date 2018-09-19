## Amazon Item Watch List
### Source code for storing Amazon items you're interested in buying along with their price, discount, item link, and other features

## Prerequisites
[Python 3.6+](https://www.python.org/downloads/) is required
[Git Bash](https://git-scm.com/downloads) is recommended

## Getting Started
1. Run `python database_setup.py` in a cmd or bash to create the database file
2. Run `python prefillWatchList.py` to populate the database with some dummy entires
3. You may need to update the `client_secrets.json` and the `fb_client_secrets.json` in order to authenticate properly
4. Run `python project.py` to start the web server
5. Go to `localhost:5000` on the your webbrower to load the page

## NOTE:
1. You may need to run `pip install <package-name>` some python packages if loading the database/running the webpage causes python errors