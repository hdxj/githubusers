# -*- coding: utf-8 -*-
import re
import scrapy
from scrapy import Request
from githubspider.items import GithubItem
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String


DB_Session = sessionmaker(bind=create_engine('mysql+pymysql://root:1234@localhost/test?charset=utf8',echo=True))  # noqa
session = DB_Session()

Base = declarative_base()
class Mysql(Base):
    __tablename__ = 'githubusers'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), index=True)
    url = Column(String(50))
    location = Column(String(30))
    repositories = Column(Integer)
    stars = Column(Integer)
    followers = Column(Integer)
    following = Column(Integer)

class GithubSpider(scrapy.Spider):
    name = "github"
    allowed_domains = ["github.com"]
    url_ = 'http://github.com'
    start_name = '/Germey'

    def start_requests(self):
        yield Request(url=self.url_+self.start_name, callback=self.parse_page, dont_filter=False)

    #解析主页
    def parse_page(self,response):
        # print(response.text)
        #请求该用户粉丝列表
        follower_url = response.xpath('//nav[@class="reponav js-reponav"]/a[4]/@href').extract_first()
        yield Request(url=self.url_+follower_url, callback=self.get_follower)

        #请求该用户关注列表
        following_url = response.xpath('//nav[@class="reponav js-reponav"]/a[5]/@href').extract_first()
        yield Request(url=self.url_ + following_url, callback=self.get_following)

        #解析主页信息，这里仅解析了7个字段
        name = response.xpath('//div[@class="profile-header"]/h3/text()').extract_first()
        url = response.url
        list_ = response.xpath('//li[@class="details-item"]').xpath('descendant::text()').extract()
        l = []
        for i in list_:
            l.append(i.strip())
        location = ''.join(l)
        repositories = response.xpath('//nav[@class="reponav js-reponav"]/a[2]//span[@class="Counter"]/text()').extract_first()
        stars = response.xpath('//nav[@class="reponav js-reponav"]/a[3]//span[@class="Counter"]/text()').extract_first()
        followers = response.xpath('//nav[@class="reponav js-reponav"]/a[4]//span[@class="Counter"]/text()').extract_first()
        following = response.xpath('//nav[@class="reponav js-reponav"]/a[5]//span[@class="Counter"]/text()').extract_first()
        result = {
            'name': name,
            'url': url,
            'location': location,
            'repositories': self.change_num(repositories),
            'stars': self.change_num(stars),
            'followers': self.change_num(followers),
            'following': self.change_num(following),
        }

        #保存至mysql数据库
        data = Mysql(name=result['name'],
                     url=result['url'],
                     location=result['location'],
                     repositories=result['repositories'],
                     stars=result['stars'],
                     followers=result['followers'],
                     following=result['following'], )
        try:
            session.add(data)
            session.commit()
        except Exception as ex:
            print(ex)
            session.rollback()

        #保存至mongodb数据库
        item = GithubItem()
        for field in item.fields:
            if field in result.keys():
                item[field] = result.get(field)
        yield item

    #请求粉丝的主页
    def get_follower(self, response):
        divs = response.xpath('//div[@class="list-item user-list-item"]/a')
        for div in divs:
            url = div.xpath('./@href').extract_first()
            if url is not None:
                yield Request(url=self.url_+url, callback=self.parse_page, dont_filter=False)

    #请求关注者的主页
    def get_following(self, response):
        divs = response.xpath('//div[@class="list-item user-list-item"]/a')
        for div in divs:
            url = div.xpath('./@href').extract_first()
            if url is not None:
                yield Request(url=self.url_ + url, callback=self.parse_page, dont_filter=False)

    #把字段中的k和w转换成千和万
    def change_num(self, num):
        try:
            if 'k' in num:
                return int(float(num[:-1]) * 1000)
            elif 'w' in num:
                return int(float(num[:-1]) * 10000)
            else:
                return int(num)
        except Exception as e:
            print(e)
            return num

