# CryptoTaxes
This will fill out IRS form 8949 with Coinbase and GDAX data.  It assumes all short term
sales and FIFO sales.  This has only been tested on Windows.

Requirements:

PDFtk: 

https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/ 

GDAX Python Library:

    pip install GDAX

Coinbase Python Library:

    pip install Coinbase

Instructions:

In the same directory that you cloned this repository, make a file "credentials.py" that
contains the following:

    coinbaseKey = ''
    coinbaseSecret = ''
    gdaxKey = ''
    gdaxSecret = ''
    gdaxPassphrase = ''
    
You will populate this file with your Coinbase and GDAX API Key details.  First, get the 
Coinbase keys.   You can get the Coinbase keys by logging into your Coinbase
account and going to https://www.coinbase.com/settings/api and clicking on "+ New API Key."
A window will pop up and you should check "all" under Accounts and "wallet:accounts:read,"
"wallet:addresses:read," "wallet:buys:read," "wallet:deposits:read," "wallet:sells:read,"
"wallet:transactions:read," and "wallet:user:read" under Permissions, and then click Create.  
A new window will pop up with the API Key Details.  Put the API Key into the coinbaseKey variable
and the API Secret into the coinbaseSecret variable.  For example if your Coinbase API Key is
abcdefg1234 and your API Secret is zxcvbasdf1234qwer, then in the credentials.py file you should
have:

    coinbaseKey = 'abcdefg1234'
    coinbaseSecret = 'zxcvbasdf1234qwer'
    
Next, you need to get the GDAX API Key details.  Sign into GDAX and go to 
https://www.gdax.com/settings/api Under Permissions, check "View" and then click 
"Create API Key."  Enter the two-factor authenication code 
if you are asked for it, and then put the API key, the API secret, and
the passphrase in the credentials.py file.  Note that the passphrase
is located in a text box directory under the Permissions area where you checked
"View."  If the API key is qwerty123, the API secret is poiuyt999, and passphrase is
 mnbvc000, then you should finish filling out the credentials.py file (note that your 
 keys, secrets, and passphases could be longer or shorter than the examples given here):
 
    coinbaseKey = 'abcdefg1234'
    coinbaseSecret = 'zxcvbasdf1234qwer'
    gdaxKey = 'qwerty123'
    gdaxSecret = 'poiuyt999'
    gdaxPassphrase = 'mnbvc000'
    
 Once the five variables (gdaxKey, gdaxSecret, gdaxPassphrase, coinbaseKey, and
 coinbaseSecret) are set in credentials.py, you can run the program at the command line: 

    python taxes.py
    
When you run this, you will be prompted to enter your full name and then your social security 
number (these are used only for filling out the tax forms).  The filled out form 8949s will be 
in a new directory called PDFs.

If you find this code useful, feel free to donate!

BTC: 1LSTU2pNgeZKeD2CiTNPJRgcnhaUAkjpWJ

LTC: Ld6CF6LSy3K2PVpdm7qHbpFTarcVxdzE3L