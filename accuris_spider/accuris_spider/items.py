# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AccurisSpiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    part_number = scrapy.Field()
    cross_part_number = scrapy.Field()
    cross_manufacturer = scrapy.Field()
    cross_type = scrapy.Field()
    notes = scrapy.Field()
