
# encoding: utf-8

"""
 1 [ ] update all coins data
 2 [ ] currencies support
 3 [ ] add update script to cron

 4 [X] high alignment calculation
 5 [X] low alignment calculation
 6 [X] avg
 7 [X] median
 8 [X] change (percent)
 9 [X] currency fullname
10 [X] header (human readable interval)
11 [ ] left axis
12 [ ] bottom axis
13 [X] date/time input
14 [X] intervals

15 [X] move to a separate module

16 [ ] url support
17 [ ] terminal size
18 [ ] json output

19 [ ] readme update
20 [ ]  intervals
21 [ ]  url
22 [ ]   screenshots
23 [ ] help update

24 [ ] commit

25 [ ] add nice colors
26 [ ] add message about @interval
27 [ ] add message about /help
28 [ ] add meessage to the main page
29 [X] clean up the code, remove all warnings

30 [ ] support of small intervals
31 [ ] output coin choice
"""

import sys
import datetime
import os
import re
import StringIO
import diagram
from colorama import Fore, Back, Style

MYDIR = os.path.abspath(os.path.dirname(os.path.dirname('__file__')))
sys.path.append("%s/lib/" % MYDIR)

# pylint: disable=wrong-import-position
import aggregate
import coins_names
import interval
from ansi_utils import colorize_number
# pylint: enable=wrong-import-position

PALETTES = {
    0: {
        1: Fore.WHITE,
    },
    1: {
        1: Fore.CYAN,
    },
    2: {
        1: Fore.RED,
    }
}

PALETTES_REVERSE = {
    0: {
        1: Back.WHITE + Fore.BLACK,
    },
    1: {
        1: Back.CYAN + Fore.BLACK,
    },
    2: {
        1: Back.RED + Fore.BLACK,
    }
}

def _format_value(value):
    return "%5.2f" % value

def _format_percentage(value):
    res = "%5.2f%%" % value
    if value > 0:
        res = "+"+res
    return res


