# Goodreads-Giveaway-BOT
An automated Bot that enters the *User* onto [Giveaways on Goodreads](https://www.goodreads.com/giveaway) using 
[Scrapy web-crawler](https://scrapy.org/).

## Prerequisites

### User

- The user needs to have a [Goodreads Account](https://www.goodreads.com/user/sign_in).
- The user needs to have atleast one shipping address saved beforehand.

### Installation

To run the bot, [Scrapy](https://doc.scrapy.org/en/latest/) needs to be installed on the system.

To install Scrapy using conda, run:

```
$ conda install -c conda-forge scrapy
```
Alternatively, installation through PyPI:
```
$ pip install Scrapy
```

## Usage

Run the crawler 
```
$ scrapy crawl giveaway -a username="***email_id***" -a password="***password***"
```

This will start the bot with **User logging** in using the Email ID and password provided as arguments. Once logged in, 
the *spider* will start, traversing through the Giveaway pages : 
[Ending soon](https://www.goodreads.com/giveaway?sort=ending_soon&tab=ending_soon) , 
[Most requested](https://www.goodreads.com/giveaway?sort=most_requested&tab=most_requested), 
[Popular authors](https://www.goodreads.com/giveaway?sort=popular_authors&tab=popular_authors) and 
the [Latest](https://www.goodreads.com/giveaway?sort=popular_authors&tab=popular_authors) *giveaways*

### Features

  - *Asychronous* calls to pages, meaning faster crawling
  
  - Verbose Output during execution of Spider
  
  - Option to *Ignore giveaways* based on selective keywords as specified by user
    - Blacklist according to the title
    ```
    # blacklisted_titles.txt
    # provide the list of blacklisted words that should be checked in the titles
    # provide each word line-wise
    # Ex:
    word1
    word2
    word3
    ```
    - Blacklist according to the description
    ```
    # blacklisted_words.txt
    # provide the list of blacklisted words that should be checked in the decription
    # provide each word line-wise
    # Ex:
    word11
    word12
    word13
    ```
    
  - Store the Entered Giveaways list in file : *#EnteredGiveaways.txt*
  - Store the Rejected Giveaways list in file : *#RejectedGiveaways.txt*
    
  - When the Giveaway is being entered, the "*Also add this book to my to-read shelf.*" checkbox is un-ticked.

  - [Scrapy Settings](https://github.com/kaushikthedeveloper/Goodreads-Giveaway-BOT/blob/master/goodreads/settings.py) :
    ```
    # Obey robots.txt rules
    ROBOTSTXT_OBEY = True

    # Enable and configure the AutoThrottle extension
    AUTOTHROTTLE_ENABLED = True

    #Enable Cookies that are received and keeps track of cookies sent by servers, 
    #and sends them back on subsequent requests
    #COOKIES_ENABLED = True
    ```
    
###### **Disclaimer** : *The bot only Enters the user onto Giveaway, and does not guarantee that the user will win the Giveaway. Any reaction upon the use of the bot is upon the user and the user alone. Use at your own discretion.*
