import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import os
import time

import praw

from keywords import KEYWORDS


email_server = os.environ["EMAIL_SERVER"]
email_port = int(os.environ["EMAIL_PORT"])
sender_name = f'{os.environ["SUBREDDIT"]} Notifier'
email_account = os.environ["EMAIL_ACCOUNT"]
email_password = os.environ["EMAIL_PASSWORD"]
email_send_to = os.environ["EMAIL_SEND_TO"]

reddit_client_id = os.environ["REDDIT_CLIENT_ID"]
reddit_client_secret = os.environ["REDDIT_CLIENT_SECRET"]
reddit_user_agent = os.environ["REDDIT_USER_AGENT"]
subreddit = os.environ["SUBREDDIT"]


def mailer(title, body, date, author, sub, link):
    try:
        mail = smtplib.SMTP(email_server, email_port)
        mail.ehlo()
        mail.starttls()
        mail.login(email_account, email_password)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = sender_name
        msg["To"] = email_send_to
        text = f"{body}\n\nSubmitted {date} by /u/{author}\nVia https://reddit.com/r/{sub} https://reddit.com{link}"
        html = f"""<html>
        <head></head>
        <body>
        <p>
        <strong>{title}</strong><br/><br/>
        {body}<br/><br/>
        Submitted {date} by <a href='https://reddit.com/u/{author}'>/u/{author}</a><br/>
        Via <a href='https://reddit.com/r/{sub}'>/r/{sub}</a> (<a href='https://reddit.com{link}'>Link</a>)
        </p>
        </body>
        </html>"""
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)
        mail.sendmail(email_account, email_send_to, msg.as_string())
        mail.quit()
    except Exception as e:
        print(e)


reddit = praw.Reddit(
    user_agent=reddit_user_agent,
    client_id=reddit_client_id,
    client_secret=reddit_client_secret,
)

subreddit = reddit.subreddit(subreddit)
start_time = time.time()
for submission in subreddit.stream.submissions():
    full_title = submission.title
    # we aren't interested in wants (for now anyway)
    title = full_title.split("[W]")[0]

    key_matches = set()
    for key in KEYWORDS:
        is_match = (
            bool(key.search(title))
            if isinstance(key, re.Pattern)
            else key.lower() in title.lower()
        )

        if start_time < submission.created_utc and is_match:
            key_matches.add(key)

    if key_matches:
        print(f"Found one! {datetime.datetime.now()}")
        author = submission.author
        sub = submission.subreddit
        date = time.strftime(
            "%b %d %Y at %H:%M:%S", time.gmtime(submission.created_utc)
        )
        body = submission.selftext.replace("\n", "<br/>")
        link = submission.permalink
        subject = ", ".join(
            [k.pattern if isinstance(k, re.Pattern) else k for k in key_matches]
        )
        mailer(f"{subject} - {full_title}", body, date, author, sub, link)
