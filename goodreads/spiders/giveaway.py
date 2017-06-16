import scrapy
import json
from scrapy import FormRequest
from datetime import datetime
from scrapy.shell import inspect_response


class MySpider(scrapy.Spider):
    name = 'giveaway'

    #global variable
    authenticity_token = ''
    entered_giveaway_count = 0
    rejected_giveaway_count = 0



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

        #Modify files EnteredGiveaway and RejectedGiveaway to show dateTime
        with open("./RejectedGiveaways.txt", 'a') as f:
            f.write("\n------------------------------- " + str(datetime.now()) + " -------------------------------\n\n")
        with open("./EnteredGiveaways.txt", 'a') as f:
            f.write("\n------------------------------- " + str(datetime.now()) + " -------------------------------\n\n")

        #Go to 'giveaway/latest'
        yield scrapy.Request(url="https://www.goodreads.com/giveaway?sort=recently_listed&tab=recently_listed"
                             ,callback=self.latest_giveaway)

    #go through List and get link of all latest giveaway pages list
    def latest_giveaway(self,response):
        #get link of all pages
        pages_list=response.xpath('//a[contains(@href,"/giveaway?page")]/@href').extract()
        pages_list.pop()
        #append 1st page to the pages_list
        pages_list.append(pages_list[0].replace('page=2','page=1'))

        #Next list page available
        for page_url in pages_list:
            yield response.follow(page_url,callback=self.enter_giveaway)


    #get the urls to proceed for giveaway
    def enter_giveaway(self,response):
        #inspect_response(response, self)

        #Find 'Enter Giveaway' button and then find its main parent conatiner
        giveaway_list = response.xpath('//a[contains(text(),"Enter Giveaway")]/parent::div/parent::div/parent::li')
        giveaway_list_description = giveaway_list.xpath('.//div[@class="description descriptionContainer"]')

        giveaway_list_url = giveaway_list.xpath('.//a[contains(text(),"Enter Giveaway")]/@href').extract()
        giveaway_list_title = giveaway_list_description.xpath('.//a[@class="bookTitle"]/text()').extract()

        self.log("\n\n---------------- List at : %s ----------------\n" %response)
        self.log("\n\n%s \n\n" %giveaway_list_url)

        #proceed to the individual giveaways
        for i,giveaway_url in enumerate(giveaway_list_url):
            #get the content of the book (hidden content not always available)
            content_container = giveaway_list_description[i].xpath('div[@class="giveawayDescriptionDetails"]')

            giveaway_hidden_content = content_container.xpath('span[contains(@style,"display")]//text()').extract()
            #check if hidden content available : using len since hidden_content is Array (extract())
            if len(giveaway_hidden_content) is 0:
                #Visibile content used : `join` in case there are more elements inside the span
                giveaway_content=' '.join(content_container.xpath('span//text()').extract_first())
            else:
                giveaway_content=' '.join(giveaway_hidden_content)

            #check if the book should be ignored
            if(has_bad_words(self,giveaway_url,giveaway_list_title[i],giveaway_content)):
                continue
            yield response.follow(giveaway_url,callback=self.select_address)


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


    #page for confirmation : send post request
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


    #Final page : done
    def giveaway_accepted(self,response):
        #inspect_response(response,self)
        self.log('\n\n---------------------- Giveaway Entered : %s ---------------------\n\n'%response)

        self.entered_giveaway_count+=1
        with open("./EnteredGiveaways.txt", 'a') as f:
            f.write(str(self.entered_giveaway_count) + ". " + str(datetime.now()) + " : \t"
                        + str(response.url) + "\n")



#return: boolean - if book should be ignored
def has_bad_words(self,url,title,content):

        is_rejected=False

        bad_words = []      #Will match word to substring
        bad_titles = []     #Will match word to word

        #Make everything LowerCase for matching
        title=title.lower()
        content=content.lower()

        #doing title.split() so that "whole word" is matched
        #sub_string.lower() to convert to LowerCase in case Case-sensitive word provided
        if any(sub_string.lower() in title.split() for sub_string in bad_titles):
            is_rejected = True

        # sub_string.lower() to convert to LowerCase in case Case-sensitive word provided
        if any(sub_string.lower() in content for sub_string in bad_words):
            is_rejected = True

        if is_rejected:
            self.log('\n\n---------------------- Giveaway Cancelled : %s ---------------------\n\n' % url)

            MySpider.rejected_giveaway_count += 1
            with open("./RejectedGiveaways.txt", 'a') as f:
                f.write(str(self.rejected_giveaway_count) + ". " + str(datetime.now()) + " : \t"
                    +'https://www.goodreads.com'+ str(url) + "\n")

            return True

        return False