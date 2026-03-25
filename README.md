# Big-O Reminders

This is a stupid simple multi-device reminders application. The idea
is that you can use a mobile automation (Tasker...) or other
entrypoint post a reminder, and it can then show up persistently on
any of your device(s) that you configured, until it is dismissed.
Great for quickly making a note of something you'll have to deal with
when you're back at your computer.

I have this on a VPS fronted by Caddy using a private CA. Notably
there is no authentication. It turns out you can make security by
obscurity pretty darn good by simply having a reverse proxy reject
requests that don't come with the appropriate SNI, and use a private
CA for the TLS, because then the IP address / domain name pair
basically acts like a username and password if they are not published
elsewhere. Besides, what are you going to do? Hack the most recent 15
minutes of my todo list? Lol.
