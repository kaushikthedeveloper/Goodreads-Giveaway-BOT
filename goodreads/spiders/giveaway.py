import scrapy
from scrapy import FormRequest
from datetime import datetime
from scrapy.shell import inspect_response


class MySpider(scrapy.Spider):
    # define the spider name
    name = 'giveaway'

    # $scrapy crawl giveaway -a username='...username...' -a password='...password...'

    def __init__(self, category=None, *args, **kwargs):
        super(MySpider, self).__init__(*args, **kwargs)

        self.start_urls = ["https://www.goodreads.com/user/sign_in", ]

        # intialise all members

        # used for header in POST
        self.authenticity_token = ''
        # count of number of entered/rejected books
        self.entered_giveaway_count = 0
        self.rejected_giveaway_count = 0
        # Since rejected books in one session may be repeated : keep track of them
        # `set` used as same book shouldn't be repeated
        self.rejected_books_list = set()

        # the files to which logs of Entered and Rejected Giveaways are to be provided
        self.f_entered_giveaways = '#EnteredGiveaways.txt'
        self.f_rejected_giveaways = '#RejectedGiveaways.txt'

        # get the username and password passed in the command line
        self.username = getattr(self, 'username', None)
        self.password = getattr(self, 'password', None)

        # get the words to be used to ignore books (not apply for giveaway) - from the files
        # usually used for ignoring books that contain bad words
        # `list` if provided | `None` if nothing is provided

        # from the title of the book
        f_blacklisted_titles = 'blacklisted_titles.txt'
        self.blacklisted_titles = get_file_contents(f_blacklisted_titles)
        # from the content description of the book
        f_blacklisted_words = 'blacklisted_words.txt'
        self.blacklisted_words = get_file_contents(f_blacklisted_words)

        # urls containing the giveaway lists
        self.giveaway_starting_urls = [
            "https://www.goodreads.com/giveaway?sort=ending_soon&tab=ending_soon",  # giveaway/ending_soon
            "https://www.goodreads.com/giveaway?sort=most_requested&tab=most_requested",  # giveaway/most_requested
            "https://www.goodreads.com/giveaway?sort=popular_authors&tab=popular_authors",  # givaway/popular_authors
            "https://www.goodreads.com/giveaway?sort=recently_listed&tab=recently_listed"  # giveaway/latest
        ]

    '''
    LOGIN : use the username and password passed by the user
    '''

    def parse(self, response):
        # submit for login
        return [FormRequest.from_response(response,
                                          formdata={'user[email]': self.username,
                                                    'user[password]': self.password},
                                          formname="sign_in",
                                          callback=self.after_login)]

    '''
    If Login not successful => exit
    Otherwise :
    => proceed to giveaway start pages having
        - Ending soon
        - Most Requested
        - Popular Authors
        - Recently listed
    '''

    def after_login(self, response):

        # login failed => close the spider
        if "sign_in" in response.url or b'try again' in response.body:
            self.logger.error("\n\n-------------------------- Login failed --------------------------\n\n")
            return

        # login successful
        self.log("\n\n-------------------------- Logged in successfully : %s --------------------------\n\n"
                 % self.username)

        # Modify files EnteredGiveaway and RejectedGiveaway to show present date-time
        # append to the end
        with open(self.f_rejected_giveaways, 'a') as f:
            f.write("\n-------------------------- " + str(datetime.now()) + " --------------------------\n\n")
        with open(self.f_entered_giveaways, 'a') as f:
            f.write("\n-------------------------- " + str(datetime.now()) + " --------------------------\n\n")

        # traverse to the giveaway list pages
        for url in self.giveaway_starting_urls:
            yield scrapy.Request(url=url, callback=self.giveaway_pages)

    '''
    Get list of the url of other pages in the tab (ex : Recently Listed tab contains pages in form of 1,2...next>>)
    '''

    def giveaway_pages(self, response):
        # get link of all pages
        pages_list = response.xpath('//a[contains(@href,"/giveaway?page")]/@href').extract()
        pages_list.pop()
        # append 1st page to the pages_list
        pages_list.append(pages_list[0].replace('page=2', 'page=1'))

        # go to those pages
        for page_url in pages_list:
            yield response.follow(page_url, callback=self.enter_giveaway)

    '''
    Go through Giveaway List - get the urls to proceed for giveaway

    NOTE : the spider employs a Depth First approach for the traversals
    '''

    def enter_giveaway(self, response):
        # Find 'Enter Giveaway' button and then find its main parent conatiner
        giveaway_list = response.xpath('//a[contains(text(),"Enter Giveaway")]/parent::div/parent::div/parent::li')
        giveaway_list_description = giveaway_list.xpath('.//div[@class="description descriptionContainer"]')

        # giveaway url
        giveaway_list_url = giveaway_list.xpath('.//a[contains(text(),"Enter Giveaway")]/@href').extract()
        # book title
        giveaway_list_title = giveaway_list_description.xpath('.//a[@class="bookTitle"]/text()').extract()

        self.log("\n\n-------------------------- List at : %s --------------------------\n" % response)
        self.log("\n\nBooks : %s \n\n" % giveaway_list_title)

        # proceed to the individual giveaways
        for i, giveaway_url in enumerate(giveaway_list_url):
            # get the description of the book
            # may contain hidden content (hidden content not always available)
            content_container = giveaway_list_description[i].xpath('div[@class="giveawayDescriptionDetails"]')
            giveaway_hidden_content = content_container.xpath('span[contains(@style,"display")]//text()').extract()

            # check if hidden content available : using len since hidden_content is Array (extract())
            if len(giveaway_hidden_content) is 0:
                # Visibile content used : `join` in case there are more elements inside the span
                giveaway_content = ' '.join(content_container.xpath('span//text()').extract_first())
            else:
                giveaway_content = ' '.join(giveaway_hidden_content)

            # check if the book should be ignored (is Blacklisted)
            if (is_blacklisted(self, giveaway_url, giveaway_list_title[i], giveaway_content)):
                # ignore this giveaway - go to next
                continue

            # go to the giveaway
            yield response.follow(giveaway_url, callback=self.select_address)

    '''
    Inside Giveaway page
    => select the 1st address (should be already arranged by user prior to running the spider)
    '''

    def select_address(self, response):
        # 1st button (Select this address)
        next_page = response.xpath('//a[contains(text(),"Select This Address")]/@href').extract_first()

        # change the value of the authenticity token
        self.authenticity_token = response.xpath('//meta[@name="csrf-token"]/@content').extract_first()

        if next_page is not None:
            # post method here
            return [FormRequest(url='https://www.goodreads.com' + next_page,
                                formdata={
                                    'authenticity_token': self.authenticity_token
                                },
                                callback=self.final_page)
                    ]

    '''
    Page for confirmation
        the post method provides
        => check  'I have read and agree to the giveaway entry terms and conditions'
        => uncheck  'Also add this book to my to-read shelf'

    NOTE : user is entered into the Giveaway at this stage
    '''

    def final_page(self, response):
        return [FormRequest.from_response(response,
                                          formdata={
                                              'authenticity_token': self.authenticity_token,
                                              'commit': 'Enter Giveaway',
                                              'entry_terms': '1',
                                              'utf8': "&#x2713;",
                                              'want_to_read': '0'
                                          },
                                          formname="entry_form",
                                          callback=self.giveaway_accepted)
                ]

    # Final page : done
    '''
    Final page - user has been entered into the Giveaway by now
    => inform user
    => increment Entered giveaway count
    '''

    def giveaway_accepted(self, response):
        # inspect_response(response,self)
        self.log('\n\n-------------------------- Giveaway Entered : %s --------------------------\n\n' % response)

        self.entered_giveaway_count += 1
        with open(self.f_entered_giveaways, 'a') as f:
            f.write(str(self.entered_giveaway_count) + ". " + str(datetime.now()) + " : \t"
                    + str(response.url) + "\n")

    '''
    @overridden close
    Before closing the Spider - show final log to user
    '''

    def close(spider, reason):
        spider.log('\n\n------------------------------- BOT WORK COMPELETED -------------------------------\n\n')
        spider.log('\n\n-------------------------- Giveaways Entered : %d --------------------------\n'
                   % spider.entered_giveaway_count)
        spider.log('\n\n-------------------------- Giveaways Ignored : %d --------------------------\n'
                   % spider.rejected_giveaway_count)
        spider.log('\n\n------------------------------- REGARDS -------------------------------\n\n')


