import scrapy
import json
from scrapy import FormRequest
from datetime import datetime
from scrapy.shell import inspect_response


class MySpider(scrapy.Spider):
    name = 'giveaway'

    #global variable
    authenticity_token = ''
    count = 0

    start_urls=["https://www.goodreads.com/user/sign_in"]

    # pass arguments as $scrapy crawl read -a html='...string...'
    #LOGIN
    def parse(self, response):
        username = getattr(self, 'username', None)
        password = getattr(self,'password', None)
        return [FormRequest.from_response(response,
                                          formdata={'user[email]': username,
                                                    'user[password]': password},
                                          formname="sign_in",
                                          callback=self.after_login)]

    def after_login(self, response):
        # check login succeed before going on
        if "authentication failed" in response.body:
            self.logger.error("Login failed")
            return

        #Login Successful
        username = getattr(self, 'username', None)
        self.log("\n\n------------------------ Logged in successfully : %s --------------------------\n\n"
                 % username)

        #Go to 'giveaway/latest'
        yield scrapy.Request(url="https://www.goodreads.com/giveaway?sort=recently_listed&tab=recently_listed"
                             ,callback=self.latest_giveaway)

    #go through List and Enter giveaway
    def latest_giveaway(self,response):
        #get link of all pages
        pages_list=response.xpath('//a[contains(@href,"/giveaway?page")]/@href').extract()
        pages_list.pop()
        #append current page to the pages_list
        pages_list.append(response.url)

        #Next list page available
        for page_url in pages_list:
            yield response.follow(page_url,callback=self.enter_giveaway)


    def enter_giveaway(self,response):
        #Get the urls for 'Entering Giveaway'
        giveaway_list = response.xpath('//a[contains(text(),"Enter Giveaway")]/@href').extract()
        self.log("\n\n---------------- List at : %s ----------------\n"
                 %response)
        self.log("\n\n%s \n\n" %giveaway_list)

        for giveway_url in giveaway_list:
            yield response.follow(giveway_url,callback=self.select_address)

    def select_address(self,response):
        next_page=response.xpath('//a[contains(text(),"Select This Address")]/@href').extract_first()

        #change the value in the global authenticity token
        global authenticity_token
        authenticity_token=response.xpath('//meta[@name="csrf-token"]/@content').extract_first()

        if next_page is not None:
            #post method here
            return [FormRequest(url='https://www.goodreads.com'+next_page,
                                              formdata={
                                                  'authenticity_token':authenticity_token
                                              },
                                              callback=self.final_page)]

    #page with confirmation : send post request
    def final_page(self,response):
        return [FormRequest.from_response(response,
                                          formdata={
                                              'authenticity_token':authenticity_token,
                                              'commit':'Enter Giveaway',
                                              'entry_terms': '1',
                                              'utf8': "&#x2713;"
                                                    },
                                          formname="entry_form",
                                          callback=self.giveaway_accepted)]

    def giveaway_accepted(self,response):
        #inspect_response(response,self)
        self.log('\n\n---------------------- Giveaway Entered : %s ---------------------\n\n'%response)

        self.count+=1
        with open("./EnteredGiveaways.txt", 'a') as f:
            f.write(str(self.count) + ". " + str(datetime.now()) + " : "
                        + str(response.url) + "\n")