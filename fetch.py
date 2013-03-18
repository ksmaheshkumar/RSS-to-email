#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import email
import os
import binascii
import hashlib
import time
import feedparser
import re
import random
import datetime
import xmlrpclib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

VERBOSITY_LEVEL=0

FROMADDR = "from@domain"
PASSWORD = "PASSWORD"
SMTP_HOST = "127.0.0.1"
MAIL_RCPT = "recepient@domain"

LOGIN    = FROMADDR

def send_email (subj, _from, DATE, to, text_part, html_part):
    msg = MIMEMultipart('alternative')
    msg['From']=_from
    if subj!=None:
        msg['Subject']=subj.encode('utf-8')
    msg['Date']=DATE
    msg['To'] = to

    part1 = MIMEText(text_part, 'plain')
    part2 = MIMEText(html_part, 'html')
    msg.attach(part1)
    msg.attach(part2)

    #server = smtplib.SMTP(SMTP_HOST, 587)
    server = smtplib.SMTP(SMTP_HOST, 25)
    #server.set_debuglevel(1)
    server.ehlo()
    #server.starttls()
    #server.login(LOGIN, PASSWORD)
    server.sendmail(FROMADDR, [MAIL_RCPT], msg.as_string())
    server.quit()

def email_post (site_type, user, post_date, post_title, post_summary, post_URL):
    # UTC time in post_date!
    TS=time.mktime(post_date)
    # convert UTC time to local time
    TS=TS+(-time.timezone)
    DATE=email.utils.formatdate(TS) # ... because that function takes only local time!

    text_part=(post_summary+"\r\n\r\n"+post_URL).encode('utf-8')
    html_part=post_summary.encode('utf-8')
    #print "post_title=["+post_title.replace("\n", "\\n")+"]"
    if post_title==None:
        post_title=""
    send_email (post_title.replace("\n", "\\n"), site_type+"-"+user, DATE, MAIL_RCPT, text_part, html_part)
    if VERBOSITY_LEVEL > 0:
        print post_URL+" - sent"

def calc_fname_in_base (site_type, user, _id):
    m = hashlib.md5()
    m.update(_id)
    hh=binascii.hexlify(m.digest())

    return site_type+"/"+user+"/"+hh[0]+"/"+hh[1]+"/"+hh[2:]

def is_id_in_base (site_type, user, _id):
    return os.path.exists(calc_fname_in_base (site_type, user, _id))

def add_id_to_base (site_type, user, _id):
    fname=calc_fname_in_base (site_type, user, _id)
    filepath=os.path.dirname(fname)

    if os.path.exists (filepath)==0:
        os.makedirs (filepath)    
    
    f=open (fname, "w+")
    #f.write ("sent")
    f.close()

def process_post (site_type, user, post_date, post_title, post_summary, post_URL, post_id):
    if is_id_in_base(site_type, user, post_id):
        return
    email_post (site_type, user, post_date, post_title, post_summary, post_URL)
    add_id_to_base (site_type, user, post_id)

def fetch (site_type, user, RSS_URL=None):
    d=None

    if site_type=='twitter':
        d = feedparser.parse("https://api.twitter.com/1/statuses/user_timeline.rss?screen_name="+user)
    if site_type=='livejournal':
        d = feedparser.parse("http://"+user+".livejournal.com/data/rss")
    if site_type=='ljr':
        d = feedparser.parse("http://lj.rossia.org/~"+user+"/data/rss")
    if site_type=='rss':
        d = feedparser.parse(RSS_URL)

    if d==None:
        print "unknown site_type="+site_type
        return

    if len(d.entries)==0:
        if VERBOSITY_LEVEL>0:
            print user+": no entries"
        return
    if VERBOSITY_LEVEL>0:
        print (site_type+":"+user+": got %d entries" % len(d.entries))
    for e in d.entries:
        if VERBOSITY_LEVEL>1:
            for i in e:
                print "["+i+"]", e[i]
        if 'published_parsed' in e:
            post_date=e['published_parsed'] # time.struct_time, UTC/GMT time
        else: 
            if 'updated_parsed' in e:
                post_date=e['updated_parsed'] # time.struct_time, UTC/GMT time
            else:
                post_date=time.localtime() # no dates, as in hacker news feed

        if 'title' in e:
            post_title=e['title']
        else:
            post_title=None

        if 'content' in e: # have full post content?
            post_body=e['content'][0]['value']
        else:
            post_body=e['summary']

        if 'id' in e:
            post_id=e['id']
        else:
            if 'published' in e:
                post_id=e['published'] # use date instead of id
            else:
                post_id=e['link'] # use link instead of id (hacker news feed)
        process_post (site_type, user, post_date, post_title, post_body, e['link'], post_id)

fetch ("livejournal", "dennis")
fetch ("twitter", "yurichev")
fetch ("rss", "blog_yurichev", "http://blog.yurichev.com/rss.xml")
