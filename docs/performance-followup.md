# Deferred TV performance check

The user reported that the TV feels a bit laggy during the stock-launcher proof
and asked to investigate improvements after the remaining setup and customization.

This has not been measured or attributed to AeroTizen, Samsung Home, an individual
streaming app, or the network. Do not treat it as a diagnosed launcher regression.

After the custom home is complete, measure remote-navigation response, time to
first usable home screen, and app launch/return latency on the physical TV. Use
the results to distinguish UI rendering, background services, network delays, and
system behavior before changing anything. Check whether static wallpaper and
reduced animation improve the custom home without harming its design.

Keep firmware updates off. Root, debloating, and service-menu changes are outside
this follow-up's initial scope. Preserve the working Native Home and recovery
path.
