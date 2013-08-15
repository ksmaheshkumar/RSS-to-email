#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, email, os, pickle, binascii, hashlib, time, feedparser, re, random, datetime
import xmlrpclib, smtplib, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

VERBOSITY_LEVEL=0

base={}

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

    if config["MAILSERVER_TLS"]:
        server = smtplib.SMTP(config["SMTP_HOST"], 587)
    else:
        server = smtplib.SMTP(config["SMTP_HOST"], 25)
    #server.set_debuglevel(1)
    server.ehlo()
    if config["MAILSERVER_TLS"]:
        server.starttls()
    if config["LOCAL_MAILSERVER"]==False and config["PASSWORD"]!="":
        server.login(LOGIN, config["PASSWORD"])
    server.sendmail(config["FROMADDR"], [config["MAIL_RCPT"]], msg.as_string())
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
    send_email (post_title.replace("\n", "\\n"), site_type+"-"+user, DATE, config["MAIL_RCPT"], text_part, html_part)
    if VERBOSITY_LEVEL > 0:
        print post_URL+" - sent"

def is_id_in_base (site_type, user, _id):
    if site_type not in base:
        return False
    if user not in base[site_type]:
        return False
    if _id not in base[site_type][user]:
        return False
    return True

def add_id_to_base (site_type, user, _id):
    if site_type not in base:
        base[site_type]={}
    if user not in base[site_type]:
        base[site_type][user]={}
    if _id in base[site_type][user]:
        return
    base[site_type][user][_id]=True

def process_post (site_type, user, post_date, post_title, post_summary, post_URL, post_id):
    if is_id_in_base(site_type, user, post_id):
        return
    email_post (site_type, user, post_date, post_title, post_summary, post_URL)
    add_id_to_base (site_type, user, post_id)

def fetch (site_type, user, RSS_URL=None):
    d=None

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

config_json=open("config.json").read()
config=json.loads(config_json)
#print config_data

LOGIN = config["FROMADDR"]

try:
    pkl_file = open('base.pkl', 'rb')
    base = pickle.load(pkl_file)
    pkl_file.close()
except IOError:
    # no file created yet
    pass

feeds_json=open("feeds.json").read()
feeds_data=json.loads(feeds_json)
#print feeds_data

for LJ in feeds_data["livejournal"]:
    fetch ("livejournal", LJ)
for tmp in feeds_data["rss"]:
    rss_url = tmp["url"]
    rss_name = tmp["name"]
    fetch ("rss", rss_name, rss_url)

output = open('base.pkl', 'wb')
pickle.dump(base, output)
output.close()