class Diagram(object):

    """
    Diagram drawer. Uses ``data`` (with ``meta`` and ``ticks``) as its input,
    returns formated diagram as a string (generate_diagram()) or
    prints it on the stdout (show_diagram()).
    """

    def __init__(self, data, interval_pair, options=None):
        self.data = data
        if options is None:
            options = {}

        self.width = options.get('width', 80)
        self.height = options.get('height', 25)
        self.palette = 0

        self.interval = interval_pair[1] - interval_pair[0]

    def _align_label(self, timestamp, label):
        """
        Align ``label`` according to its ``timestamp``
        """
        time_begin = self.data['meta']['time_begin']
        time_end = self.data['meta']['time_end']

        number_of_spaces = int(1.0*self.width*(timestamp - time_begin)/(time_end - time_begin))
        number_of_spaces -= len(label)/2
        return " "*number_of_spaces + label

    def _format_time(self, timestamp, use_format=None, show_date=None, show_time=None):
        """
        Format ``timestamp`` depending on the current interval size (``self.interval``).
        If it is smaller than 24h, don't show date;
        if it is bigger than 7d, don't show time.
        If ``details`` is greater than 0, increase deails level.
        """

        if use_format is None:
            time_fmt = '%H:%M'

            if self.interval < 7*24*3600:
                date_fmt = '%a %d'
            else:
                date_fmt = '%d %b'

            fmt = ''
            if self.interval >= 24*3600 or show_date:
                fmt = date_fmt

            if self.interval < 24*3600 or show_time:
                if fmt:
                    fmt += ' '
                fmt += time_fmt

        else:
            fmt = use_format

        result = datetime.datetime.fromtimestamp(timestamp).strftime(fmt)
        return result

    def _show_change_percentage(self):
        f_p = _format_percentage
        meta = self.data['meta']
        change = meta['end'] - meta['begin']
        change_percentage = 100.0*change/meta['begin']
        return colorize_number(change), colorize_number(f_p(change_percentage))

    def _show_header(self):
        coin_symbol = self.data['meta']['symbol']
        coin_name = coins_names.coin_name(coin_symbol)

        meta = self.data['meta']
        interval_name = interval.from_secs(self.interval)
        time_interval = "%s +%s" % (
            self._format_time(meta['time_begin']),
            interval_name)
            #self._format_time(meta['time_end'], show_date=True, show_time=True),

        output = "\n"
        #output += u"{-1▶ %s (%s) }{1▶}" % (coin_name, coin_symbol)
        output += u"{1%s (%s)}," % (coin_name, coin_symbol)
        output += " %s" % (time_interval)
        output += " %s\n" % self._show_change_percentage()[1]
        output += "\n\n"

        return output

    def _show_footer(self):

        f_f = _format_value
        f_t = lambda t: self._format_time(t, show_date=True, show_time=True)

        meta = self.data['meta']

        output = "\n\n"
        output += "begin: %s (%s)" % (meta['begin'], f_t(meta['time_begin'])) + \
                  " // " + \
                  "end: %s (%s)" % (meta['end'], f_t(meta['time_end'])) + \
                  "\n"
        output += "high: %s (%s)" % (meta['max'], f_t(meta['time_max'])) + \
                  " // " + \
                  "low: %s (%s)" % (meta['min'], f_t(meta['time_min'])) + \
                  "\n"
        output += "avg: %s" % f_f(meta['avg']) + \
                  " // " + \
                  "median: %s" % f_f((meta['max'] + meta['min'])/2) + \
                  " // " + \
                  "change: %s (%s)" % self._show_change_percentage()

        return output

    def _colorize(self, text):

        palette = PALETTES[self.palette]
        palette_reverse = PALETTES_REVERSE[self.palette]

        def _colorize_curlies_block(text):

            text = text.group()[1:-1]
            stripped = text.lstrip('0123456789-')
            color_number = int(text[:len(text)-len(stripped)])

            reverse = False
            if color_number < 0:
                color_number = -color_number
                reverse = True

            if reverse:
                stripped = palette_reverse[color_number] + stripped + Style.RESET_ALL
            else:
                stripped = palette[color_number] + stripped + Style.RESET_ALL

            return stripped

        return re.sub("{.*?}", _colorize_curlies_block, text)

    def generate_diagram(self):
        """
        Show diagram for ``data``
        """

        class Option(object): #pylint: disable=too-many-instance-attributes,too-few-public-methods
            """Diagram configuration."""

            def __init__(self):
                self.axis = False
                self.batch = None
                self.color = True
                self.encoding = None
                self.function = None
                self.height = None
                self.keys = None
                self.legend = None
                self.palette = 'spectrum-reversed'
                self.reverse = None
                self.sleep = None

        data = self.data

        #print len(data['ticks'])
        istream = [str(x) for x in data['ticks']]
        #print "\n".join(istream)

        ostream = StringIO.StringIO()

        size = diagram.Point((self.width, self.height))
        option = Option()
        engine = diagram.AxisGraph(size, option)
        engine.consume(istream, ostream)

        meta = data['meta']

        high_line = self._align_label(meta['time_max'], _format_value(meta['max']))
        low_line = self._align_label(meta['time_min'], _format_value(meta['min']))
        lines = [high_line] + ostream.getvalue().splitlines() + [low_line]

        output = ""
        output += self._show_header()
        output += "\n".join([u"  │ %s" % x.decode('utf-8') for x in lines])
        output += u"\n  └" + u"─" * 80
        output += self._show_footer()

        output = self._colorize(output)
        return output

    def show_diagram(self):
        """
        Show diagram on the standard output.
        """
        print self.generate_diagram()

def _split_query(query):

    at_index = query.find('@')
    if '@' in query:
        coin = query[:at_index]
        interval_string = query[at_index+1:]
    else:
        coin = query
        interval_string = '24h'

    return coin, interval_string

def _parse_query(query):

    coin, interval_string = _split_query(query)

    coin = coin.upper()
    if coins_names.coin_name(coin) == '':
        raise SyntaxError("Invalid coin name: %s" % coin)

    time_begin, time_end = interval.parse_interval(interval_string)
    if time_begin is None or time_end is None:
        raise SyntaxError("Invalid time interval specification: %s" % interval_string)

    return coin, time_begin, time_end

def main():
    "experimenting with get_aggregated_coin()"

    if sys.argv == []:
        query = 'ETH@4d'
    else:
        query = sys.argv[1]

    try:
        coin, time_begin, time_end = _parse_query(query)
    except SyntaxError as e_msg:
        print "ERROR: %s" % e_msg
        sys.exit(1)


    ticks = 80
    data = aggregate.get_aggregated_coin(coin, time_begin, time_end, ticks)
    #import json
    #print json.dumps(data['meta'], indent=True)

    dia = Diagram(data, (time_begin, time_end))
    dia.show_diagram()

if __name__ == '__main__':
    main()