'''
return boolean - is blacklisted (title/content)
=> check if the title contains any words (whole) that are Blacklisted
=> check if the description contains any words/sub-words that are Blacklisted

 - incase either of the two files are empty, ignore them

if is_rejected=True => call giveaway_rejected()
'''


def is_blacklisted(self, url, title, content):
    # flag
    is_rejected = False

    # book url
    url = 'https://www.goodreads.com' + url

    # if the book is already rejected : return True
    if url in self.rejected_books_list:
        return True

    # Make everything LowerCase for matching
    title = title.lower()
    content = content.lower()

    # doing title.split() so that "whole word" is matched
    # sub_string.lower() to convert to LowerCase in case Case-sensitive word provided
    if self.blacklisted_titles != None and \
            any(sub_string.lower() in title.split() for sub_string in self.blacklisted_titles):
        is_rejected = True

    # sub_string.lower() to convert to LowerCase in case Case-sensitive word provided
    if self.blacklisted_words != None and \
            any(sub_string.lower() in content for sub_string in self.blacklisted_words):
        is_rejected = True

    # giveaway is rejected
    if is_rejected:
        giveaway_rejected(self, url)
        return True
    else:
        return False


'''
Upon giveaway being rejected
=> inform user
=> increment Rejected giveaway count
'''


def giveaway_rejected(self, url):
    self.log('\n\n-------------------------- Giveaway Ignored : %s --------------------------\n\n' % url)

    self.rejected_giveaway_count += 1
    self.rejected_books_list.add(url)

    with open(self.f_rejected_giveaways, 'a') as f:
        f.write(str(self.rejected_giveaway_count) + ". " + str(datetime.now()) + " : \t"
                + str(url) + "\n")


'''
Get contents in the file
=> split with delimiter `newline` (each line contains the word)
=> strip whitespace
=> ignore empty lines
'''


def get_file_contents(filename):
    with open(filename) as f:
        required_list = [words.strip() for words in f.readlines() if len(words.strip()) > 0]

    if len(required_list) > 0:
        return required_list
    else:
        return None