# -*- coding: utf-8 -*-
class Intention:
    """
    Matches the current line to various pattern to guess what kind of
    code the user wants to write.
    """
    def __init__(self, line):
        self.line = line

    def assignment(self):
        """
        Whether the intention is to spell an assignment. Starts at "x=".
        """
        shards = self.line.split('=')
        if len(shards) == 2:
            return True

    def is_function(self):
        """
        Whether the current line is trying to spell "function". Starts at
        "fu", ends at "function"
        """
        line = self.line.strip()
        if line.startswith('fu'):
            if line.startswith('function') is False:
                return True

    def function_argument(self):
        """
        Whether the current line is trying to spell a function argument.
        Starts at "function name x:"
        """
        shards = self.line.split()
        if len(shards) > 2:
            if shards[0] == 'function':
                if ':' in shards[-1]:
                    return True

    def function_returns(self):
        """
        Whether the intention is to spell the return type of a function
        """
        shards = self.line.split()
        if len(shards) > 3:
            if self.line.endswith('returns') is False:
                if shards[-1] in 'return':
                    return True

    def foreach(self):
        """
        Whether the intention is to spell "foreach". Starts at "fo", ends at
        "foreach".
        """
        if self.line.startswith('fo'):
            if self.line.endswith('foreach') is False:
                return True

    def foreach_as(self):
        """
        Whether the intention is to spell the value in
        "foreach array as value".
        """
        line = self.line.strip()
        if line.endswith('as'):
            if line.startswith('as') is False:
                return True

    def while_(self):
        """
        Whether the intention is to spell "while". Starts at "wh", ends at
        "while".
        """
        if self.line.startswith('wh'):
            if self.line.endswith('while') is False:
                return True

    def unnecessary_colon(self):
        """
        Whether the intention is to write an if statement, but there is an
        unecessary colon
        """
        if self.line.endswith(':'):
            return True
