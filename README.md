# bustracker
Routine for tracking buses using a html scrape and neopixels

Bus stops around York have a QR code on them that leads to a basic webpage showing a live departure board. Bus departures predicted from the schedule are shown in HH:MM format. Bus departures with a "live" departure time based off GPS data for the bus (which I think is measured against time-gates along the bus route, rather than anything more intelligent) are shown in as "XX mins" or "1min". The page loads from a server every refresh but I couldn't work out any API, so I've scraped it as text and used regular expressions to get a list of buses and their departure times.

These buses are then plotted on a string of neopixels which can be laid underneath a sketched map of the neighbourhood, creating a smart picture for use in the house. I am running this on an ESP32 firebeetle powered with a 500mAh battery.
