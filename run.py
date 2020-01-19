import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import os
import ssl
import time

import praw

from keywords import KEYWORDS, ARTISANS


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


def create_email(*, subject, from_email, to_email, text, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    msg.attach(part1)
    msg.attach(part2)

    return msg


def send_email(title, body, date, author, sub, link):
    try:
        msg = create_email(
            subject=title,
            from_email=sender_name,
            to_email=email_send_to,
            text=f"{body}\n\nSubmitted {date} by /u/{author}\nVia https://reddit.com/r/{sub} https://reddit.com{link}",
            html=f"""<html>
            <head></head>
            <body>
            <p>
            {body}<br/><br/>
            Submitted {date} by <a href='https://reddit.com/u/{author}'>/u/{author}</a><br/>
            Via <a href='https://reddit.com/r/{sub}'>/r/{sub}</a> (<a href='https://reddit.com{link}'>Link</a>)
            </p>
            </body>
            </html>""",
        )

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(email_server, email_port, context=context) as server:
            server.login(email_account, email_password)
            server.sendmail(email_account, email_send_to, msg.as_string())
    except Exception as e:
        print(e)


def clean_body(body, key_matches=[]):
    body = submission.selftext.replace("\n", "<br/>")

    # highlight search terms
    for key in key_matches:
        if not isinstance(key, re.Pattern):
            key = re.compile(re.escape(key), re.IGNORECASE)

        body = key.sub(r'<span style="background-color:yellow">\g<0></span>', body)

    return body


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
    title, _, title_want = full_title.partition("[W]")

    key_matches = set()
    # match keywords in title
    for key in KEYWORDS + ARTISANS:
        is_match = (
            bool(key.search(title))
            if isinstance(key, re.Pattern)
            else key.lower() in title.lower()
        )

        if start_time < submission.created_utc and is_match:
            key_matches.add(key)

    # match artisans in body
    for key in ARTISANS:
        is_match = (
            bool(key.search(submission.selftext))
            if isinstance(key, re.Pattern)
            else key.lower() in submission.selftext.lower()
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

        body = clean_body(submission.selftext, key_matches)
        link = submission.permalink
        subject = ", ".join(
            sorted(k.pattern if isinstance(k, re.Pattern) else k for k in key_matches)
        )
        send_email(f"{subject} - {full_title}", body, date, author, sub, link)
